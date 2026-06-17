<!--
  子系统 3.1 — 安全范围配置
  功能：设定无人机水平/垂直安全距离及风险等级阈值，在地图上实时预览缓冲圈效果。
  地图：高德地图 2D（AMap 2.0），每架模拟无人机渲染一个可配置半径的缓冲圆。
-->
<template>
  <div class="buffer-config-page">
    <!-- 左侧配置面板 -->
    <aside class="config-panel">
      <div class="panel-header">
        <span class="panel-icon">🛡️</span>
        <h2>安全范围配置</h2>
      </div>

      <div class="section">
        <h3 class="section-title">水平安全距离</h3>
        <div class="param-row">
          <span>缓冲半径</span>
          <el-slider v-model="config.horizontalBuffer" :min="10" :max="500" :step="10"
            show-input input-size="small" @change="updateCircles" />
          <span class="unit">米</span>
        </div>
        <div class="param-row">
          <span>风险阈值（中）</span>
          <el-slider v-model="config.warnDistance" :min="50" :max="800" :step="10"
            show-input input-size="small" @change="updateCircles" />
          <span class="unit">米</span>
        </div>
      </div>

      <div class="section">
        <h3 class="section-title">垂直安全距离</h3>
        <div class="param-row">
          <span>垂直间隔</span>
          <el-slider v-model="config.verticalBuffer" :min="5" :max="100" :step="5"
            show-input input-size="small" />
          <span class="unit">米</span>
        </div>
      </div>

      <div class="section">
        <h3 class="section-title">风险等级阈值</h3>
        <div class="threshold-item" v-for="t in thresholds" :key="t.level">
          <span class="dot" :style="{ background: t.color }"></span>
          <span class="level-name">{{ t.name }}</span>
          <el-input-number v-model="t.value" :min="1" :max="1000" :step="10"
            size="small" @change="updateCircles" style="width:120px" />
          <span class="unit">米</span>
        </div>
      </div>

      <div class="section">
        <h3 class="section-title">模拟无人机</h3>
        <div v-for="drone in drones" :key="drone.id" class="drone-item">
          <span class="drone-icon">🚁</span>
          <span class="drone-name">{{ drone.name }}</span>
          <el-tag size="small" :type="drone.statusType">{{ drone.status }}</el-tag>
        </div>
      </div>

      <div class="section">
        <el-button type="primary" style="width:100%" @click="applyConfig">
          应用配置
        </el-button>
        <el-button style="width:100%;margin-top:8px" @click="resetConfig">
          恢复默认
        </el-button>
      </div>
    </aside>

    <!-- 右侧地图 -->
    <div class="map-area">
      <div ref="mapRef" class="map-container"></div>
      <!-- 图例 -->
      <div class="map-legend">
        <div class="legend-title">缓冲圈图例</div>
        <div class="legend-item"><span class="legend-color" style="background:#3b82f6;opacity:.3"></span>安全缓冲区（{{ config.horizontalBuffer }}m）</div>
        <div class="legend-item"><span class="legend-color" style="background:#f59e0b;opacity:.3"></span>警戒区（{{ config.warnDistance }}m）</div>
        <div class="legend-item"><span class="legend-color" style="background:#dc2626;opacity:.3"></span>危险区（{{ thresholds[2].value }}m）</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import AMapLoader from '@amap/amap-jsapi-loader'
import { ElMessage } from 'element-plus'

// ── 模拟无人机数据（广州市内6架无人机） ──────────
const drones = ref([
  { id: 1, name: 'GZ-A001', lng: 113.3245, lat: 23.1201, status: '飞行中', statusType: 'success' },
  { id: 2, name: 'GZ-A002', lng: 113.2994, lat: 23.1540, status: '飞行中', statusType: 'success' },
  { id: 3, name: 'GZ-B001', lng: 113.3580, lat: 23.1050, status: '悬停', statusType: 'warning' },
  { id: 4, name: 'GZ-B002', lng: 113.2671, lat: 23.0900, status: '飞行中', statusType: 'success' },
  { id: 5, name: 'GZ-C001', lng: 113.3900, lat: 23.1380, status: '返航中', statusType: 'info' },
  { id: 6, name: 'GZ-C002', lng: 113.3100, lat: 23.0750, status: '飞行中', statusType: 'success' },
])

// ── 安全配置参数 ──────────────────────────────────
const config = reactive({ horizontalBuffer: 100, warnDistance: 300, verticalBuffer: 20 })

const thresholds = reactive([
  { level: 'low', name: '低风险', value: 500, color: '#16a34a' },
  { level: 'medium', name: '中风险', value: 300, color: '#f59e0b' },
  { level: 'high', name: '高风险', value: 100, color: '#dc2626' },
])

// ── AMap 实例 ─────────────────────────────────────
let AMap = null, map = null
const mapRef = ref(null)
// 每架无人机的圆圈和标记存在这里
const droneOverlays = {}

