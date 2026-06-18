<!--
  低空拥堵识别（6.2）— 6.2.1 任务密度计算 / 6.2.2 拥堵阈值判断
  2D：AMap 彩色热点圆 + 信息窗口
  3D：Cesium OSM 建筑场景 + 密度柱体实体
-->
<template>
  <div class="hotspot-page">
    <!-- 左侧控制面板 -->
    <aside class="control-panel">
      <div class="panel-header">
        <span>📍</span>
        <h2>低空拥堵识别</h2>
      </div>

      <div class="section">
        <h3 class="section-title">分析参数</h3>
        <div class="param-row">
          <span>密度阈值（次/时）</span>
          <el-input-number v-model="densityThreshold" :min="5" :max="100" :step="5" size="small" style="width:110px" />
        </div>
        <div class="param-row">
          <span>热点半径（米）</span>
          <el-input-number v-model="hotspotRadius" :min="100" :max="2000" :step="100" size="small" style="width:110px" />
        </div>
        <div class="param-row">
          <span>分析时段</span>
          <el-select v-model="selectedPeriod" size="small" style="width:130px">
            <el-option label="全天" value="all" />
            <el-option label="早高峰" value="morning" />
            <el-option label="午间" value="noon" />
            <el-option label="晚高峰" value="evening" />
          </el-select>
        </div>
        <el-button type="primary" style="width:100%;margin-top:8px" @click="runAnalysis">
          识别拥堵区域
        </el-button>
      </div>

      <div class="section">
        <h3 class="section-title">拥堵区域列表</h3>
        <div class="stats-bar">
          <span>共识别 <strong>{{ hotspots.length }}</strong> 个热点</span>
          <span class="high-count">高密度：{{ hotspots.filter(h => h.level === 'high').length }} 个</span>
        </div>
        <div v-for="hs in hotspots" :key="hs.id" class="hotspot-item"
          :class="`level-${hs.level}`" @click="focusHotspot(hs)">
          <div class="hs-top">
            <span class="hs-name">{{ hs.name }}</span>
            <el-tag :type="hs.level === 'high' ? 'danger' : hs.level === 'medium' ? 'warning' : 'info'" size="small">
              {{ hs.level === 'high' ? '高密度' : hs.level === 'medium' ? '中密度' : '低密度' }}
            </el-tag>
          </div>
          <div class="hs-detail">
            <div class="hs-stat"><span>过境次数</span><strong>{{ hs.count }}次/时</strong></div>
            <div class="hs-stat"><span>涉及航线</span><strong>{{ hs.routes }}条</strong></div>
            <div class="hs-stat"><span>高峰时段</span><strong>{{ hs.peak }}</strong></div>
            <div class="hs-stat"><span>区域坐标</span><strong>{{ hs.coordStr }}</strong></div>
          </div>
        </div>
        <div v-if="!hotspots.length" class="empty-tip">点击「识别拥堵区域」开始分析</div>
      </div>
    </aside>

    <!-- 右侧地图 -->
    <div class="map-area">
      <!-- 2D/3D 切换 -->
      <div class="mode-toggle">
        <el-button-group size="small">
          <el-button :type="viewMode === '2D' ? 'primary' : 'default'" @click="switchMode('2D')">2D 平面</el-button>
          <el-button :type="viewMode === '3D' ? 'primary' : 'default'" @click="switchMode('3D')">3D 实景</el-button>
        </el-button-group>
      </div>

      <!-- AMap 2D -->
      <div v-if="viewMode === '2D'" ref="mapRef" class="map-container"></div>
      <!-- Cesium 3D -->
      <div v-if="viewMode === '3D'" ref="cesiumRef" class="map-container"></div>

      <div v-if="hotspots.length" class="map-summary">
        高峰期最大过境密度：<strong>{{ maxDensity }}</strong> 次/时
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onUnmounted, nextTick } from 'vue'
import AMapLoader from '@amap/amap-jsapi-loader'
import { ElMessage } from 'element-plus'

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

