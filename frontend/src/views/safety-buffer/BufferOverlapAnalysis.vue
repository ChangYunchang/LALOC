<!--
  缓冲区重叠动态分析 — 类火车区间模型
  多架无人机共享同一航线，按区间划分，每区间同时只允许 1 架进入，
  后机自动减速/停止；缓冲球重叠时触发防撞告警。
  2D / 3D 双模式，切换栏置于地图容器外部，避免被 Cesium canvas 覆盖。
-->
<template>
  <div class="overlap-page">
    <!-- 左侧控制 & 状态面板 -->
    <aside class="status-panel">
      <div class="panel-header">
        <span class="panel-icon">📡</span>
        <h2>区间防撞分析</h2>
        <el-tag size="small" :type="running ? 'success' : 'info'">
          {{ running ? '仿真中' : '已暂停' }}
        </el-tag>
      </div>

      <!-- 模拟控制 -->
      <div class="section">
        <div class="ctrl-row">
          <el-button size="small" :type="running ? 'warning' : 'primary'" @click="toggleSim">
            {{ running ? '⏸ 暂停' : '▶ 开始' }}
          </el-button>
          <el-button size="small" @click="resetSim">↺ 重置</el-button>
          <el-button size="small" @click="addConflict">💥 制造冲突</el-button>
        </div>
        <div class="param-row">
          <span>仿真速度</span>
          <el-slider v-model="simSpeed" :min="0.5" :max="5" :step="0.5" show-input input-size="small" style="flex:1" />
          <span class="unit">×</span>
        </div>
        <div class="param-row">
          <span>缓冲半径</span>
          <el-slider v-model="bufferR" :min="50" :max="500" :step="25" show-input input-size="small" style="flex:1" />
          <span class="unit">m</span>
        </div>
      </div>

      <!-- 区间状态 -->
      <div class="section">
        <h3 class="section-title">航线区间状态 <span class="zone-count">{{ ZONES }}段</span></h3>
        <div class="zones-grid">
          <div v-for="(z, i) in zoneStatus" :key="i" class="zone-cell" :class="z.state">
            <div class="zone-label">Z{{ i }}</div>
            <div class="zone-icon">{{ z.state === 'conflict' ? '⚠️' : z.state === 'occupied' ? '🔴' : '🟢' }}</div>
            <div class="zone-drone">{{ z.droneId || '—' }}</div>
          </div>
        </div>
      </div>

      <!-- 无人机状态 -->
      <div class="section">
        <h3 class="section-title">无人机状态</h3>
        <div v-for="d in droneStates" :key="d.id" class="drone-status-item">
          <div class="ds-header">
            <span class="ds-dot" :style="{ background: d.color }"></span>
            <span class="ds-name">{{ d.name }}</span>
            <el-tag size="small" :type="d.status === 'conflict' ? 'danger' : d.status === 'stopped' ? 'warning' : 'success'">
              {{ statusLabel[d.status] }}
            </el-tag>
          </div>
          <div class="ds-bar-row">
            <div class="ds-bar-bg">
              <div class="ds-bar-fill" :class="d.status"
                :style="{ width: `${d.speedRatio * 100}%`, background: d.color }">
              </div>
            </div>
            <span class="ds-speed-num">{{ Math.round(d.speedRatio * 100) }}%</span>
          </div>
          <div class="ds-meta">
            <span>Z{{ d.zone }}</span>
            <span>{{ (d.t * 100).toFixed(1) }}%</span>
            <span>H {{ Math.round(altAtT(d.t)) }}m</span>
          </div>
        </div>
      </div>

      <!-- 事件日志 -->
      <div class="section log-section">
        <h3 class="section-title">防撞事件日志</h3>
        <div class="event-log" ref="logRef">
          <div v-for="(e, i) in eventLog" :key="i" class="event-item" :class="e.type">
            <span class="event-time">{{ e.time }}</span>
            <span class="event-msg">{{ e.msg }}</span>
          </div>
          <div v-if="eventLog.length === 0" class="empty-log">暂无事件</div>
        </div>
      </div>
    </aside>

    <!-- 右侧地图区域 -->
    <div class="right-section">
      <!-- 2D/3D 切换栏 — 在 map-container 外部，不被 Cesium canvas 覆盖 -->
      <div class="view-mode-bar">
        <div class="mode-btns">
          <button class="mode-btn" :class="{ active: viewMode === '2D' }" @click="switchMode('2D')">
            🗺 2D 平面
          </button>
          <button class="mode-btn" :class="{ active: viewMode === '3D' }" @click="switchMode('3D')">
            🌐 3D 缓冲球防撞
          </button>
        </div>
        <div class="mode-info" v-if="viewMode === '3D'">
          <span>🔵 蓝色球体 = 安全间距</span>
          <span>🔴 红色球体 = 缓冲区重叠 · 防撞触发</span>
        </div>
        <div class="mode-info" v-else>
          <span>彩色圆圈 = 缓冲圆  |  区段颜色 = 区间占用状态</span>
        </div>
        <div class="conflict-badge" v-if="activeConflicts > 0">
          ⚠️ {{ activeConflicts }} 处冲突
        </div>
      </div>

      <!-- 地图区 -->
      <div class="map-area">
        <div v-show="viewMode === '2D'" ref="mapRef" class="map-container"></div>
        <div v-show="viewMode === '3D'" ref="cesiumRef" class="map-container"></div>

        <!-- 3D 场景说明浮层 -->
        <div v-if="viewMode === '3D'" class="scene-legend">
          <div class="sl-title">3D 缓冲球说明</div>
          <div class="sl-item"><span class="sl-dot safe"></span>蓝色球：安全区（{{ bufferR }}m）</div>
          <div class="sl-item"><span class="sl-dot conflict"></span>红色球：发生重叠 → 触发防撞</div>
          <div class="sl-item"><span class="sl-dot zone"></span>橙色段：区间被占用</div>
          <div class="sl-divider"></div>
          <div class="sl-note">球体相交时后机自动减速 / 停止</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, nextTick } from 'vue'
