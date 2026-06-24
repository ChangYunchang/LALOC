<!--
  安全风险热力分析（6.3）— 6.3.3 热力图展示
  2D：AMap + HeatMap 插件，时间段/时间轴动画
-->
<template>
  <div class="density-contour-page">
    <!-- 顶部控制栏 -->
    <div class="top-bar">
      <div class="control-group">
        <span class="ctrl-label">分析时段：</span>
        <el-select v-model="selectedPeriod" size="small" style="width:160px" @change="onPeriodChange">
          <el-option v-for="p in timePeriods" :key="p.value" :label="p.label" :value="p.value" />
        </el-select>
      </div>
      <div class="control-group">
        <span class="ctrl-label">时间点（分钟）：</span>
        <el-slider v-model="currentMinute" :min="0" :max="maxMinute" :step="5"
          style="width:200px" @change="onTimeChange" />
        <span class="ctrl-label" style="margin-left:8px">{{ currentMinute }}min</span>
      </div>
      <div v-if="viewMode === '2D'" class="control-group">
        <span class="ctrl-label">透明度：</span>
        <el-slider v-model="opacity" :min="10" :max="100" :step="5" style="width:120px" @change="updateOpacity" />
      </div>
      <div class="control-group">
        <el-button size="small" @click="togglePlay">{{ playing ? '⏸ 暂停' : '▶ 自动播放' }}</el-button>
        <el-button size="small" @click="resetPlay">⏮ 重置</el-button>
      </div>
    </div>

    <!-- 地图容器区域 -->
    <div class="map-area">
      <!-- AMap 2D 热力图 -->
      <div ref="mapRef" class="map-container"></div>

      <!-- 图例 -->
      <div class="legend">
        <div class="legend-title">飞行密度</div>
        <div class="legend-gradient"></div>
        <div class="legend-labels"><span>低</span><span>中</span><span>高</span></div>
      </div>

      <!-- 时刻信息牌 -->
      <div class="time-badge">
        {{ periodLabel }} · T={{ currentMinute }}min
        <div class="time-sub">已加载 {{ heatPointCount }} 个密度采样点</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import AMapLoader from '@amap/amap-jsapi-loader'
import { DENSITY_ROUTES, SAMPLE_ROUTES } from '@/data/sampleRoutes'

// ── 时段配置 ─────────────────────────────────────────
const timePeriods = [
  { value: 'morning', label: '早高峰（08:00-10:00）', duration: 120 },
  { value: 'noon', label: '午间（11:00-13:00）', duration: 120 },
  { value: 'afternoon', label: '下午（14:00-18:00）', duration: 240 },
  { value: 'evening', label: '晚高峰（18:00-20:00）', duration: 120 },
]
const selectedPeriod = ref('morning')
const currentMinute = ref(0)
const maxMinute = ref(120)
const opacity = ref(70)
const playing = ref(false)
const heatPointCount = ref(0)

const periodLabel = computed(() => timePeriods.find(p => p.value === selectedPeriod.value)?.label || '')

const ROUTES = DENSITY_ROUTES

// ── 密度因子 ─────────────────────────────────────────
function getPeakFactor(t) {
  const total = timePeriods.find(p => p.value === selectedPeriod.value)?.duration || 120
  const r = t / total
  return 1 - Math.abs((r - 0.5) * 2) * 0.4
}
function getPeriodFactor() {
  return selectedPeriod.value === 'evening' ? 1.2 : selectedPeriod.value === 'morning' ? 1.1 : 0.9
}

// ── 2D：热力点生成（沿航线走廊带随机变异的采样） ──────
// 设计目标：
//   1. 步长 ~0.003°（≈300m），避免肉眼可见的均匀点阵
//   2. 每个点叠加 ±40% 随机变异，消除机械均匀感
//   3. 走廊扩散点稀疏（约 50% 概率）且偏移较大，模拟实际飞行轨迹漂移
//   4. 低 w 航线段在时间窗外自然变暗，交叉口靠多航线叠加变红
function generateHeatPoints(t) {
  const pf = getPeakFactor(t), ef = getPeriodFactor()
  const pts = []
  ROUTES.forEach(route => {
    for (let i = 0; i < route.pts.length - 1; i++) {
      const [x1, y1] = route.pts[i], [x2, y2] = route.pts[i + 1]
      const dist = Math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
      // 步长 0.003°（~300m），比之前少 2 倍点数
      const steps = Math.max(3, Math.ceil(dist / 0.003))
      for (let k = 0; k <= steps; k++) {
        const f = k / steps
        const lng = x1 + (x2 - x1) * f
        const lat = y1 + (y2 - y1) * f
        // 随机变异：同一条航线也有冷热区段
        const noise = 0.55 + Math.random() * 0.45
        const w = route.w * pf * ef * noise
        pts.push({ lng, lat, count: w })
        // 走廊扩散：随机决定是否生成，避免等距散点
        if (Math.random() > 0.45) {
          pts.push({
            lng: lng + (Math.random() - 0.5) * 0.009,
            lat: lat + (Math.random() - 0.5) * 0.009,
            count: w * (0.18 + Math.random() * 0.28),
          })
        }
      }
    }
  })
  return pts
}

// ── AMap 实例 ─────────────────────────────────────────
let AMap = null, amapInst = null, heatmapLayer = null
let routeLineOverlays2D = []
const mapRef = ref(null)

