<!--
  安全范围配置 — 2D/3D 双模式
  3D：Cesium 场景下以无人机为球心渲染半透明安全球，
      当两球相交时自动标红（防撞预警）
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
            show-input input-size="small" @change="onConfigChange" />
          <span class="unit">m</span>
        </div>
        <div class="param-row">
          <span>警戒距离</span>
          <el-slider v-model="config.warnDistance" :min="50" :max="800" :step="10"
            show-input input-size="small" @change="onConfigChange" />
          <span class="unit">m</span>
        </div>
      </div>

      <div class="section">
        <h3 class="section-title">垂直安全距离</h3>
        <div class="param-row">
          <span>垂直间隔</span>
          <el-slider v-model="config.verticalBuffer" :min="5" :max="100" :step="5"
            show-input input-size="small" />
          <span class="unit">m</span>
        </div>
      </div>

      <div class="section">
        <h3 class="section-title">风险等级阈值</h3>
        <div class="threshold-item" v-for="t in thresholds" :key="t.level">
          <span class="dot" :style="{ background: t.color }"></span>
          <span class="level-name">{{ t.name }}</span>
          <el-input-number v-model="t.value" :min="1" :max="1000" :step="10"
            size="small" @change="onConfigChange" style="width:110px" />
          <span class="unit">m</span>
        </div>
      </div>

      <div class="section">
        <h3 class="section-title">模拟无人机 <span class="drone-count">{{ drones.length }} 架</span></h3>
        <div v-for="d in drones" :key="d.id" class="drone-item">
          <span class="drone-dot" :style="{ background: d.color }"></span>
          <span class="drone-name">{{ d.name }}</span>
          <el-tag size="small" :type="d.statusType">{{ d.status }}</el-tag>
          <el-tag v-if="conflictIds.has(d.id)" size="small" type="danger" style="margin-left:2px">⚠冲突</el-tag>
        </div>
        <div v-if="conflictIds.size > 0" class="conflict-warn">
          ⚠️ {{ conflictIds.size }} 架无人机缓冲球重叠，建议调大半径
        </div>
      </div>

      <div class="section">
        <el-button type="primary" style="width:100%" @click="applyConfig">应用配置</el-button>
        <el-button style="width:100%;margin-top:8px" @click="resetConfig">恢复默认</el-button>
      </div>
    </aside>

    <!-- 右侧地图区域 -->
    <div class="right-section">
      <!-- 2D/3D 切换栏（在地图容器外部，避免被 Cesium canvas 覆盖） -->
      <div class="view-mode-bar">
        <div class="mode-btns">
          <button class="mode-btn" :class="{ active: viewMode === '2D' }" @click="switchMode('2D')">
            🗺 2D 平面
          </button>
          <button class="mode-btn" :class="{ active: viewMode === '3D' }" @click="switchMode('3D')">
            🌐 3D 缓冲球
          </button>
        </div>
        <span class="mode-tip" v-if="viewMode === '3D'">可拖拽旋转视角 · 红色球体表示缓冲区重叠</span>
        <span class="mode-tip" v-else>显示每架无人机的安全缓冲圆圈</span>
        <div class="conflict-badge" v-if="conflictIds.size > 0 && viewMode === '3D'">
          🔴 {{ conflictIds.size }} 处防撞冲突
        </div>
      </div>

      <!-- 地图容器（2D AMap / 3D Cesium 二选一） -->
      <div class="map-area">
        <div v-show="viewMode === '2D'" ref="mapRef" class="map-container"></div>
        <div v-show="viewMode === '3D'" ref="cesiumRef" class="map-container"></div>

        <!-- 图例浮窗（放在 map-area 内，不会被 Cesium 主 canvas 遮挡因为我们用了 v-show 而非 v-if） -->
        <div class="map-legend">
          <div class="legend-title">{{ viewMode === '3D' ? '缓冲球' : '缓冲圆' }}图例</div>
          <div class="legend-item">
            <span class="legend-color" style="background:#3b82f6;opacity:.5"></span>
            安全缓冲（{{ config.horizontalBuffer }}m）
          </div>
          <div class="legend-item">
            <span class="legend-color" style="background:#f59e0b;opacity:.4"></span>
            警戒区（{{ config.warnDistance }}m）
          </div>
          <div class="legend-item">
            <span class="legend-color" style="background:#dc2626;opacity:.5"></span>
            冲突（球体相交）
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import AMapLoader from '@amap/amap-jsapi-loader'
import { ElMessage } from 'element-plus'

// 动态加载 Cesium（避免 Vite 处理 Cesium 源码时的 @zip.js 依赖缺失问题）
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