import AMapLoader from '@amap/amap-jsapi-loader'

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

// ── 航线坐标（天河→番禺，7个控制点） ──────────────────
const ROUTE_COORDS = [
  [113.3245, 23.1201], [113.3200, 23.1100], [113.3150, 23.0950],
  [113.3080, 23.0800], [113.3020, 23.0650], [113.2960, 23.0530],
  [113.2920, 23.0430],
]
const ZONES = 6
const DRONE_COLORS = ['#3b82f6', '#8b5cf6', '#ec4899', '#22c55e', '#f59e0b']

// 预计算累计距离用于精确插值
function latLngDist(a, b) {
  const M_PER_LNG = Math.cos(a[1] * Math.PI / 180) * 111320
  return Math.sqrt(((b[0] - a[0]) * M_PER_LNG) ** 2 + ((b[1] - a[1]) * 111320) ** 2)
}
const cumDist = [0]
for (let i = 1; i < ROUTE_COORDS.length; i++) {
  cumDist.push(cumDist[i - 1] + latLngDist(ROUTE_COORDS[i - 1], ROUTE_COORDS[i]))
}
const ROUTE_LEN = cumDist[cumDist.length - 1]

function posOnRoute(t) {
  const target = t * ROUTE_LEN
  let seg = 0
  for (let i = 0; i < cumDist.length - 1; i++) {
    if (target <= cumDist[i + 1]) { seg = i; break }
    seg = i
  }
  const local = (target - cumDist[seg]) / Math.max(cumDist[seg + 1] - cumDist[seg], 1)
  const a = ROUTE_COORDS[seg], b = ROUTE_COORDS[Math.min(seg + 1, ROUTE_COORDS.length - 1)]
  return { lng: a[0] + (b[0] - a[0]) * local, lat: a[1] + (b[1] - a[1]) * local }
}