const densityThreshold = ref(20)
const hotspotRadius = ref(500)
const selectedPeriod = ref('all')
const hotspots = ref([])
const viewMode = ref('2D')
const mapRef = ref(null)
const cesiumRef = ref(null)
let AMap = null, amapInst = null, infoWindow = null
let overlays = []
let cesiumViewer = null

const HOTSPOT_DEFINITIONS = [
  { id: 1, name: '天河中心枢纽', lng: 113.3245, lat: 23.1201, baseCount: { all: 68, morning: 85, noon: 42, evening: 91 }, routes: 6, peak: '18:00-19:00', level: 'high' },
  { id: 2, name: '白云东路交汇点', lng: 113.3100, lat: 23.1050, baseCount: { all: 54, morning: 72, noon: 38, evening: 76 }, routes: 5, peak: '08:30-09:30', level: 'high' },
  { id: 3, name: '荔湾航路交叉区', lng: 113.2994, lat: 23.1380, baseCount: { all: 41, morning: 55, noon: 28, evening: 60 }, routes: 4, peak: '08:00-10:00', level: 'medium' },
  { id: 4, name: '番禺物流节点', lng: 113.2671, lat: 23.0900, baseCount: { all: 37, morning: 48, noon: 30, evening: 52 }, routes: 3, peak: '14:00-16:00', level: 'medium' },
  { id: 5, name: '黄埔东部走廊', lng: 113.3580, lat: 23.1050, baseCount: { all: 29, morning: 38, noon: 22, evening: 44 }, routes: 3, peak: '09:00-10:00', level: 'medium' },
  { id: 6, name: '越秀纵向通道', lng: 113.3100, lat: 23.1380, baseCount: { all: 25, morning: 32, noon: 18, evening: 38 }, routes: 3, peak: '18:30-19:30', level: 'medium' },
  { id: 7, name: '南沙新区起降点', lng: 113.3900, lat: 23.1380, baseCount: { all: 18, morning: 22, noon: 14, evening: 26 }, routes: 2, peak: '10:00-11:00', level: 'low' },
  { id: 8, name: '海珠低密区', lng: 113.2671, lat: 23.1050, baseCount: { all: 12, morning: 16, noon: 10, evening: 18 }, routes: 2, peak: '14:00-15:00', level: 'low' },
]

const maxDensity = computed(() => hotspots.value.length ? Math.max(...hotspots.value.map(h => h.count)) : 0)

// ── 分析逻辑 ─────────────────────────────────────────
function runAnalysis() {
  const period = selectedPeriod.value
  const filtered = HOTSPOT_DEFINITIONS
    .map(def => ({ ...def, count: def.baseCount[period], coordStr: `${def.lng.toFixed(4)}, ${def.lat.toFixed(4)}` }))
    .filter(hs => hs.count >= densityThreshold.value)
    .sort((a, b) => b.count - a.count)

  hotspots.value = filtered
  if (viewMode.value === '2D') renderHotspots2D(filtered)
  else renderHotspots3D(filtered)

  ElMessage({ type: 'success', message: `识别到 ${filtered.length} 个拥堵区域（阈值 ≥ ${densityThreshold.value} 次/时）` })
}

// ── AMap 2D 渲染 ──────────────────────────────────────
function clearOverlays() {
  overlays.forEach(o => amapInst?.remove(o))
  overlays = []
  infoWindow?.close()
}

