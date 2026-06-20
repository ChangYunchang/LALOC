<!--
  安全风险热力分析（6.3）— 6.3.3 热力图展示
  2D：AMap + HeatMap 插件，时间段/时间轴动画
  3D：Cesium OSM 建筑场景 + 密度柱体实体
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
      <div class="control-group mode-toggle">
        <el-button-group size="small">
          <el-button :type="viewMode === '2D' ? 'primary' : 'default'" @click="switchMode('2D')">2D 平面</el-button>
          <el-button :type="viewMode === '3D' ? 'primary' : 'default'" @click="switchMode('3D')">3D 实景</el-button>
        </el-button-group>
      </div>
    </div>

    <!-- 地图容器区域 -->
    <div class="map-area">
      <!-- AMap 2D 热力图 -->
      <div v-if="viewMode === '2D'" ref="mapRef" class="map-container"></div>
      <!-- Cesium 3D 密度柱体 -->
      <div v-if="viewMode === '3D'" ref="cesiumRef" class="map-container"></div>

      <!-- 图例（两种模式共用） -->
      <div class="legend">
        <div class="legend-title">飞行密度</div>
        <div class="legend-gradient"></div>
        <div class="legend-labels"><span>低</span><span>中</span><span>高</span></div>
      </div>

      <!-- 时刻信息牌 -->
      <div class="time-badge">
        {{ periodLabel }} · T={{ currentMinute }}min
        <div class="time-sub" v-if="viewMode === '2D'">已加载 {{ heatPointCount }} 个密度采样点</div>
        <div class="time-sub" v-else>3D 密度柱体：{{ columnCount }} 个节点</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onUnmounted, nextTick } from 'vue'
import AMapLoader from '@amap/amap-jsapi-loader'

let Cesium = null
async function loadCesium() {
  if (Cesium) return Cesium
  window.CESIUM_BASE_URL = '/cesium/'
  if (!document.querySelector('link[data-cesium]')) {
    const link = document.createElement('link')
    link.rel = 'stylesheet'
    link.href = '/cesium/Widgets/widgets.css'
    link.setAttribute('data-cesium', '1')
    document.head.appendChild(link)
  }
  if (!window.Cesium) {
    await new Promise((resolve, reject) => {
      if (document.querySelector('script[data-cesium]')) { resolve(); return }
      const script = document.createElement('script')
      script.src = '/cesium/Cesium.js'
      script.setAttribute('data-cesium', '1')
      script.onload = resolve
      script.onerror = () => reject(new Error('Cesium.js load failed'))
      document.head.appendChild(script)
    })
  }
  Cesium = window.Cesium
  return Cesium
}

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
const viewMode = ref('2D')
const heatPointCount = ref(0)
const columnCount = ref(0)

const periodLabel = computed(() => timePeriods.find(p => p.value === selectedPeriod.value)?.label || '')