// ── 无人机数据（刻意让前两架接近，体现防撞） ─────────
// GZ-A001 与 GZ-A002 相距约 220m，默认 100m 半径时不冲突；
// 调到 130m 以上即发生重叠，方便演示
const DRONE_COLORS = ['#3b82f6', '#8b5cf6', '#ec4899', '#22c55e', '#f59e0b', '#06b6d4']

const drones = ref([
  { id: 1, name: 'GZ-A001', lng: 113.3245, lat: 23.1201, alt: 120, status: '飞行中', statusType: 'success', color: DRONE_COLORS[0] },
  { id: 2, name: 'GZ-A002', lng: 113.3264, lat: 23.1188, alt: 145, status: '飞行中', statusType: 'success', color: DRONE_COLORS[1] },  // ~210m from A001
  { id: 3, name: 'GZ-B001', lng: 113.3198, lat: 23.1240, alt: 100, status: '悬停',   statusType: 'warning', color: DRONE_COLORS[2] },  // ~540m from A001
  { id: 4, name: 'GZ-B002', lng: 113.3100, lat: 23.1160, alt: 130, status: '飞行中', statusType: 'success', color: DRONE_COLORS[3] },
  { id: 5, name: 'GZ-C001', lng: 113.3180, lat: 23.1100, alt: 110, status: '返航中', statusType: 'info',    color: DRONE_COLORS[4] },  // ~150m from B002
  { id: 6, name: 'GZ-C002', lng: 113.3300, lat: 23.1150, alt: 125, status: '飞行中', statusType: 'success', color: DRONE_COLORS[5] },
])

const config = reactive({ horizontalBuffer: 100, warnDistance: 300, verticalBuffer: 20 })
const thresholds = reactive([
  { level: 'low',    name: '低风险', value: 500, color: '#16a34a' },
  { level: 'medium', name: '中风险', value: 300, color: '#f59e0b' },
  { level: 'high',   name: '高风险', value: 100, color: '#dc2626' },
])

// ── 冲突检测（两球球心距 < 2×半径即冲突） ────────────
function dist2D(a, b) {
  const LNG_M = Math.cos(a.lat * Math.PI / 180) * 111320
  const LAT_M = 111320
  return Math.sqrt(((b.lng - a.lng) * LNG_M) ** 2 + ((b.lat - a.lat) * LAT_M) ** 2)
}

const conflictIds = computed(() => {
  const ids = new Set()
  const r = config.horizontalBuffer
  for (let i = 0; i < drones.value.length; i++) {
    for (let j = i + 1; j < drones.value.length; j++) {
      if (dist2D(drones.value[i], drones.value[j]) < r * 2) {
        ids.add(drones.value[i].id)
        ids.add(drones.value[j].id)
      }
    }
  }
  return ids
})

// ── 视图模式 ──────────────────────────────────────────
const viewMode = ref('2D')
const mapRef = ref(null)
const cesiumRef = ref(null)

// ── 2D AMap ──────────────────────────────────────────
let AMap = null, map = null
const droneOverlays = {}

async function initMap() {
  if (!mapRef.value || map) return
  window._AMapSecurityConfig = { securityJsCode: import.meta.env.VITE_AMAP_SECURITY_CODE }
  try {
    if (!AMap) AMap = await AMapLoader.load({ key: import.meta.env.VITE_AMAP_KEY, version: '2.0', plugins: ['AMap.Scale'] })
    map = new AMap.Map(mapRef.value, {
      viewMode: '2D', zoom: 14,
      center: [113.3220, 23.1180],
      mapStyle: 'amap://styles/whitesmoke',
    })
    map.addControl(new AMap.Scale({ position: 'LB' }))
    renderDrones2D()
  } catch (e) { console.error('AMap init failed:', e) }
}

function renderDrones2D() {
  if (!map || !AMap) return
  Object.values(droneOverlays).forEach(o => {
    try { map.remove(o.circles); map.remove(o.marker) } catch {}
  })
  const bufH = config.horizontalBuffer
  const bufW = config.warnDistance
  const conflicts = conflictIds.value

  drones.value.forEach(d => {
    const pos = new AMap.LngLat(d.lng, d.lat)
    const isConflict = conflicts.has(d.id)
    const safeColor = isConflict ? '#dc2626' : d.color
    const warnCircle = new AMap.Circle({ center: pos, radius: bufW,
      strokeColor: '#f59e0b', strokeWeight: 1.5, strokeOpacity: 0.5, fillColor: '#f59e0b', fillOpacity: 0.05 })
    const safeCircle = new AMap.Circle({ center: pos, radius: bufH,
      strokeColor: safeColor, strokeWeight: 2, strokeOpacity: 0.9,
      fillColor: safeColor, fillOpacity: isConflict ? 0.20 : 0.12 })
    const marker = new AMap.Marker({
      position: pos,
      content: `<div style="background:${isConflict ? '#dc2626' : d.color};color:#fff;padding:3px 7px;border-radius:4px;font-size:11px;white-space:nowrap;box-shadow:0 1px 4px rgba(0,0,0,.3)">${isConflict ? '⚠️' : '🚁'} ${d.name}</div>`,
      offset: new AMap.Pixel(-28, -14),
    })
    map.add([warnCircle, safeCircle, marker])
    droneOverlays[d.id] = { circles: [warnCircle, safeCircle], marker }
  })
}