function altAtT(t) {
  if (t < 0.12) return 20 + (160 - 20) * (t / 0.12)
  if (t > 0.88) return 20 + (160 - 20) * ((1 - t) / 0.12)
  return 160
}

// ── 无人机状态 ───────────────────────────────────────
const droneStates = reactive([
  { id: 1, name: 'GZ-A001', color: DRONE_COLORS[0], t: 0.00, speed: 12, speedRatio: 1.0, zone: 0, status: 'normal' },
  { id: 2, name: 'GZ-A002', color: DRONE_COLORS[1], t: 0.10, speed: 12, speedRatio: 1.0, zone: 0, status: 'normal' },
  { id: 3, name: 'GZ-B001', color: DRONE_COLORS[2], t: 0.30, speed: 12, speedRatio: 1.0, zone: 1, status: 'normal' },
  { id: 4, name: 'GZ-B002', color: DRONE_COLORS[3], t: 0.55, speed: 12, speedRatio: 1.0, zone: 3, status: 'normal' },
  { id: 5, name: 'GZ-C001', color: DRONE_COLORS[4], t: 0.78, speed: 12, speedRatio: 1.0, zone: 4, status: 'normal' },
])

const bufferR = ref(200)
const simSpeed = ref(1.5)
const running = ref(false)
const eventLog = ref([])
const logRef = ref(null)

const statusLabel = { normal: '飞行中', slowing: '减速中', stopped: '等待中', conflict: '防撞告警' }

const activeConflicts = computed(() => droneStates.filter(d => d.status === 'conflict').length)

// 区间状态
const zoneStatus = computed(() => {
  const zones = Array.from({ length: ZONES }, () => ({ state: 'free', droneId: null }))
  for (const d of droneStates) {
    const zi = Math.min(Math.floor(d.t * ZONES), ZONES - 1)
    if (zones[zi].state === 'occupied') {
      zones[zi].state = 'conflict'
      zones[zi].droneId = '多机'
    } else if (zones[zi].state !== 'conflict') {
      zones[zi].state = 'occupied'
      zones[zi].droneId = d.name
    }
  }
  return zones
})

function addLog(type, msg) {
  const now = new Date()
  const time = `${now.getHours().toString().padStart(2,'0')}:${now.getMinutes().toString().padStart(2,'0')}:${now.getSeconds().toString().padStart(2,'0')}`
  eventLog.value.unshift({ type, time, msg })
  if (eventLog.value.length > 50) eventLog.value.pop()
}

// ── 区间防撞算法（火车区间模型 + 缓冲球检测） ─────────────
function adjustSpeeds() {
  const sorted = [...droneStates].sort((a, b) => b.t - a.t)

  for (let i = 1; i < sorted.length; i++) {
    const follower = sorted[i]
    const leader = sorted[i - 1]

    const posF = posOnRoute(follower.t)
    const posL = posOnRoute(leader.t)
    const M_PER_LNG = Math.cos(posF.lat * Math.PI / 180) * 111320
    const dx = (posL.lng - posF.lng) * M_PER_LNG
    const dy = (posL.lat - posF.lat) * 111320
    const dz = altAtT(leader.t) - altAtT(follower.t)
    const dist = Math.sqrt(dx * dx + dy * dy + dz * dz)

    const R = bufferR.value
    const prevStatus = follower.status

    if (dist < R * 2) {
      follower.status = 'conflict'
      follower.speedRatio = Math.max(0, (dist - R) / (R * 1.5))
      if (prevStatus !== 'conflict') {
        addLog('danger', `⚠️ ${follower.name} 与 ${leader.name} 缓冲球重叠！间距 ${Math.round(dist)}m`)
      }
    } else if (follower.zone === leader.zone) {
      follower.status = 'stopped'
      follower.speedRatio = 0
      if (prevStatus !== 'stopped') {
        addLog('warn', `${follower.name} 进入已占区间Z${follower.zone}，停止等待`)
      }
    } else if (dist < R * 4) {
      follower.status = 'slowing'
      follower.speedRatio = 0.3 + (dist - R * 2) / (R * 2) * 0.7
      if (prevStatus === 'normal') {
        addLog('info', `${follower.name} 进入减速区（间距 ${Math.round(dist)}m）`)
      }
    } else {
      if (prevStatus !== 'normal') {
        addLog('success', `${follower.name} 恢复正常速度`)
      }
      follower.status = 'normal'
      follower.speedRatio = 1.0
    }
  }
  sorted[0].status = 'normal'
  sorted[0].speedRatio = 1.0
}

