<!--
  子系统 3.2 — 缓冲区重叠分析
  功能：基于时间轴同步多架无人机位置，判断安全缓冲区是否重叠，输出冲突时间、位置、风险等级。
  算法：对每个时间步，计算所有无人机两两之间的水平距离，< 2×buffer 即判定为缓冲区重叠冲突。
  数据：模拟6条无人机航迹（广州区域），时间范围 0~60 分钟，1 分钟步进。
-->
<template>
  <div class="overlap-page">
    <!-- 左侧控制面板 -->
    <aside class="control-panel">
      <div class="panel-header">
        <span>🔍</span>
        <h2>缓冲区重叠分析</h2>
      </div>

      <div class="section">
        <h3 class="section-title">分析参数</h3>
        <div class="param-row">
          <span>安全缓冲（m）</span>
          <el-input-number v-model="bufferRadius" :min="50" :max="500" :step="10" size="small" style="width:120px" />
        </div>
        <div class="param-row">
          <span>时间范围</span>
          <el-select v-model="timeRange" size="small" style="width:140px">
            <el-option label="全程（0-60分钟）" :value="60" />
            <el-option label="前30分钟" :value="30" />
            <el-option label="前15分钟" :value="15" />
          </el-select>
        </div>
        <el-button type="primary" style="width:100%;margin-top:10px" :loading="analyzing" @click="runAnalysis">
          执行分析
        </el-button>
      </div>

      <div class="section">
        <h3 class="section-title">时间轴回放</h3>
        <div class="time-display">T = {{ currentMinute }} 分钟</div>
        <el-slider v-model="currentMinute" :min="0" :max="timeRange" :step="1"
          show-tooltip @change="renderFrame" />
        <div class="playback-btns">
          <el-button size="small" @click="togglePlay">{{ playing ? '⏸ 暂停' : '▶ 播放' }}</el-button>
          <el-button size="small" @click="resetPlayback">⏮ 重置</el-button>
        </div>
      </div>

      <div class="section">
        <h3 class="section-title">冲突事件列表</h3>
        <div v-if="!conflicts.length" class="empty-tip">
          {{ analyzed ? '未检测到缓冲区重叠' : '请先执行分析' }}
        </div>
        <div v-for="c in conflicts" :key="c.id" class="conflict-item"
          :class="`risk-${c.risk}`" @click="jumpToConflict(c)">
          <div class="conflict-top">
            <span class="conflict-time">T={{ c.time }}min</span>
            <el-tag :type="c.risk === 'high' ? 'danger' : 'warning'" size="small">
              {{ c.risk === 'high' ? '高风险' : '中风险' }}
            </el-tag>
          </div>
          <div class="conflict-drones">{{ c.droneA }} ↔ {{ c.droneB }}</div>
          <div class="conflict-dist">最近距离：{{ c.distance.toFixed(0) }}m（阈值 {{ bufferRadius * 2 }}m）</div>
        </div>
      </div>
    </aside>

    <!-- 右侧地图 -->
    <div class="map-area">
      <div ref="mapRef" class="map-container"></div>
      <div class="conflict-badge" v-if="analyzed">
        发现 <strong>{{ conflicts.length }}</strong> 处缓冲区重叠
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import AMapLoader from '@amap/amap-jsapi-loader'
import { ElMessage } from 'element-plus'

const bufferRadius = ref(150)
const timeRange = ref(60)
const currentMinute = ref(0)
const playing = ref(false)
const analyzed = ref(false)
const analyzing = ref(false)
const conflicts = ref([])
const mapRef = ref(null)

let AMap = null, map = null, playTimer = null
let markers = [], circles = [], conflictMarkers = []

// ── 模拟6条航迹（起止点线性插值） ──────────────────
// 格式：[起点, 终点, 无人机名称]，时间0~60min均匀飞行
const TRAJECTORIES = [
  { name: 'GZ-A001', start: [113.3245, 23.1201], end: [113.2671, 23.0900] },
  { name: 'GZ-A002', start: [113.2994, 23.1540], end: [113.3580, 23.1050] },
  { name: 'GZ-B001', start: [113.3580, 23.1050], end: [113.3100, 23.1380] },
  { name: 'GZ-B002', start: [113.2671, 23.0900], end: [113.3245, 23.1201] },
  { name: 'GZ-C001', start: [113.3100, 23.1380], end: [113.2994, 23.0750] },
  { name: 'GZ-C002', start: [113.3900, 23.1380], end: [113.3100, 23.1050] },
]