function renderHotspots2D(list) {
  if (!amapInst || !AMap) return
  clearOverlays()
  list.forEach(hs => {
    const colorMap = { high: '#dc2626', medium: '#f59e0b', low: '#3b82f6' }
    const color = colorMap[hs.level]
    const maxCount = Math.max(...list.map(h => h.count))
    const radiusScale = 0.6 + (hs.count / maxCount) * 0.4

    const circle = new AMap.Circle({
      center: [hs.lng, hs.lat], radius: hotspotRadius.value * radiusScale,
      strokeColor: color, strokeWeight: 2, strokeOpacity: 0.9,
      fillColor: color, fillOpacity: 0.2,
    })
    amapInst.add(circle)
    overlays.push(circle)

    const marker = new AMap.Marker({
      position: [hs.lng, hs.lat],
      content: `<div style="background:${color};color:#fff;padding:4px 8px;border-radius:4px;font-size:11px;white-space:nowrap;font-weight:600;box-shadow:0 2px 6px rgba(0,0,0,0.2)">
        ${hs.count}次/时<br><span style="font-size:10px;font-weight:400">${hs.name}</span>
      </div>`,
      offset: new AMap.Pixel(-30, -32),
    })
    marker.on('click', () => {
      if (!infoWindow) infoWindow = new AMap.InfoWindow({ offset: new AMap.Pixel(0, -40), closeWhenClickMap: true })
      infoWindow.setContent(`
        <div style="padding:8px;font-size:12px;min-width:180px">
          <strong style="font-size:13px">${hs.name}</strong>
          <div style="margin-top:6px;color:#374151">
            <div>过境次数：<b>${hs.count}次/时</b></div>
            <div>涉及航线：<b>${hs.routes}条</b></div>
            <div>高峰时段：<b>${hs.peak}</b></div>
            <div>密度级别：<b style="color:${color}">${hs.level === 'high' ? '高密度' : hs.level === 'medium' ? '中密度' : '低密度'}</b></div>
          </div>
        </div>`)
      infoWindow.open(amapInst, [hs.lng, hs.lat])
    })
    amapInst.add(marker)
    overlays.push(marker)
  })
  if (list.length) { amapInst.setCenter([list[0].lng, list[0].lat]); amapInst.setZoom(12) }
}

async function initAMap() {
  if (!mapRef.value) return
  window._AMapSecurityConfig = { securityJsCode: import.meta.env.VITE_AMAP_SECURITY_CODE }
  try {
    if (!AMap) AMap = await AMapLoader.load({ key: import.meta.env.VITE_AMAP_KEY, version: '2.0', plugins: ['AMap.Scale', 'AMap.InfoWindow'] })
    amapInst = new AMap.Map(mapRef.value, {
      viewMode: '2D', zoom: 12,
      center: [113.3100, 23.1150],
      mapStyle: 'amap://styles/whitesmoke',
    })
    amapInst.addControl(new AMap.Scale({ position: 'LB' }))
    if (hotspots.value.length) renderHotspots2D(hotspots.value)
    else runAnalysis()
  } catch (e) { console.error('AMap init failed:', e) }
}

function destroyAMap() {
  infoWindow = null
  overlays = []
  amapInst?.destroy()
  amapInst = null
}

// ── Cesium 3D 渲染 ────────────────────────────────────
const LEVEL_COLORS = {
  high: '#dc2626',
  medium: '#f59e0b',
  low: '#3b82f6',
}

function renderHotspots3D(list) {
  if (!cesiumViewer) return
  cesiumViewer.entities.removeAll()
  if (!list.length) return

  const maxCount = Math.max(...list.map(h => h.count))
  list.forEach(hs => {
    const h = Math.max(40, (hs.count / maxCount) * 220)
    const color = Cesium.Color.fromCssColorString(LEVEL_COLORS[hs.level]).withAlpha(0.82)
    const r = hotspotRadius.value * 0.3

    // 密度柱体
    cesiumViewer.entities.add({
      position: Cesium.Cartesian3.fromDegrees(hs.lng, hs.lat, h / 2),
      cylinder: { length: h, topRadius: r, bottomRadius: r, material: color, outline: false },
    })
    // 柱顶标注
    cesiumViewer.entities.add({
      position: Cesium.Cartesian3.fromDegrees(hs.lng, hs.lat, h + 30),
      label: {
        text: `${hs.name}\n${hs.count}次/时`,
        font: '12px PingFang SC, sans-serif',
        fillColor: Cesium.Color.WHITE,
        style: Cesium.LabelStyle.FILL_AND_OUTLINE,
        outlineColor: Cesium.Color.BLACK,
        outlineWidth: 1,
        backgroundColor: color.withAlpha(0.75),
        showBackground: true,
        backgroundPadding: new Cesium.Cartesian2(5, 3),
        verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
        pixelOffset: new Cesium.Cartesian2(0, -4),
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
      },
    })
  })
  cesiumViewer.scene.requestRender()
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
  if (hotspots.value.length) renderHotspots3D(hotspots.value)
  else runAnalysis()
}