// 在热力图下方绘制航线走廊参考线（虚线，不遮挡热力图）
function drawRouteLines2D() {
  if (!amapInst || !AMap) return
  routeLineOverlays2D.forEach(o => amapInst.remove(o))
  routeLineOverlays2D = []
  SAMPLE_ROUTES.forEach(route => {
    const line = new AMap.Polyline({
      path: route.pts.map(([lng, lat]) => [lng, lat]),
      strokeColor: route.color,
      strokeWeight: 2,
      strokeOpacity: 0.5,
      strokeStyle: 'dashed',
      strokeDasharray: [6, 4],
      lineJoin: 'round',
      lineCap: 'round',
      zIndex: 10,
    })
    amapInst.add(line)
    routeLineOverlays2D.push(line)
    // 在起终点加小标注
    ;[route.pts[0], route.pts[route.pts.length - 1]].forEach(([lng, lat]) => {
      const dot = new AMap.CircleMarker({ center: [lng, lat], radius: 3, strokeColor: route.color, strokeWeight: 1, fillColor: route.color, fillOpacity: 0.8, zIndex: 20 })
      amapInst.add(dot)
      routeLineOverlays2D.push(dot)
    })
  })
}

async function initAMap() {
  if (!mapRef.value) return
  window._AMapSecurityConfig = { securityJsCode: import.meta.env.VITE_AMAP_SECURITY_CODE }
  try {
    if (!AMap) AMap = await AMapLoader.load({ key: import.meta.env.VITE_AMAP_KEY, version: '2.0', plugins: ['AMap.Scale', 'AMap.HeatMap'] })
    amapInst = new AMap.Map(mapRef.value, {
      viewMode: '2D', zoom: 12,
      center: [113.3100, 23.1150],
      mapStyle: 'amap://styles/whitesmoke',
    })
    amapInst.addControl(new AMap.Scale({ position: 'LB' }))
    drawRouteLines2D()
    heatmapLayer = new AMap.HeatMap(amapInst, {
      radius: 40,
      opacity: [0, opacity.value / 100],
      gradient: { 0: '#3b82f6', 0.35: '#22d3ee', 0.65: '#fbbf24', 0.85: '#f97316', 1: '#dc2626' },
    })
    updateHeatmap(currentMinute.value)
  } catch (e) { console.error('AMap init failed:', e) }
}

function destroyAMap() {
  heatmapLayer = null
  routeLineOverlays2D = []
  amapInst?.destroy()
  amapInst = null
}

function updateHeatmap(t) {
  if (!heatmapLayer) return
  const pts = generateHeatPoints(t)
  heatPointCount.value = pts.length
  // max=0.72：单条主干航线峰值约 0.82×1×1.1×1.0 ≈ 0.9，超过 0.72 才显红
  // 低频航线（w≈0.3）峰值约 0.3×1.1 ≈ 0.33，显蓝绿
  // 多航线交叉口叠加后突破 0.72 → 红色热点
  heatmapLayer.setDataSet({ data: pts.map(p => ({ lng: p.lng, lat: p.lat, count: p.count })), max: 0.72 })
}

function updateOpacity() {
  heatmapLayer?.setOptions({ opacity: [0, opacity.value / 100] })
}

// ── 控制回调 ─────────────────────────────────────────
function onTimeChange(val) {
  updateHeatmap(val)
}

function onPeriodChange() {
  const p = timePeriods.find(t => t.value === selectedPeriod.value)
  maxMinute.value = p.duration
  currentMinute.value = 0
  updateHeatmap(0)
}

let playTimer = null
function togglePlay() {
  if (playing.value) { clearInterval(playTimer); playing.value = false }
  else {
    playing.value = true
    playTimer = setInterval(() => {
      if (currentMinute.value >= maxMinute.value) { clearInterval(playTimer); playing.value = false; return }
      currentMinute.value += 5
      updateHeatmap(currentMinute.value)
    }, 500)
  }
}
function resetPlay() {
  clearInterval(playTimer); playing.value = false; currentMinute.value = 0
  updateHeatmap(0)
}

onMounted(() => {
  initAMap()
})

onUnmounted(() => {
  clearInterval(playTimer)
  destroyAMap()
})
</script>

<style scoped>
.density-contour-page { display: flex; flex-direction: column; height: 100%; overflow: hidden; }
.top-bar {
  display: flex; align-items: center; gap: 20px; flex-wrap: wrap;
  padding: 10px 16px; background: #fff; border-bottom: 1px solid #e5e7eb; flex-shrink: 0;
}
.control-group { display: flex; align-items: center; gap: 8px; }
.ctrl-label { font-size: 13px; color: #374151; white-space: nowrap; }
.map-area { flex: 1; position: relative; overflow: hidden; }
.map-container { width: 100%; height: 100%; }
.legend {
  position: absolute; bottom: 24px; right: 16px; background: rgba(255,255,255,0.95);
  border-radius: 8px; padding: 10px 14px; box-shadow: 0 2px 8px rgba(0,0,0,0.15); font-size: 12px; z-index: 100;
}
.legend-title { font-weight: 600; color: #374151; margin-bottom: 6px; }
.legend-gradient {
  width: 140px; height: 10px; border-radius: 5px;
  background: linear-gradient(to right, #3b82f6, #22d3ee, #fbbf24, #dc2626); margin-bottom: 4px;
}
.legend-labels { display: flex; justify-content: space-between; color: #6b7280; }
.time-badge {
  position: absolute; top: 12px; left: 16px; background: rgba(255,255,255,0.95);
  border-radius: 8px; padding: 8px 14px; font-size: 13px; font-weight: 600;
  color: #1e40af; box-shadow: 0 2px 8px rgba(0,0,0,0.12); z-index: 100;
}
.time-sub { font-size: 11px; color: #6b7280; font-weight: 400; margin-top: 2px; }
</style>