// ── 仿真 tick ───────────────────────────────────────
let simTimer = null
let lastTs = 0

function tick(ts) {
  if (!running.value) return
  if (lastTs === 0) lastTs = ts
  const dt = Math.min((ts - lastTs) / 1000, 0.1) * simSpeed.value
  lastTs = ts

  adjustSpeeds()
  for (const d of droneStates) {
    d.t += (d.speed * d.speedRatio * dt) / ROUTE_LEN
    if (d.t >= 1.0) d.t = 0
    d.zone = Math.min(Math.floor(d.t * ZONES), ZONES - 1)
  }

  if (viewMode.value === '2D') updateAMap2D()
  else updateCesium3D()

  simTimer = requestAnimationFrame(tick)
}

function toggleSim() {
  running.value = !running.value
  if (running.value) {
    lastTs = 0
    simTimer = requestAnimationFrame(tick)
    addLog('info', '仿真启动')
  } else {
    if (simTimer) { cancelAnimationFrame(simTimer); simTimer = null }
    addLog('info', '仿真暂停')
  }
}

function resetSim() {
  if (simTimer) { cancelAnimationFrame(simTimer); simTimer = null }
  running.value = false
  droneStates[0].t = 0.00; droneStates[1].t = 0.15
  droneStates[2].t = 0.32; droneStates[3].t = 0.55; droneStates[4].t = 0.78
  droneStates.forEach(d => { d.speedRatio = 1.0; d.status = 'normal' })
  eventLog.value = []
  if (viewMode.value === '2D') updateAMap2D()
  else { buildCesiumEntities(); updateCesium3D() }
  addLog('info', '仿真已重置')
}

function addConflict() {
  droneStates[1].t = droneStates[0].t + 0.018
  addLog('warn', '手动制造冲突：GZ-A001 与 GZ-A002 间距缩短')
}

// ── 2D AMap ──────────────────────────────────────────
let AMap = null, map = null
const zonePolylines = []
const droneMarkers2D = {}
const bufferCircles2D = {}

async function initAMap() {
  if (!mapRef.value || map) return
  window._AMapSecurityConfig = { securityJsCode: import.meta.env.VITE_AMAP_SECURITY_CODE }
  try {
    if (!AMap) AMap = await AMapLoader.load({ key: import.meta.env.VITE_AMAP_KEY, version: '2.0', plugins: [] })
    map = new AMap.Map(mapRef.value, {
      viewMode: '2D', zoom: 13,
      center: [113.3082, 23.0816],
      mapStyle: 'amap://styles/whitesmoke',
    })
    buildAMapZones()
    updateAMap2D()
  } catch (e) { console.error('AMap init error:', e) }
}

const ZONE_COLORS_2D = ['#60a5fa', '#818cf8', '#f472b6', '#4ade80', '#fb923c', '#34d399']

function buildAMapZones() {
  if (!map || !AMap) return
  for (let z = 0; z < ZONES; z++) {
    const t0 = z / ZONES, t1 = (z + 1) / ZONES
    const pts = []
    for (let k = 0; k <= 10; k++) pts.push(posOnRoute(t0 + (t1 - t0) * k / 10))
    const pl = new AMap.Polyline({
      path: pts.map(p => [p.lng, p.lat]),
      strokeColor: ZONE_COLORS_2D[z], strokeWeight: 8, strokeOpacity: 0.4,
    })
    map.add(pl)
    zonePolylines.push(pl)
  }
}