function destroyCesium() {
  if (cesiumViewer && !cesiumViewer.isDestroyed()) cesiumViewer.destroy()
  cesiumViewer = null
}

// ── 模式切换 ─────────────────────────────────────────
function switchMode(mode) {
  if (viewMode.value === mode) return
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

function focusHotspot(hs) {
  if (viewMode.value === '2D' && amapInst) {
    amapInst.setCenter([hs.lng, hs.lat])
    amapInst.setZoom(14)
  } else if (cesiumViewer) {
    cesiumViewer.camera.flyTo({
      destination: Cesium.Cartesian3.fromDegrees(hs.lng, hs.lat, 2000),
      orientation: { heading: 0, pitch: Cesium.Math.toRadians(-45), roll: 0 },
      duration: 1.5,
    })
  }
}

onUnmounted(() => {
  destroyAMap()
  destroyCesium()
})
</script>

<style scoped>
.hotspot-page { display: flex; height: 100%; overflow: hidden; }
.control-panel { width: 310px; flex-shrink: 0; background: #fff; border-right: 1px solid #e5e7eb; overflow-y: auto; padding: 16px; }
.panel-header { display: flex; align-items: center; gap: 8px; margin-bottom: 16px; font-size: 20px; }
.panel-header h2 { font-size: 15px; font-weight: 700; margin: 0; }
.section { border-top: 1px solid #f3f4f6; padding-top: 14px; margin-bottom: 12px; }
.section-title { font-size: 13px; font-weight: 600; color: #374151; margin: 0 0 10px; }
.param-row { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; font-size: 12px; color: #6b7280; flex-wrap: wrap; }
.param-row > span:first-child { width: 95px; flex-shrink: 0; }
.stats-bar { display: flex; justify-content: space-between; font-size: 12px; color: #6b7280; margin-bottom: 8px; }
.stats-bar strong { color: #1e40af; }
.high-count { color: #dc2626; }
.hotspot-item { padding: 10px; border-radius: 6px; margin-bottom: 8px; background: #f9fafb; border-left: 3px solid #d1d5db; cursor: pointer; }
.hotspot-item:hover { background: #f0f4ff; }
.hotspot-item.level-high { border-left-color: #dc2626; }
.hotspot-item.level-medium { border-left-color: #f59e0b; }
.hotspot-item.level-low { border-left-color: #3b82f6; }
.hs-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.hs-name { font-size: 12px; font-weight: 600; color: #374151; }
.hs-detail { display: grid; grid-template-columns: 1fr 1fr; gap: 3px; }
.hs-stat { font-size: 11px; color: #6b7280; }
.hs-stat strong { color: #374151; }
.empty-tip { font-size: 12px; color: #9ca3af; text-align: center; padding: 16px 0; }
.map-area { flex: 1; position: relative; }
.map-container { width: 100%; height: 100%; }
.mode-toggle {
  position: absolute; top: 14px; left: 14px; z-index: 200;
}
.map-summary {
  position: absolute; top: 14px; right: 16px; background: rgba(255,255,255,0.95);
  border-radius: 8px; padding: 8px 14px; font-size: 13px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.12); color: #374151; z-index: 100;
}
.map-summary strong { color: #dc2626; }
</style>
