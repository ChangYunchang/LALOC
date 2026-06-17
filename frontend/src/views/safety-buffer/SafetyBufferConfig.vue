<!--
  安全范围配置 — 2D/3D 双模式
  2D：AMap 多同心圆（安全/警戒/危险）
  3D：Cesium 半透明球体（ellipsoid entity），以无人机为中心
-->
<template>
  <div class="buffer-config-page">
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
            show-input input-size="small" @change="onConfigChange" />
          <span class="unit">米</span>
        </div>
        <div class="param-row">
          <span>警戒距离</span>
          <el-slider v-model="config.warnDistance" :min="50" :max="800" :step="10"
            show-input input-size="small" @change="onConfigChange" />
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
            size="small" @change="onConfigChange" style="width:110px" />
          <span class="unit">米</span>
        </div>
      </div>

      <div class="section">
        <h3 class="section-title">模拟无人机</h3>
        <div v-for="d in drones" :key="d.id" class="drone-item">
          <span class="drone-dot" :style="{ background: d.color }"></span>
          <span class="drone-name">{{ d.name }}</span>
          <el-tag size="small" :type="d.statusType">{{ d.status }}</el-tag>
        </div>
      </div>

      <div class="section">
        <el-button type="primary" style="width:100%" @click="applyConfig">应用配置</el-button>
        <el-button style="width:100%;margin-top:8px" @click="resetConfig">恢复默认</el-button>
      </div>
    </aside>

    <div class="map-area">
      <!-- 2D/3D 切换 -->
      <div class="mode-toggle-bar">
        <el-button-group size="small">
          <el-button :type="viewMode === '2D' ? 'primary' : 'default'" @click="switchMode('2D')">2D 平面</el-button>
          <el-button :type="viewMode === '3D' ? 'primary' : 'default'" @click="switchMode('3D')">3D 实景球</el-button>
        </el-button-group>
        <span class="mode-hint" v-if="viewMode === '3D'">拖动视角可查看球体形态</span>
      </div>

      <div v-if="viewMode === '2D'" ref="mapRef" class="map-container"></div>
      <div v-if="viewMode === '3D'" ref="cesiumRef" class="map-container"></div>

      <div class="map-legend">
        <div class="legend-title">缓冲{{ viewMode === '3D' ? '球' : '圆' }}图例</div>
        <div class="legend-item">
          <span class="legend-color" style="background:#3b82f6;opacity:.5"></span>
          安全缓冲（{{ config.horizontalBuffer }}m）
        </div>
        <div class="legend-item">
          <span class="legend-color" style="background:#f59e0b;opacity:.4"></span>
          警戒区（{{ config.warnDistance }}m）
        </div>
        <div class="legend-item">
          <span class="legend-color" style="background:#dc2626;opacity:.4"></span>
          危险区（{{ thresholds[2].value }}m）
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, watch, onUnmounted, nextTick } from 'vue'
import AMapLoader from '@amap/amap-jsapi-loader'
import * as Cesium from 'cesium'
import { ElMessage } from 'element-plus'

const DRONE_COLORS = ['#3b82f6', '#8b5cf6', '#ec4899', '#22c55e', '#f59e0b', '#06b6d4']

const drones = ref([
  { id: 1, name: 'GZ-A001', lng: 113.3245, lat: 23.1201, alt: 120, status: '飞行中', statusType: 'success', color: DRONE_COLORS[0] },
  { id: 2, name: 'GZ-A002', lng: 113.2994, lat: 23.1540, alt: 140, status: '飞行中', statusType: 'success', color: DRONE_COLORS[1] },
  { id: 3, name: 'GZ-B001', lng: 113.3580, lat: 23.1050, alt: 100, status: '悬停',   statusType: 'warning', color: DRONE_COLORS[2] },
  { id: 4, name: 'GZ-B002', lng: 113.2671, lat: 23.0900, alt: 130, status: '飞行中', statusType: 'success', color: DRONE_COLORS[3] },
  { id: 5, name: 'GZ-C001', lng: 113.3900, lat: 23.1380, alt: 110, status: '返航中', statusType: 'info',    color: DRONE_COLORS[4] },
  { id: 6, name: 'GZ-C002', lng: 113.3100, lat: 23.0750, alt: 125, status: '飞行中', statusType: 'success', color: DRONE_COLORS[5] },
])

const config = reactive({ horizontalBuffer: 100, warnDistance: 300, verticalBuffer: 20 })
const thresholds = reactive([
  { level: 'low',    name: '低风险', value: 500, color: '#16a34a' },
  { level: 'medium', name: '中风险', value: 300, color: '#f59e0b' },
  { level: 'high',   name: '高风险', value: 100, color: '#dc2626' },
])

const viewMode = ref('2D')
const mapRef = ref(null)
const cesiumRef = ref(null)

// ── 2D AMap ──────────────────────────────────────────
let AMap = null, map = null
const droneOverlays = {}