// ── 航迹核心数据（9条命名航线） ──────────────────────
// 这套路由与 HotspotAnalysis.vue 共享同一地理骨架。
// 热力点、热点交叉、统计数据都从此派生，保证三个页面数据一致。
// w 值代表该航线的基础流量等级：
//   主干走廊（0.7-0.85）、中频支线（0.45-0.6）、低频末段（0.25-0.38）
// 差异化的 w + 随机变异才能让热力图出现冷暖分区，不至于全红
const ROUTES = [
  { id: 0, name: '番禺→天河干线', pts: [[113.2671,23.0900],[113.2900,23.0980],[113.3100,23.1050],[113.3245,23.1201]], w: 0.82, color: '#3b82f6' },
  { id: 1, name: '白云→天河横线', pts: [[113.2994,23.1540],[113.3100,23.1380],[113.3245,23.1201],[113.3400,23.1050]], w: 0.60, color: '#8b5cf6' },
  { id: 2, name: '黄埔→白云线',   pts: [[113.3580,23.1050],[113.3400,23.1201],[113.3245,23.1201],[113.3100,23.1050]], w: 0.50, color: '#10b981' },
  { id: 3, name: '南沙→黄埔线',   pts: [[113.3900,23.1380],[113.3700,23.1300],[113.3580,23.1050],[113.3400,23.0900]], w: 0.32, color: '#f59e0b' },
  { id: 4, name: '荔湾→天河线',   pts: [[113.2671,23.1380],[113.2800,23.1250],[113.3100,23.1201],[113.3245,23.1050]], w: 0.48, color: '#ec4899' },
  { id: 5, name: '越秀纵向线',     pts: [[113.3100,23.0750],[113.3100,23.1050],[113.3100,23.1380],[113.3100,23.1600]], w: 0.75, color: '#06b6d4' },
  { id: 6, name: '白云横向线',     pts: [[113.2500,23.1050],[113.2671,23.1050],[113.2994,23.1050],[113.3245,23.1050]], w: 0.38, color: '#f97316' },
  { id: 7, name: '天河→黄埔线',   pts: [[113.3245,23.1201],[113.3400,23.1380],[113.3580,23.1500],[113.3800,23.1600]], w: 0.27, color: '#64748b' },
  { id: 8, name: '番禺→天河南线', pts: [[113.2994,23.0750],[113.3100,23.0900],[113.3245,23.1050],[113.3400,23.1201]], w: 0.44, color: '#dc2626' },
]

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
  ROUTES.forEach(route => {
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

// ── Cesium 3D ────────────────────────────────────────
let cesiumViewer = null
const cesiumRef = ref(null)

function densityColor(d) {
  if (d > 0.85) return Cesium.Color.fromCssColorString('#dc2626').withAlpha(0.85)
  if (d > 0.70) return Cesium.Color.fromCssColorString('#f97316').withAlpha(0.85)
  if (d > 0.55) return Cesium.Color.fromCssColorString('#fbbf24').withAlpha(0.80)
  if (d > 0.40) return Cesium.Color.fromCssColorString('#22d3ee').withAlpha(0.75)
  return Cesium.Color.fromCssColorString('#3b82f6').withAlpha(0.75)
}

async function initCesium() {
  if (!cesiumRef.value) return
  await loadCesium()
  Cesium.Ion.defaultAccessToken = import.meta.env.VITE_CESIUM_ION_TOKEN
  cesiumViewer = new Cesium.Viewer(cesiumRef.value, {
    terrain: Cesium.Terrain.fromWorldTerrain(),
    baseLayerPicker: false, geocoder: false, homeButton: false,
    sceneModePicker: false, navigationHelpButton: false,
    animation: false, timeline: false, fullscreenButton: false,
    infoBox: false, selectionIndicator: false,
  })
  try {
    const tileset = await Cesium.createOsmBuildingsAsync()
    cesiumViewer.scene.primitives.add(tileset)
  } catch {}
  cesiumViewer.camera.setView({
    destination: Cesium.Cartesian3.fromDegrees(113.3100, 23.1150, 9000),
    orientation: { heading: 0, pitch: Cesium.Math.toRadians(-50), roll: 0 },
  })
  render3DColumns()
}

function render3DColumns() {
  if (!cesiumViewer) return
  cesiumViewer.entities.removeAll()
  const pf = getPeakFactor(currentMinute.value)
  const ef = getPeriodFactor()
  let count = 0

  // 先绘制航线走廊参考线（低空 60m，彩色半透明）
  ROUTES.forEach(route => {
    const positions = route.pts.flatMap(([lng, lat]) => [lng, lat, 60])
    cesiumViewer.entities.add({
      polyline: {
        positions: Cesium.Cartesian3.fromDegreesArrayHeights(positions),
        width: 3,
        material: new Cesium.PolylineDashMaterialProperty({
          color: Cesium.Color.fromCssColorString(route.color).withAlpha(0.55),
          dashLength: 16,
        }),
        clampToGround: false,
      },
    })
  })

  // 再绘制密度柱体（沿航线节点，高度 = 密度）
  ROUTES.forEach(route => {
    route.pts.forEach(([lng, lat]) => {
      const density = route.w * pf * ef
      const h = Math.max(30, density * 260)
      cesiumViewer.entities.add({
        position: Cesium.Cartesian3.fromDegrees(lng, lat, h / 2),
        cylinder: {
          length: h,
          topRadius: 85,
          bottomRadius: 85,
          material: densityColor(density),
          outline: false,
        },
      })
      count++
    })
  })
  columnCount.value = count
  cesiumViewer.scene.requestRender()
}

function destroyCesium() {
  if (cesiumViewer && !cesiumViewer.isDestroyed()) cesiumViewer.destroy()
  cesiumViewer = null
}

// ── 模式切换 ─────────────────────────────────────────
function switchMode(mode) {
  if (viewMode.value === mode) return
  if (playing.value) { clearInterval(playTimer); playing.value = false }
  if (mode === '3D') {
    destroyAMap()
    viewMode.value = '3D'
  } else {
    destroyCesium()
    viewMode.value = '2D'
  }
}

watch(mapRef, async (el) => { if (el) { await nextTick(); initAMap() } })
watch(cesiumRef, async (el) => { if (el) { await nextTick(); initCesium() } })

// ── 控制回调 ─────────────────────────────────────────
function onTimeChange(val) {
  if (viewMode.value === '2D') updateHeatmap(val)
  else render3DColumns()
}

function onPeriodChange() {
  const p = timePeriods.find(t => t.value === selectedPeriod.value)
  maxMinute.value = p.duration
  currentMinute.value = 0
  if (viewMode.value === '2D') updateHeatmap(0)
  else render3DColumns()
}

let playTimer = null
function togglePlay() {
  if (playing.value) { clearInterval(playTimer); playing.value = false }
  else {
    playing.value = true
    playTimer = setInterval(() => {
      if (currentMinute.value >= maxMinute.value) { clearInterval(playTimer); playing.value = false; return }
      currentMinute.value += 5
      if (viewMode.value === '2D') updateHeatmap(currentMinute.value)
      else render3DColumns()
    }, 500)
  }
}
function resetPlay() {
  clearInterval(playTimer); playing.value = false; currentMinute.value = 0
  if (viewMode.value === '2D') updateHeatmap(0)
  else render3DColumns()
}

onUnmounted(() => {
  clearInterval(playTimer)
  destroyAMap()
  destroyCesium()
})
</script>

<style scoped>
.density-contour-page { display: flex; flex-direction: column; height: 100%; overflow: hidden; }
.top-bar {
  display: flex; align-items: center; gap: 20px; flex-wrap: wrap;
  padding: 10px 16px; background: #fff; border-bottom: 1px solid #e5e7eb; flex-shrink: 0;
}
.control-group { display: flex; align-items: center; gap: 8px; }
.mode-toggle { margin-left: auto; }
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