// 在 t 时刻（0~60min）获取每架无人机的插值位置
function getPositions(t) {
  const ratio = t / 60
  return TRAJECTORIES.map(traj => ({
    name: traj.name,
    lng: traj.start[0] + (traj.end[0] - traj.start[0]) * ratio,
    lat: traj.start[1] + (traj.end[1] - traj.start[1]) * ratio,
  }))
}

// 计算两点间的近似水平距离（米）
function haversine(p1, p2) {
  const R = 6371000
  const dLat = (p2.lat - p1.lat) * Math.PI / 180
  const dLng = (p2.lng - p1.lng) * Math.PI / 180
  const a = Math.sin(dLat / 2) ** 2 + Math.cos(p1.lat * Math.PI / 180) * Math.cos(p2.lat * Math.PI / 180) * Math.sin(dLng / 2) ** 2
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
}

async function initMap() {
  const key = import.meta.env.VITE_AMAP_KEY
  const sec = import.meta.env.VITE_AMAP_SECURITY_CODE
  window._AMapSecurityConfig = { securityJsCode: sec }
  try {
    AMap = await AMapLoader.load({ key, version: '2.0', plugins: ['AMap.Scale'] })
    map = new AMap.Map(mapRef.value, {
      viewMode: '2D', zoom: 12,
      center: [113.3244, 23.1150],
      mapStyle: 'amap://styles/whitesmoke',
    })
    map.addControl(new AMap.Scale({ position: 'LB' }))
    renderFrame(0)
  } catch (e) { console.error('AMap load failed:', e) }
}

// 清除当前帧的所有覆盖物
function clearFrame() {
  markers.forEach(m => map.remove(m))
  circles.forEach(c => map.remove(c))
  conflictMarkers.forEach(m => map.remove(m))
  markers = []; circles = []; conflictMarkers = []
}

// 渲染指定时间步的地图帧
function renderFrame(t) {
  if (!map || !AMap) return
  clearFrame()
  const positions = getPositions(t)

  // 检测当前帧的冲突对
  const frameConflicts = []
  for (let i = 0; i < positions.length; i++) {
    for (let j = i + 1; j < positions.length; j++) {
      const dist = haversine(positions[i], positions[j])
      if (dist < bufferRadius.value * 2) {
        frameConflicts.push({ i, j, dist })
      }
    }
  }
  const conflictIds = new Set(frameConflicts.flatMap(c => [c.i, c.j]))

  positions.forEach((pos, idx) => {
    const isConflict = conflictIds.has(idx)
    const color = isConflict ? '#dc2626' : '#2563eb'

    // 缓冲圆
    const circle = new AMap.Circle({
      center: new AMap.LngLat(pos.lng, pos.lat),
      radius: bufferRadius.value,
      strokeColor: color, strokeWeight: 2, strokeOpacity: 0.8,
      fillColor: color, fillOpacity: isConflict ? 0.2 : 0.1,
    })
    map.add(circle)
    circles.push(circle)

    // 无人机标记
    const marker = new AMap.Marker({
      position: [pos.lng, pos.lat],
      content: `<div style="background:${isConflict ? '#dc2626' : '#1e40af'};color:#fff;padding:3px 6px;border-radius:4px;font-size:11px;white-space:nowrap;${isConflict ? 'box-shadow:0 0 6px #dc2626;' : ''}">🚁 ${pos.name}</div>`,
      offset: new AMap.Pixel(-24, -12),
    })
    map.add(marker)
    markers.push(marker)
  })

  // 冲突连线
  frameConflicts.forEach(c => {
    const p1 = positions[c.i], p2 = positions[c.j]
    const line = new AMap.Polyline({
      path: [[p1.lng, p1.lat], [p2.lng, p2.lat]],
      strokeColor: '#dc2626', strokeWeight: 2,
      strokeStyle: 'dashed', strokeOpacity: 0.7,
    })
    map.add(line)
    conflictMarkers.push(line)
  })
}