function destroyAMap() {
  Object.values(droneOverlays).forEach(o => {
    try { map?.remove(o.circles); map?.remove(o.marker) } catch {}
  })
  map?.destroy(); map = null
}

// ── 3D Cesium ─────────────────────────────────────────
let cesiumViewer = null
let cesium3DReady = false

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
  if (!cesiumRef.value || cesium3DReady) return
  await loadCesium()
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
  // 聚焦在无人机密集区域，高度 1200m 使球体清晰可见
  cesiumViewer.camera.setView({
    destination: Cesium.Cartesian3.fromDegrees(113.3220, 23.1175, 1200),
    orientation: { heading: Cesium.Math.toRadians(20), pitch: Cesium.Math.toRadians(-45), roll: 0 },
  })
  cesium3DReady = true
  render3DSpheres()
}

function render3DSpheres() {
  if (!cesiumViewer || !cesium3DReady) return
  cesiumViewer.entities.removeAll()

  const bufH = config.horizontalBuffer
  const bufW = config.warnDistance
  const conflicts = conflictIds.value

  drones.value.forEach(d => {
    const isConflict = conflicts.has(d.id)
    const baseColor = Cesium.Color.fromCssColorString(isConflict ? '#dc2626' : d.color)
    const pos3D = Cesium.Cartesian3.fromDegrees(d.lng, d.lat, d.alt)

    // 警戒外球（线框，很透明）
    cesiumViewer.entities.add({
      position: pos3D,
      ellipsoid: {
        radii: new Cesium.Cartesian3(bufW, bufW, bufW * 0.55),
        material: Cesium.Color.fromCssColorString('#f59e0b').withAlpha(0.04),
        outline: true,
        outlineColor: Cesium.Color.fromCssColorString('#f59e0b').withAlpha(0.30),
        slicePartitions: 12, stackPartitions: 12,
      },
    })

    // 安全缓冲球（主视觉，半透明填充 + 清晰轮廓）
    cesiumViewer.entities.add({
      position: pos3D,
      ellipsoid: {
        radii: new Cesium.Cartesian3(bufH, bufH, bufH),
        material: baseColor.withAlpha(isConflict ? 0.35 : 0.18),
        outline: true,
        outlineColor: baseColor.withAlpha(isConflict ? 0.90 : 0.65),
        slicePartitions: 24, stackPartitions: 24,
      },
    })

    // 无人机图标 billboard
    cesiumViewer.entities.add({
      position: Cesium.Cartesian3.fromDegrees(d.lng, d.lat, d.alt + bufH * 0.1),
      billboard: {
        image: makeDroneCanvas(isConflict ? '#dc2626' : d.color),
        width: 36, height: 36,
        verticalOrigin: Cesium.VerticalOrigin.CENTER,
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
        eyeOffset: new Cesium.Cartesian3(0, 0, -30),
      },
      label: {
        text: `${d.name}\nH ${d.alt}m`,
        font: '11px monospace',
        fillColor: Cesium.Color.WHITE,
        showBackground: true,
        backgroundColor: baseColor.withAlpha(0.88),
        backgroundPadding: new Cesium.Cartesian2(5, 3),
        pixelOffset: new Cesium.Cartesian2(0, -52),
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
      },
    })

    // 冲突时增加红色告警环（水平圆盘）
    if (isConflict) {
      cesiumViewer.entities.add({
        position: pos3D,
        ellipse: {
          semiMajorAxis: bufH,
          semiMinorAxis: bufH,
          material: Cesium.Color.fromCssColorString('#dc2626').withAlpha(0.12),
          outline: true,
          outlineColor: Cesium.Color.fromCssColorString('#dc2626').withAlpha(0.7),
          outlineWidth: 2,
          height: d.alt,
        },
      })
    }

    // 到地面的竖向指示线
    cesiumViewer.entities.add({
      polyline: {
        positions: [
          Cesium.Cartesian3.fromDegrees(d.lng, d.lat, 0),
          Cesium.Cartesian3.fromDegrees(d.lng, d.lat, d.alt),
        ],
        width: 1,
        material: baseColor.withAlpha(0.25),
      },
    })
  })

  cesiumViewer.scene.requestRender()
}