function updateAMap2D() {
  if (!map || !AMap) return
  zoneStatus.value.forEach((z, i) => {
    const pl = zonePolylines[i]
    if (!pl) return
    if (z.state === 'conflict') pl.setOptions({ strokeColor: '#dc2626', strokeOpacity: 0.9, strokeWeight: 12 })
    else if (z.state === 'occupied') pl.setOptions({ strokeColor: '#f59e0b', strokeOpacity: 0.7, strokeWeight: 10 })
    else pl.setOptions({ strokeColor: ZONE_COLORS_2D[i], strokeOpacity: 0.4, strokeWeight: 8 })
  })

  droneStates.forEach(d => {
    const pos = posOnRoute(d.t)
    const center = new AMap.LngLat(pos.lng, pos.lat)
    const isConflict = d.status === 'conflict'
    const color = isConflict ? '#dc2626' : d.color

    if (!bufferCircles2D[d.id]) {
      bufferCircles2D[d.id] = new AMap.Circle({
        center, radius: bufferR.value,
        strokeColor: color, strokeWeight: 2, strokeOpacity: 0.9,
        fillColor: color, fillOpacity: 0.12,
      })
      map.add(bufferCircles2D[d.id])
    } else {
      bufferCircles2D[d.id].setCenter(center)
      bufferCircles2D[d.id].setRadius(bufferR.value)
      bufferCircles2D[d.id].setOptions({ strokeColor: color, fillColor: color, fillOpacity: isConflict ? 0.25 : 0.12 })
    }

    const icon = isConflict ? '⚠️' : d.status === 'stopped' ? '⏹' : d.speedRatio < 0.5 ? '🐢' : '🚁'
    const label = `${icon} ${d.name} ${Math.round(d.speedRatio * 100)}%`
    if (!droneMarkers2D[d.id]) {
      droneMarkers2D[d.id] = new AMap.Marker({
        position: center,
        content: `<div class="oa-drone-tag" style="background:${color}">${label}</div>`,
        offset: new AMap.Pixel(-38, -14),
      })
      map.add(droneMarkers2D[d.id])
    } else {
      droneMarkers2D[d.id].setPosition(center)
      droneMarkers2D[d.id].setContent(`<div class="oa-drone-tag" style="background:${color}">${label}</div>`)
    }
  })
}

function destroyAMap() {
  if (map) { map.destroy(); map = null }
}

// ── 3D Cesium ─────────────────────────────────────────
let cesiumViewer = null
let cesium3DReady = false
const posProps = {}

function makeDroneCanvas(color, size = 32) {
  const cv = document.createElement('canvas'); cv.width = size; cv.height = size
  const ctx = cv.getContext('2d')
  const c = size / 2
  ctx.strokeStyle = '#fff'; ctx.lineWidth = 2
  ctx.beginPath(); ctx.moveTo(c, c - c*0.6); ctx.lineTo(c, c + c*0.6); ctx.stroke()
  ctx.beginPath(); ctx.moveTo(c - c*0.6, c); ctx.lineTo(c + c*0.6, c); ctx.stroke()
  ;[[-1,-1],[1,-1],[-1,1],[1,1]].forEach(([sx,sy]) => {
    ctx.beginPath(); ctx.arc(c + sx*c*0.6, c + sy*c*0.6, c*0.18, 0, Math.PI*2)
    ctx.fillStyle = color; ctx.fill()
    ctx.strokeStyle = '#fff'; ctx.lineWidth = 1; ctx.stroke()
  })
  ctx.beginPath(); ctx.arc(c, c, c*0.14, 0, Math.PI*2)
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
  cesiumViewer.camera.setView({
    destination: Cesium.Cartesian3.fromDegrees(113.3150, 23.0850, 2200),
    orientation: { heading: Cesium.Math.toRadians(-10), pitch: Cesium.Math.toRadians(-40), roll: 0 },
  })
  cesium3DReady = true
  buildCesiumEntities()
}