// 全程扫描所有时间步，收集冲突事件
async function runAnalysis() {
  analyzing.value = true
  await new Promise(r => setTimeout(r, 100))
  const found = []
  const seen = new Set() // 去重：同一对无人机只保留最近点

  for (let t = 0; t <= timeRange.value; t++) {
    const positions = getPositions(t)
    for (let i = 0; i < positions.length; i++) {
      for (let j = i + 1; j < positions.length; j++) {
        const dist = haversine(positions[i], positions[j])
        if (dist < bufferRadius.value * 2) {
          const key = `${i}-${j}`
          // 只保留距离最近的一次冲突
          const existing = found.findIndex(f => f._key === key)
          if (existing >= 0) {
            if (dist < found[existing].distance) {
              found[existing] = { id: `${key}-${t}`, _key: key, time: t, droneA: positions[i].name, droneB: positions[j].name, distance: dist, risk: dist < bufferRadius.value ? 'high' : 'medium', lat: (positions[i].lat + positions[j].lat) / 2, lng: (positions[i].lng + positions[j].lng) / 2 }
            }
          } else {
            found.push({ id: `${key}-${t}`, _key: key, time: t, droneA: positions[i].name, droneB: positions[j].name, distance: dist, risk: dist < bufferRadius.value ? 'high' : 'medium', lat: (positions[i].lat + positions[j].lat) / 2, lng: (positions[i].lng + positions[j].lng) / 2 })
          }
        }
      }
    }
  }

  conflicts.value = found.sort((a, b) => a.time - b.time)
  analyzed.value = true
  analyzing.value = false
  renderFrame(currentMinute.value)
  ElMessage({ type: found.length ? 'warning' : 'success', message: found.length ? `检测到 ${found.length} 处缓冲区重叠` : '未检测到缓冲区重叠' })
}

function jumpToConflict(c) {
  currentMinute.value = c.time
  renderFrame(c.time)
  if (map && AMap) map.setCenter([c.lng, c.lat])
}

function togglePlay() {
  if (playing.value) {
    clearInterval(playTimer); playing.value = false
  } else {
    playing.value = true
    playTimer = setInterval(() => {
      if (currentMinute.value >= timeRange.value) { clearInterval(playTimer); playing.value = false; return }
      currentMinute.value++
      renderFrame(currentMinute.value)
    }, 300)
  }
}

function resetPlayback() {
  clearInterval(playTimer); playing.value = false; currentMinute.value = 0; renderFrame(0)
}

onMounted(initMap)
onUnmounted(() => { clearInterval(playTimer); map?.destroy() })
</script>

<style scoped>
.overlap-page { display: flex; height: 100%; overflow: hidden; }
.control-panel { width: 300px; flex-shrink: 0; background: #fff; border-right: 1px solid #e5e7eb; overflow-y: auto; padding: 16px; }
.panel-header { display: flex; align-items: center; gap: 8px; margin-bottom: 16px; font-size: 20px; }
.panel-header h2 { font-size: 15px; font-weight: 700; margin: 0; }
.section { border-top: 1px solid #f3f4f6; padding-top: 14px; margin-bottom: 12px; }
.section-title { font-size: 13px; font-weight: 600; color: #374151; margin: 0 0 10px; }
.param-row { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; font-size: 12px; color: #6b7280; }
.param-row > span:first-child { width: 90px; flex-shrink: 0; }
.time-display { text-align: center; font-size: 20px; font-weight: 700; color: #2563eb; margin-bottom: 8px; }
.playback-btns { display: flex; gap: 8px; margin-top: 8px; }
.empty-tip { font-size: 12px; color: #9ca3af; text-align: center; padding: 10px 0; }
.conflict-item { padding: 8px 10px; border-radius: 6px; margin-bottom: 6px; cursor: pointer; border-left: 3px solid #d1d5db; background: #f9fafb; }
.conflict-item:hover { background: #f0f4ff; }
.conflict-item.risk-high { border-left-color: #dc2626; }
.conflict-item.risk-medium { border-left-color: #f59e0b; }
.conflict-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
.conflict-time { font-size: 12px; font-weight: 600; color: #374151; }
.conflict-drones { font-size: 12px; color: #1e40af; margin-bottom: 2px; }
.conflict-dist { font-size: 11px; color: #6b7280; }
.map-area { flex: 1; position: relative; }
.map-container { width: 100%; height: 100%; }
.conflict-badge {
  position: absolute; top: 16px; right: 16px; background: rgba(255,255,255,0.95);
  border-radius: 8px; padding: 8px 14px; font-size: 13px; box-shadow: 0 2px 8px rgba(0,0,0,0.15);
  color: #374151;
}
.conflict-badge strong { color: #dc2626; }
</style>