async function initMap() {
  if (!mapRef.value) return
  window._AMapSecurityConfig = { securityJsCode: import.meta.env.VITE_AMAP_SECURITY_CODE }
  try {
    if (!AMap) AMap = await AMapLoader.load({ key: import.meta.env.VITE_AMAP_KEY, version: '2.0', plugins: ['AMap.Scale'] })
    map = new AMap.Map(mapRef.value, {
      viewMode: '2D', zoom: 12,
      center: [113.3244, 23.1201],
      mapStyle: 'amap://styles/whitesmoke',
    })
    map.addControl(new AMap.Scale({ position: 'LB' }))
    renderDrones2D()
  } catch (e) { console.error('AMap init failed:', e) }
}

function renderDrones2D() {
  if (!map || !AMap) return
  Object.values(droneOverlays).forEach(o => { map.remove(o.circles); map.remove(o.marker) })

  drones.value.forEach(d => {
    const pos = new AMap.LngLat(d.lng, d.lat)
    const dangerCircle = new AMap.Circle({ center: pos, radius: thresholds[2].value,
      strokeColor: '#dc2626', strokeWeight: 1, strokeOpacity: 0.6, fillColor: '#dc2626', fillOpacity: 0.07 })
    const warnCircle = new AMap.Circle({ center: pos, radius: config.warnDistance,
      strokeColor: '#f59e0b', strokeWeight: 1.5, strokeOpacity: 0.7, fillColor: '#f59e0b', fillOpacity: 0.07 })
    const safeCircle = new AMap.Circle({ center: pos, radius: config.horizontalBuffer,
      strokeColor: d.color, strokeWeight: 2, strokeOpacity: 0.9, fillColor: d.color, fillOpacity: 0.15 })
    const marker = new AMap.Marker({
      position: pos,
      content: `<div style="background:${d.color};color:#fff;padding:3px 7px;border-radius:4px;font-size:11px;white-space:nowrap;box-shadow:0 1px 4px rgba(0,0,0,0.3)">🚁 ${d.name}</div>`,
      offset: new AMap.Pixel(-28, -14),
    })
    const circles = [dangerCircle, warnCircle, safeCircle]
    map.add(circles)
    map.add(marker)
    droneOverlays[d.id] = { circles, marker }
  })
}

function destroyAMap() {
  Object.values(droneOverlays).forEach(o => { try { map?.remove(o.circles); map?.remove(o.marker) } catch {} })
  map?.destroy(); map = null
}

// ── 3D Cesium ─────────────────────────────────────────
let cesiumViewer = null

function makeDroneCanvas(color) {
  const cv = document.createElement('canvas'); cv.width = 36; cv.height = 36
  const ctx = cv.getContext('2d')
  ctx.strokeStyle = '#fff'; ctx.lineWidth = 2.5
  ctx.beginPath(); ctx.moveTo(18, 7); ctx.lineTo(18, 29); ctx.stroke()
  ctx.beginPath(); ctx.moveTo(7, 18); ctx.lineTo(29, 18); ctx.stroke()
  ;[[7,7],[29,7],[7,29],[29,29]].forEach(([x,y]) => {
    ctx.beginPath(); ctx.arc(x, y, 5, 0, Math.PI*2)
    ctx.fillStyle = color; ctx.fill(); ctx.strokeStyle='#fff'; ctx.lineWidth=1.5; ctx.stroke()
  })
  ctx.beginPath(); ctx.arc(18, 18, 4, 0, Math.PI*2)
  ctx.fillStyle = '#fff'; ctx.fill()
  return cv
}

async function initCesium() {
  if (!cesiumRef.value) return
  Cesium.Ion.defaultAccessToken = import.meta.env.VITE_CESIUM_ION_TOKEN
  cesiumViewer = new Cesium.Viewer(cesiumRef.value, {
    terrain: Cesium.Terrain.fromWorldTerrain(),
    baseLayerPicker: false, geocoder: false, homeButton: false,
    sceneModePicker: false, navigationHelpButton: false,
    animation: false, timeline: false, fullscreenButton: false,
    infoBox: false, selectionIndicator: false,
    requestRenderMode: true,
  })
  try { cesiumViewer.scene.primitives.add(await Cesium.createOsmBuildingsAsync()) } catch {}
  cesiumViewer.camera.setView({
    destination: Cesium.Cartesian3.fromDegrees(113.3244, 23.1100, 3200),
    orientation: { heading: 0, pitch: Cesium.Math.toRadians(-48), roll: 0 },
  })
  render3DSpheres()
}