function buildCesiumEntities() {
  if (!cesiumViewer || !cesium3DReady) return
  cesiumViewer.entities.removeAll()
  Object.keys(posProps).forEach(k => delete posProps[k])

  droneStates.forEach(d => {
    const initPos = posOnRoute(d.t)
    const posProp = new Cesium.ConstantPositionProperty(
      Cesium.Cartesian3.fromDegrees(initPos.lng, initPos.lat, altAtT(d.t))
    )
    posProps[d.id] = posProp

    // 缓冲球（动态颜色）
    cesiumViewer.entities.add({
      position: posProp,
      ellipsoid: {
        radii: new Cesium.CallbackProperty(() => {
          const R = bufferR.value
          return new Cesium.Cartesian3(R, R, R * 0.7)
        }, false),
        material: new Cesium.ColorMaterialProperty(
          new Cesium.CallbackProperty(() => {
            const isC = d.status === 'conflict'
            return (isC ? Cesium.Color.fromCssColorString('#dc2626') : Cesium.Color.fromCssColorString(d.color))
              .withAlpha(isC ? 0.40 : 0.22)
          }, false)
        ),
        outline: true,
        outlineColor: new Cesium.CallbackProperty(() => {
          const isC = d.status === 'conflict'
          return (isC ? Cesium.Color.fromCssColorString('#dc2626') : Cesium.Color.fromCssColorString(d.color))
            .withAlpha(isC ? 0.85 : 0.55)
        }, false),
        slicePartitions: 20, stackPartitions: 20,
      },
    })

    // 无人机 billboard
    cesiumViewer.entities.add({
      position: posProp,
      billboard: {
        image: makeDroneCanvas(d.color),
        width: 36, height: 36,
        verticalOrigin: Cesium.VerticalOrigin.CENTER,
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
        eyeOffset: new Cesium.Cartesian3(0, 0, -20),
      },
      label: {
        text: new Cesium.CallbackProperty(() => {
          const icon = d.status === 'conflict' ? '⚠' : d.status === 'stopped' ? '⏹' : d.speedRatio < 0.5 ? '↓' : '▶'
          return `${d.name}\n${icon} ${Math.round(d.speedRatio * 100)}%`
        }, false),
        font: '11px sans-serif',
        fillColor: Cesium.Color.WHITE,
        showBackground: true,
        backgroundColor: new Cesium.CallbackProperty(() => {
          return (d.status === 'conflict'
            ? Cesium.Color.fromCssColorString('#dc2626')
            : Cesium.Color.fromCssColorString(d.color)).withAlpha(0.9)
        }, false),
        backgroundPadding: new Cesium.Cartesian2(5, 3),
        pixelOffset: new Cesium.Cartesian2(0, -48),
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
      },
    })
  })

  // 区间线（动态颜色）
  for (let z = 0; z < ZONES; z++) {
    const t0 = z / ZONES, t1 = (z + 1) / ZONES
    const pts = []
    for (let k = 0; k <= 8; k++) {
      const p = posOnRoute(t0 + (t1 - t0) * k / 8)
      pts.push(Cesium.Cartesian3.fromDegrees(p.lng, p.lat, altAtT(t0 + (t1 - t0) * k / 8)))
    }
    const zi = z
    cesiumViewer.entities.add({
      polyline: {
        positions: pts,
        width: 4,
        material: new Cesium.ColorMaterialProperty(
          new Cesium.CallbackProperty(() => {
            const s = zoneStatus.value[zi]
            if (s.state === 'conflict') return Cesium.Color.fromCssColorString('#dc2626').withAlpha(0.9)
            if (s.state === 'occupied') return Cesium.Color.fromCssColorString('#f59e0b').withAlpha(0.7)
            return Cesium.Color.fromCssColorString('#94a3b8').withAlpha(0.4)
          }, false)
        ),
        clampToGround: false,
      },
    })
  }

  cesiumViewer.scene.requestRender()
}