async function initMap() {
  const key = import.meta.env.VITE_AMAP_KEY
  const sec = import.meta.env.VITE_AMAP_SECURITY_CODE
  window._AMapSecurityConfig = { securityJsCode: sec }
  try {
    AMap = await AMapLoader.load({
      key, version: '2.0',
      plugins: ['AMap.Scale', 'AMap.GeometryUtil'],
    })
    map = new AMap.Map(mapRef.value, {
      viewMode: '2D', zoom: 12,
      center: [113.3244, 23.1201],
      mapStyle: 'amap://styles/whitesmoke',
    })
    map.addControl(new AMap.Scale({ position: 'LB' }))
    renderDrones()
  } catch (e) {
    console.error('AMap load failed:', e)
  }
}

// 在地图上渲染每架无人机的缓冲圆圈和标记
function renderDrones() {
  if (!map || !AMap) return
  // 清除旧覆盖物
  Object.values(droneOverlays).forEach(o => { map.remove(o.circles); map.remove(o.marker) })

  drones.value.forEach(d => {
    const pos = new AMap.LngLat(d.lng, d.lat)

    // 危险圈（红）
    const dangerCircle = new AMap.Circle({
      center: pos, radius: thresholds[2].value,
      strokeColor: '#dc2626', strokeWeight: 1, strokeOpacity: 0.6,
      fillColor: '#dc2626', fillOpacity: 0.08,
    })
    // 警戒圈（橙）
    const warnCircle = new AMap.Circle({
      center: pos, radius: config.warnDistance,
      strokeColor: '#f59e0b', strokeWeight: 1.5, strokeOpacity: 0.7,
      fillColor: '#f59e0b', fillOpacity: 0.08,
    })
    // 安全缓冲圈（蓝）
    const safeCircle = new AMap.Circle({
      center: pos, radius: config.horizontalBuffer,
      strokeColor: '#3b82f6', strokeWeight: 2, strokeOpacity: 0.9,
      fillColor: '#3b82f6', fillOpacity: 0.15,
    })

    // 无人机标记
    const marker = new AMap.Marker({
      position: pos,
      content: `<div style="background:#1e40af;color:#fff;padding:3px 6px;border-radius:4px;font-size:11px;white-space:nowrap;box-shadow:0 1px 4px rgba(0,0,0,0.3)">🚁 ${d.name}</div>`,
      offset: new AMap.Pixel(-24, -12),
    })

    const circles = [dangerCircle, warnCircle, safeCircle]
    map.add(circles)
    map.add(marker)
    droneOverlays[d.id] = { circles, marker }
  })
}

function updateCircles() { renderDrones() }

function applyConfig() {
  renderDrones()
  ElMessage.success(`安全配置已应用：水平缓冲 ${config.horizontalBuffer}m，垂直间隔 ${config.verticalBuffer}m`)
}

function resetConfig() {
  config.horizontalBuffer = 100
  config.warnDistance = 300
  config.verticalBuffer = 20
  thresholds[0].value = 500
  thresholds[1].value = 300
  thresholds[2].value = 100
  renderDrones()
  ElMessage.info('已恢复默认配置')
}

onMounted(initMap)
onUnmounted(() => { map?.destroy() })
</script>

<style scoped>
.buffer-config-page { display: flex; height: 100%; overflow: hidden; }

.config-panel {
  width: 300px; flex-shrink: 0; background: #fff; border-right: 1px solid #e5e7eb;
  overflow-y: auto; padding: 16px;
}
.panel-header { display: flex; align-items: center; gap: 8px; margin-bottom: 16px; }
.panel-header h2 { font-size: 16px; font-weight: 700; color: #111827; margin: 0; }
.panel-icon { font-size: 20px; }
.section { border-top: 1px solid #f3f4f6; padding-top: 14px; margin-bottom: 14px; }
.section-title { font-size: 13px; font-weight: 600; color: #374151; margin: 0 0 10px; }
.param-row { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; flex-wrap: wrap; }
.param-row > span:first-child { font-size: 12px; color: #6b7280; width: 90px; flex-shrink: 0; }
.unit { font-size: 12px; color: #9ca3af; }
.threshold-item { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
.level-name { font-size: 12px; color: #374151; width: 50px; }
.drone-item { display: flex; align-items: center; gap: 8px; padding: 4px 0; }
.drone-icon { font-size: 14px; }
.drone-name { font-size: 12px; color: #374151; flex: 1; }

.map-area { flex: 1; position: relative; }
.map-container { width: 100%; height: 100%; }
.map-legend {
  position: absolute; bottom: 24px; right: 16px;
  background: rgba(255,255,255,0.95); border-radius: 8px;
  padding: 12px 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.15);
  font-size: 12px;
}
.legend-title { font-weight: 600; color: #374151; margin-bottom: 6px; }
.legend-item { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; color: #6b7280; }
.legend-color { width: 20px; height: 12px; border-radius: 2px; flex-shrink: 0; }
</style>