function render3DSpheres() {
  if (!cesiumViewer) return
  cesiumViewer.entities.removeAll()

  const bufH = config.horizontalBuffer
  const bufW = config.warnDistance

  drones.value.forEach(d => {
    const cesiumColor = Cesium.Color.fromCssColorString(d.color)

    // 警戒外球（大、极透明、线框为主）
    cesiumViewer.entities.add({
      position: Cesium.Cartesian3.fromDegrees(d.lng, d.lat, d.alt),
      ellipsoid: {
        radii: new Cesium.Cartesian3(bufW, bufW, bufW * 0.6),
        material: Cesium.Color.fromCssColorString('#f59e0b').withAlpha(0.05),
        outline: true,
        outlineColor: Cesium.Color.fromCssColorString('#f59e0b').withAlpha(0.35),
        slicePartitions: 12, stackPartitions: 12,
      },
    })

    // 安全缓冲球（主要视觉元素，半透明）
    cesiumViewer.entities.add({
      position: Cesium.Cartesian3.fromDegrees(d.lng, d.lat, d.alt),
      ellipsoid: {
        radii: new Cesium.Cartesian3(bufH, bufH, bufH),
        material: cesiumColor.withAlpha(0.20),
        outline: true,
        outlineColor: cesiumColor.withAlpha(0.65),
        slicePartitions: 24, stackPartitions: 24,
      },
    })

    // 无人机图标
    cesiumViewer.entities.add({
      position: Cesium.Cartesian3.fromDegrees(d.lng, d.lat, d.alt),
      billboard: {
        image: makeDroneCanvas(d.color),
        width: 36, height: 36,
        verticalOrigin: Cesium.VerticalOrigin.CENTER,
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
        eyeOffset: new Cesium.Cartesian3(0, 0, -50),
      },
      label: {
        text: `${d.name}\nH=${d.alt}m`,
        font: '11px monospace',
        fillColor: Cesium.Color.WHITE,
        showBackground: true,
        backgroundColor: cesiumColor.withAlpha(0.85),
        backgroundPadding: new Cesium.Cartesian2(4, 3),
        pixelOffset: new Cesium.Cartesian2(0, -50),
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
      },
    })

    // 竖向高度指示线（无人机到地面）
    cesiumViewer.entities.add({
      polyline: {
        positions: [
          Cesium.Cartesian3.fromDegrees(d.lng, d.lat, 0),
          Cesium.Cartesian3.fromDegrees(d.lng, d.lat, d.alt),
        ],
        width: 1,
        material: cesiumColor.withAlpha(0.3),
      },
    })
  })

  cesiumViewer.scene.requestRender()
}

function destroyCesium() {
  if (cesiumViewer && !cesiumViewer.isDestroyed()) cesiumViewer.destroy()
  cesiumViewer = null
}

// ── 模式切换 ──────────────────────────────────────────
function switchMode(mode) {
  if (viewMode.value === mode) return
  if (mode === '3D') { destroyAMap(); viewMode.value = '3D' }
  else { destroyCesium(); viewMode.value = '2D' }
}

watch(mapRef, async el => { if (el) { await nextTick(); initMap() } })
watch(cesiumRef, async el => { if (el) { await nextTick(); initCesium() } })

function onConfigChange() {
  if (viewMode.value === '2D') renderDrones2D()
  else render3DSpheres()
}

function applyConfig() {
  onConfigChange()
  ElMessage.success(`配置已应用：安全缓冲 ${config.horizontalBuffer}m，警戒 ${config.warnDistance}m`)
}

function resetConfig() {
  config.horizontalBuffer = 100; config.warnDistance = 300; config.verticalBuffer = 20
  thresholds[0].value = 500; thresholds[1].value = 300; thresholds[2].value = 100
  onConfigChange()
  ElMessage.info('已恢复默认配置')
}

onUnmounted(() => { destroyAMap(); destroyCesium() })
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
.param-row > span:first-child { font-size: 12px; color: #6b7280; width: 60px; flex-shrink: 0; }
.unit { font-size: 12px; color: #9ca3af; }
.threshold-item { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
.level-name { font-size: 12px; color: #374151; width: 45px; }
.drone-item { display: flex; align-items: center; gap: 8px; padding: 4px 0; }
.drone-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
.drone-name { font-size: 12px; color: #374151; flex: 1; }

.map-area { flex: 1; position: relative; overflow: hidden; }
.map-container { width: 100%; height: 100%; }

.mode-toggle-bar {
  position: absolute; top: 12px; left: 50%; transform: translateX(-50%);
  z-index: 100; display: flex; align-items: center; gap: 10px;
  background: rgba(255,255,255,0.95); padding: 6px 12px; border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.15);
}
.mode-hint { font-size: 11px; color: #6b7280; }

.map-legend {
  position: absolute; bottom: 24px; right: 16px; background: rgba(255,255,255,0.95);
  border-radius: 8px; padding: 12px 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.15); font-size: 12px; z-index: 100;
}
.legend-title { font-weight: 600; color: #374151; margin-bottom: 6px; }
.legend-item { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; color: #6b7280; }
.legend-color { width: 20px; height: 12px; border-radius: 2px; flex-shrink: 0; }
</style>