function updateCesium3D() {
  if (!cesiumViewer || !cesium3DReady) return
  droneStates.forEach(d => {
    const pos = posOnRoute(d.t)
    posProps[d.id]?.setValue(Cesium.Cartesian3.fromDegrees(pos.lng, pos.lat, altAtT(d.t)))
  })
  cesiumViewer.scene.requestRender()
}

function destroyCesium() {
  cesium3DReady = false
  if (cesiumViewer && !cesiumViewer.isDestroyed()) cesiumViewer.destroy()
  cesiumViewer = null
}

// ── 模式切换 ──────────────────────────────────────────
const viewMode = ref('2D')
const mapRef = ref(null)
const cesiumRef = ref(null)

async function switchMode(mode) {
  if (viewMode.value === mode) return
  viewMode.value = mode
  await nextTick()
  if (mode === '2D') {
    await initAMap()
  } else {
    if (!cesium3DReady) {
      await initCesium()
    } else {
      buildCesiumEntities()
      updateCesium3D()
    }
  }
}

onMounted(async () => {
  await initAMap()
  addLog('info', '系统初始化完成，共 5 架无人机，分 6 个区间')
})

onUnmounted(() => {
  if (simTimer) cancelAnimationFrame(simTimer)
  destroyAMap()
  destroyCesium()
})
</script>

<style scoped>
.overlap-page { display: flex; height: 100%; overflow: hidden; }