function destroyCesium() {
  cesium3DReady = false
  if (cesiumViewer && !cesiumViewer.isDestroyed()) cesiumViewer.destroy()
  cesiumViewer = null
}

// ── 模式切换 ──────────────────────────────────────────
function switchMode(mode) {
  if (viewMode.value === mode) return
  viewMode.value = mode
  if (mode === '2D') {
    nextTick(() => initMap())
  } else {
    nextTick(() => initCesium())
  }
}

function onConfigChange() {
  if (viewMode.value === '2D') renderDrones2D()
  else render3DSpheres()
}

function applyConfig() {
  onConfigChange()
  const conflicts = conflictIds.value.size
  if (conflicts > 0) {
    ElMessage.warning(`配置已应用，但仍有 ${conflicts} 架无人机缓冲球重叠，建议增大半径`)
  } else {
    ElMessage.success(`配置已应用：缓冲半径 ${config.horizontalBuffer}m，无冲突`)
  }
}

function resetConfig() {
  config.horizontalBuffer = 100; config.warnDistance = 300; config.verticalBuffer = 20
  thresholds[0].value = 500; thresholds[1].value = 300; thresholds[2].value = 100
  onConfigChange()
  ElMessage.info('已恢复默认配置')
}

onMounted(() => initMap())
onUnmounted(() => { destroyAMap(); destroyCesium() })
</script>

<style scoped>
.buffer-config-page { display: flex; height: 100%; overflow: hidden; }

/* 左侧面板 */
.config-panel {
  width: 295px; flex-shrink: 0; background: #fff; border-right: 1px solid #e5e7eb;
  overflow-y: auto; padding: 16px;
}
.panel-header { display: flex; align-items: center; gap: 8px; margin-bottom: 16px; }
.panel-header h2 { font-size: 15px; font-weight: 700; color: #111827; margin: 0; }
.panel-icon { font-size: 20px; }
.section { border-top: 1px solid #f3f4f6; padding-top: 14px; margin-bottom: 14px; }
.section-title { font-size: 13px; font-weight: 600; color: #374151; margin: 0 0 10px; display: flex; align-items: center; gap: 6px; }
.drone-count { font-size: 11px; font-weight: 400; color: #9ca3af; }
.param-row { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; flex-wrap: wrap; }
.param-row > span:first-child { font-size: 12px; color: #6b7280; width: 60px; flex-shrink: 0; }
.unit { font-size: 12px; color: #9ca3af; }
.threshold-item { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
.level-name { font-size: 12px; color: #374151; width: 45px; }
.drone-item { display: flex; align-items: center; gap: 6px; padding: 4px 0; flex-wrap: wrap; }
.drone-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
.drone-name { font-size: 12px; color: #374151; flex: 1; }
.conflict-warn {
  margin-top: 8px; padding: 7px 10px; background: #fef2f2; border: 1px solid #fecaca;
  border-radius: 6px; font-size: 11px; color: #dc2626; line-height: 1.5;
}

/* 右侧区域 */
.right-section { flex: 1; display: flex; flex-direction: column; overflow: hidden; }

/* 切换栏 — 在地图容器外部，确保不被 Cesium canvas 覆盖 */
.view-mode-bar {
  flex-shrink: 0; height: 46px; padding: 0 16px;
  background: #fff; border-bottom: 1px solid #e5e7eb;
  display: flex; align-items: center; gap: 14px;
}
.mode-btns { display: flex; gap: 2px; background: #f3f4f6; padding: 3px; border-radius: 8px; }
.mode-btn {
  padding: 5px 18px; border: none; border-radius: 6px; font-size: 13px; font-weight: 500;
  cursor: pointer; color: #6b7280; background: transparent; transition: all .15s;
}
.mode-btn.active { background: #2563eb; color: #fff; box-shadow: 0 1px 3px rgba(37,99,235,.4); }
.mode-tip { font-size: 12px; color: #9ca3af; flex: 1; }
.conflict-badge {
  padding: 4px 10px; background: #fef2f2; border: 1px solid #fecaca;
  border-radius: 6px; font-size: 12px; color: #dc2626; font-weight: 600;
}

/* 地图区 */
.map-area { flex: 1; position: relative; overflow: hidden; }
.map-container { width: 100%; height: 100%; }

.map-legend {
  position: absolute; bottom: 20px; right: 14px; background: rgba(255,255,255,0.95);
  border-radius: 8px; padding: 10px 14px; box-shadow: 0 2px 8px rgba(0,0,0,.15); font-size: 12px; z-index: 10;
  pointer-events: none;
}
.legend-title { font-weight: 600; color: #374151; margin-bottom: 6px; }
.legend-item { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; color: #6b7280; }
.legend-color { width: 22px; height: 12px; border-radius: 3px; flex-shrink: 0; }
</style>