/* 左侧 */
.status-panel {
  width: 300px; flex-shrink: 0; background: #fff; border-right: 1px solid #e5e7eb;
  overflow-y: auto; padding: 14px;
}
.panel-header { display: flex; align-items: center; gap: 8px; margin-bottom: 14px; flex-wrap: wrap; }
.panel-header h2 { font-size: 15px; font-weight: 700; color: #111827; margin: 0; flex: 1; }
.panel-icon { font-size: 18px; }
.section { border-top: 1px solid #f3f4f6; padding-top: 12px; margin-bottom: 12px; }
.section-title { font-size: 13px; font-weight: 600; color: #374151; margin: 0 0 10px; display: flex; align-items: center; gap: 6px; }
.zone-count { font-size: 11px; font-weight: 400; color: #9ca3af; }
.ctrl-row { display: flex; gap: 6px; margin-bottom: 10px; flex-wrap: wrap; }
.param-row { display: flex; align-items: center; gap: 6px; margin-bottom: 8px; }
.param-row > span:first-child { font-size: 12px; color: #6b7280; width: 52px; flex-shrink: 0; }
.unit { font-size: 12px; color: #9ca3af; }

/* 区间网格 */
.zones-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; }
.zone-cell { text-align: center; padding: 6px 4px; border-radius: 6px; font-size: 11px; border: 1px solid transparent; }
.zone-cell.free { background: #f0fdf4; border-color: #bbf7d0; }
.zone-cell.occupied { background: #fefce8; border-color: #fde68a; }
.zone-cell.conflict { background: #fef2f2; border-color: #fecaca; }
.zone-label { font-weight: 700; color: #374151; font-size: 12px; }
.zone-icon { font-size: 14px; margin: 2px 0; }
.zone-drone { font-size: 10px; color: #6b7280; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

/* 无人机状态条 */
.drone-status-item { margin-bottom: 10px; }
.ds-header { display: flex; align-items: center; gap: 6px; margin-bottom: 4px; flex-wrap: wrap; }
.ds-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
.ds-name { font-size: 12px; font-weight: 500; color: #374151; flex: 1; }
.ds-bar-row { display: flex; align-items: center; gap: 6px; }
.ds-bar-bg { flex: 1; height: 8px; background: #f3f4f6; border-radius: 4px; overflow: hidden; }
.ds-bar-fill { height: 100%; border-radius: 4px; transition: width .3s; }
.ds-speed-num { font-size: 11px; color: #6b7280; width: 32px; text-align: right; flex-shrink: 0; }
.ds-meta { display: flex; gap: 8px; margin-top: 2px; }
.ds-meta span { font-size: 10px; color: #9ca3af; }

/* 事件日志 */
.log-section { flex: 1; min-height: 0; }
.event-log { max-height: 160px; overflow-y: auto; }
.event-item { display: flex; gap: 6px; padding: 4px 0; border-bottom: 1px solid #f9fafb; font-size: 11px; }
.event-time { color: #9ca3af; flex-shrink: 0; }
.event-msg { color: #374151; flex: 1; }
.event-item.danger .event-msg { color: #dc2626; font-weight: 600; }
.event-item.warn .event-msg { color: #d97706; }
.event-item.success .event-msg { color: #16a34a; }
.empty-log { text-align: center; color: #d1d5db; font-size: 12px; padding: 14px; }

/* 右侧 */
.right-section { flex: 1; display: flex; flex-direction: column; overflow: hidden; }

/* 切换栏 — 在地图外部，Cesium canvas 无法覆盖它 */
.view-mode-bar {
  flex-shrink: 0; height: 48px; padding: 0 16px;
  background: #fff; border-bottom: 1px solid #e5e7eb;
  display: flex; align-items: center; gap: 14px;
}
.mode-btns { display: flex; gap: 2px; background: #f3f4f6; padding: 3px; border-radius: 8px; flex-shrink: 0; }
.mode-btn {
  padding: 5px 16px; border: none; border-radius: 6px; font-size: 13px; font-weight: 500;
  cursor: pointer; color: #6b7280; background: transparent; transition: all .15s; white-space: nowrap;
}
.mode-btn.active { background: #2563eb; color: #fff; box-shadow: 0 1px 3px rgba(37,99,235,.4); }
.mode-info { display: flex; gap: 12px; font-size: 12px; color: #9ca3af; flex: 1; flex-wrap: wrap; }
.conflict-badge {
  padding: 4px 10px; background: #fef2f2; border: 1px solid #fecaca;
  border-radius: 6px; font-size: 12px; color: #dc2626; font-weight: 600; flex-shrink: 0;
}

/* 地图区 */
.map-area { flex: 1; position: relative; overflow: hidden; }
.map-container { width: 100%; height: 100%; }

/* 3D 图例 */
.scene-legend {
  position: absolute; bottom: 18px; right: 14px;
  background: rgba(15,23,42,0.88); color: #e2e8f0;
  border-radius: 10px; padding: 12px 16px; font-size: 12px;
  box-shadow: 0 4px 16px rgba(0,0,0,.4); z-index: 10; pointer-events: none; min-width: 200px;
}
.sl-title { font-weight: 700; color: #f1f5f9; margin-bottom: 8px; font-size: 13px; }
.sl-item { display: flex; align-items: center; gap: 8px; margin-bottom: 5px; }
.sl-dot { width: 14px; height: 14px; border-radius: 50%; flex-shrink: 0; }
.sl-dot.safe { background: #3b82f6; opacity: 0.8; }
.sl-dot.conflict { background: #dc2626; opacity: 0.9; }
.sl-dot.zone { background: #f59e0b; opacity: 0.8; border-radius: 2px; }
.sl-divider { border-top: 1px solid rgba(255,255,255,.15); margin: 8px 0; }
.sl-note { color: #94a3b8; font-size: 11px; }
</style>

<!-- 全局样式：为 AMap 注入的 DOM 设置样式 -->
<style>
.oa-drone-tag {
  color: #fff; padding: 3px 7px; border-radius: 4px; font-size: 11px;
  white-space: nowrap; box-shadow: 0 1px 4px rgba(0,0,0,.3); font-weight: 500;
}
</style>
