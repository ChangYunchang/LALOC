<!--
  缓冲区重叠分析 — 列车区间模型 + 动态速度调整
  核心逻辑：
    1. 将航线分为 N 个区间，每区间最多容纳 1 架无人机（类铁路闭塞区间）
    2. 实时检测任意两架无人机的缓冲球是否相交（距离 < 2×R）
    3. 当前跟随无人机进入前车所在区间 OR 缓冲球趋近时，动态降速
    4. 区间腾空后自动恢复正常速度
  2D：AMap 圆圈 + 彩色分区折线
  3D：Cesium 半透明缓冲球 + 区间边界垂线 + 高度剖面折线
-->
<template>
  <div class="overlap-page">
    <!-- 左侧控制面板 -->
    <aside class="control-panel">
      <div class="panel-header"><span>🚦</span><h2>安全缓冲分析</h2></div>

      <!-- 参数配置 -->
      <div class="section">
        <h3 class="section-title">参数配置</h3>
        <div class="param-row">
          <span>缓冲半径</span>
          <el-input-number v-model="bufferRadius" :min="50" :max="500" :step="25" size="small" style="width:110px" />
          <span class="unit">m</span>
        </div>
        <div class="param-row">
          <span>区间数量</span>
          <el-select v-model="numZones" size="small" style="width:110px" @change="onParamChange">
            <el-option v-for="n in [3,4,5,6,8]" :key="n" :label="`${n} 个区间`" :value="n" />
          </el-select>
        </div>
        <div class="param-row">
          <span>仿真速度</span>
          <el-slider v-model="simSpeed" :min="5" :max="80" :step="5" style="width:120px" />
          <span class="unit">×</span>
        </div>
      </div>

      <!-- 模拟控制 -->
      <div class="section">
        <h3 class="section-title">模拟控制</h3>
        <div class="sim-time-display">T = {{ formatSimTime(simTime) }}</div>
        <div class="ctrl-btns">
          <el-button :type="running ? 'warning' : 'primary'" size="small" @click="toggleRun">
            {{ running ? '⏸ 暂停' : '▶ 开始' }}
          </el-button>
          <el-button size="small" @click="resetSim">⏮ 重置</el-button>
        </div>
        <div class="conflict-counter" v-if="totalConflicts > 0">
          ⚠️ 累计触发速度调整 <strong>{{ totalConflicts }}</strong> 次
        </div>
      </div>

      <!-- 区间状态 -->
      <div class="section">
        <h3 class="section-title">区间占用状态</h3>
        <div class="zone-table">
          <div class="zone-row zone-header">
            <span>区间</span><span>状态</span><span>占用</span>
          </div>
          <div v-for="z in zoneStatus" :key="z.index" class="zone-row"
            :class="{ 'zone-conflict': z.conflict, 'zone-occupied': z.occupants.length === 1 }">
            <span class="zone-id">Z{{ z.index }}</span>
            <span class="zone-state">
              <span v-if="z.conflict" style="color:#dc2626">🔴 冲突</span>
              <span v-else-if="z.occupants.length === 1" :style="{ color: z.color }">🟢 占用</span>
              <span v-else style="color:#9ca3af">⬜ 空闲</span>
            </span>
            <span class="zone-drone">{{ z.occupants.join(', ') || '—' }}</span>
          </div>
        </div>
      </div>

      <!-- 无人机速度状态 -->
      <div class="section">
        <h3 class="section-title">无人机实时速度</h3>
        <div v-for="d in droneStates" :key="d.id" class="drone-speed-row">
          <span class="drone-dot" :style="{ background: d.color }"></span>
          <span class="drone-label">{{ d.name }}</span>
          <div class="speed-bar-wrap">
            <div class="speed-bar"
              :style="{ width: `${d.speedRatio * 100}%`, background: speedBarColor(d.speedRatio) }"></div>
          </div>
          <span class="speed-pct" :style="{ color: speedBarColor(d.speedRatio) }">
            {{ Math.round(d.speedRatio * 100) }}%
          </span>
          <span class="status-chip" :class="`status-${d.status}`">
            {{ statusLabel(d.status) }}
          </span>
        </div>
      </div>

      <!-- 事件日志 -->
      <div class="section">
        <h3 class="section-title">事件日志</h3>
        <div class="log-wrap">
          <div v-if="!conflictLog.length" class="empty-tip">待仿真开始后记录…</div>
          <div v-for="(log, i) in conflictLog.slice(-6).reverse()" :key="i" class="log-item">
            <span class="log-time">{{ log.time }}</span>
            <span class="log-msg">{{ log.msg }}</span>
          </div>
        </div>
      </div>
    </aside>

    <!-- 右侧地图 -->
    <div class="map-area">
      <!-- 2D/3D 切换 -->
      <div class="mode-toggle-bar">
        <el-button-group size="small">
          <el-button :type="viewMode === '2D' ? 'primary' : 'default'" @click="switchMode('2D')">2D 平面</el-button>
          <el-button :type="viewMode === '3D' ? 'primary' : 'default'" @click="switchMode('3D')">3D 缓冲球</el-button>
        </el-button-group>
      </div>

      <div v-if="viewMode === '2D'" ref="mapRef" class="map-container"></div>
      <div v-if="viewMode === '3D'" ref="cesiumRef" class="map-container"></div>

      <!-- 图例 -->
      <div class="map-legend">
        <div class="legend-title">图例</div>
        <div class="legend-item"><span class="legend-seg" style="background:#3b82f6"></span>空闲区间</div>
        <div class="legend-item"><span class="legend-seg" style="background:#22c55e"></span>已占用区间</div>
        <div class="legend-item"><span class="legend-seg" style="background:#dc2626"></span>冲突区间</div>
        <div class="legend-item"><span class="legend-ball" style="background:rgba(59,130,246,.35)"></span>缓冲球（安全）</div>
        <div class="legend-item"><span class="legend-ball" style="background:rgba(220,38,38,.35)"></span>缓冲球（冲突）</div>
      </div>

      <!-- 信息徽章 -->
      <div class="info-badge">
        <div class="badge-route">🛣 天河→番禺干线｜{{ numZones }} 个区间｜{{ droneStates.length }} 架无人机</div>
        <div class="badge-conflict" v-if="currentConflicts > 0">
          🔴 当前 {{ currentConflicts }} 处缓冲球重叠
        </div>
        <div class="badge-ok" v-else>✅ 当前无缓冲球重叠</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onUnmounted, nextTick } from 'vue'
import AMapLoader from '@amap/amap-jsapi-loader'
import * as Cesium from 'cesium'

// ── 航线定义（天河→番禺） ────────────────────────────
const ROUTE_COORDS = [
  [113.3245, 23.1201],
  [113.3190, 23.1090],
  [113.3130, 23.0960],
  [113.3070, 23.0800],
  [113.3010, 23.0660],
  [113.2960, 23.0540],
  [113.2920, 23.0430],
]
const CRUISE_ALT = 160
const DRONE_COLORS = ['#3b82f6', '#8b5cf6', '#ec4899', '#22c55e', '#f59e0b']
const BASE_SPEED = 15 // m/s

// ── 工具函数 ─────────────────────────────────────────
function haversine(a, b) {
  const R = 6371000
  const dLat = (b.lat - a.lat) * Math.PI / 180
  const dLng = (b.lng - a.lng) * Math.PI / 180
  const s = Math.sin(dLat/2)**2 + Math.cos(a.lat*Math.PI/180)*Math.cos(b.lat*Math.PI/180)*Math.sin(dLng/2)**2
  return R * 2 * Math.atan2(Math.sqrt(s), Math.sqrt(1-s))
}

// 预计算累积距离，用于精确路径插值
const cumDist = [0]
for (let i = 1; i < ROUTE_COORDS.length; i++) {
  cumDist.push(cumDist[i-1] + haversine(
    { lat: ROUTE_COORDS[i-1][1], lng: ROUTE_COORDS[i-1][0] },
    { lat: ROUTE_COORDS[i][1],   lng: ROUTE_COORDS[i][0] }
  ))
}
const ROUTE_LEN = cumDist[cumDist.length - 1]

function posOnRoute(t) {
  t = Math.max(0, Math.min(1, t))
  const dist = t * ROUTE_LEN
  let seg = 0
  while (seg < cumDist.length - 2 && cumDist[seg + 1] < dist) seg++
  const segLen = cumDist[seg + 1] - cumDist[seg]
  const segT = segLen > 0 ? (dist - cumDist[seg]) / segLen : 0
  const a = ROUTE_COORDS[seg], b = ROUTE_COORDS[seg + 1]
  return { lng: a[0] + (b[0] - a[0]) * segT, lat: a[1] + (b[1] - a[1]) * segT }
}

function altAtT(t) {
  if (t < 0.12) return 15 + (CRUISE_ALT - 15) * (t / 0.12)
  if (t > 0.88) return 15 + (CRUISE_ALT - 15) * ((1 - t) / 0.12)
  return CRUISE_ALT
}

// ── 仿真参数 ─────────────────────────────────────────
const bufferRadius = ref(200)
const numZones = ref(5)
const simSpeed = ref(25)
const running = ref(false)
const simTime = ref(0)
const totalConflicts = ref(0)
const currentConflicts = ref(0)
const conflictLog = ref([])

const viewMode = ref('2D')
const mapRef = ref(null)
const cesiumRef = ref(null)

// ── 无人机状态 ────────────────────────────────────────
// 5架无人机，沿同一航线，初始不均匀分布（故意制造区间冲突）
const droneStates = reactive(DRONE_COLORS.map((color, i) => ({
  id: i + 1,
  name: `GZ-D00${i+1}`,
  color,
  t: [0.0, 0.12, 0.30, 0.55, 0.78][i], // 前两架共处 zone0，制造初始冲突
  speed: BASE_SPEED,
  speedRatio: 1.0,
  zone: 0,
  status: 'normal', // 'normal' | 'slowing' | 'stopped'
})))

// ── 区间占用计算 ──────────────────────────────────────
const zoneStatus = computed(() => {
  const n = numZones.value
  return Array.from({ length: n }, (_, z) => {
    const occupants = droneStates.filter(d => d.zone === z)
    return {
      index: z,
      occupants: occupants.map(d => d.name),
      conflict: occupants.length > 1,
      color: occupants.length === 1 ? occupants[0].color : '#9ca3af',
    }
  })
})

// ── 速度调整算法（核心） ──────────────────────────────
function adjustSpeeds(dt) {
  // 按位置从前到后排列（t 大的在前）
  const sorted = [...droneStates].sort((a, b) => b.t - a.t)
  let conflicts = 0

  for (let i = 0; i < sorted.length; i++) {
    const d = sorted[i]
    d.zone = Math.min(Math.floor(d.t * numZones.value), numZones.value - 1)

    if (i === 0) { d.speedRatio = 1.0; d.status = 'normal'; continue }

    const lead = sorted[i - 1]
    const posL = posOnRoute(lead.t)
    const posF = posOnRoute(d.t)
    const dist3D = haversine(posL, posF)

    // ① 区间冲突：同一区间内只允许一架
    if (lead.zone === d.zone) {
      d.speedRatio = 0
      d.status = 'stopped'
      conflicts++
      const msg = `${d.name} 等待：区间Z${d.zone}已被${lead.name}占用`
      addLog(msg)
    }
    // ② 缓冲球接近：距离 < 2.5×R 时按比例降速
    else if (dist3D < bufferRadius.value * 2.5) {
      const ratio = Math.max(0.08, (dist3D - bufferRadius.value) / (bufferRadius.value * 1.5))
      d.speedRatio = ratio
      d.status = ratio < 0.4 ? 'stopped' : 'slowing'
      conflicts++
      if (dist3D < bufferRadius.value * 2) {
        addLog(`⚠️ ${d.name}↔${lead.name} 缓冲球重叠！距 ${dist3D.toFixed(0)}m < ${(bufferRadius.value*2).toFixed(0)}m`)
      }
    }
    // ③ 正常行驶
    else {
      if (d.status !== 'normal') {
        addLog(`${d.name} 恢复正常速度`)
      }
      d.speedRatio = 1.0
      d.status = 'normal'
    }
  }

  // 将排序结果写回 droneStates
  for (const s of sorted) {
    const orig = droneStates.find(d => d.id === s.id)
    if (orig) { orig.speedRatio = s.speedRatio; orig.status = s.status; orig.zone = s.zone }
  }

  currentConflicts.value = conflicts
}

// ── 推进动画帧 ────────────────────────────────────────
let lastFrameTime = 0

function tick() {
  const now = Date.now()
  const dt = lastFrameTime ? Math.min((now - lastFrameTime) / 1000, 0.1) : 0.016
  lastFrameTime = now

  adjustSpeeds(dt)

  for (const d of droneStates) {
    const advance = (BASE_SPEED * d.speedRatio * simSpeed.value * dt) / ROUTE_LEN
    d.t += advance
    if (d.t >= 1) { d.t = 0 } // 循环飞行
    d.speed = BASE_SPEED * d.speedRatio
  }

  simTime.value += dt * simSpeed.value

  if (viewMode.value === '2D') updateAMap2D()
  else updateCesium3D()
}

let animTimer = null
function toggleRun() {
  if (running.value) {
    clearInterval(animTimer); animTimer = null; running.value = false; lastFrameTime = 0
  } else {
    running.value = true
    lastFrameTime = Date.now()
    animTimer = setInterval(tick, 50)
  }
}

function resetSim() {
  clearInterval(animTimer); animTimer = null; running.value = false; lastFrameTime = 0
  const initT = [0.0, 0.12, 0.30, 0.55, 0.78]
  droneStates.forEach((d, i) => {
    d.t = initT[i]; d.speed = BASE_SPEED; d.speedRatio = 1.0; d.zone = 0; d.status = 'normal'
  })
  simTime.value = 0; totalConflicts.value = 0; currentConflicts.value = 0
  conflictLog.value = []
  if (viewMode.value === '2D') updateAMap2D()
  else updateCesium3D()
}

// 防抖日志（同一条消息 2 秒内不重复）
const _lastLogMsg = { msg: '', at: 0 }
function addLog(msg) {
  totalConflicts.value++
  const now = Date.now()
  if (msg === _lastLogMsg.msg && now - _lastLogMsg.at < 2000) return
  _lastLogMsg.msg = msg; _lastLogMsg.at = now
  conflictLog.value.push({ time: formatSimTime(simTime.value), msg })
  if (conflictLog.value.length > 20) conflictLog.value.splice(0, 1)
}

// ── 2D AMap ──────────────────────────────────────────
let AMap = null, map = null
let dynamicOverlays = []

async function initMap() {
  if (!mapRef.value) return
  window._AMapSecurityConfig = { securityJsCode: import.meta.env.VITE_AMAP_SECURITY_CODE }
  try {
    if (!AMap) AMap = await AMapLoader.load({ key: import.meta.env.VITE_AMAP_KEY, version: '2.0', plugins: ['AMap.Scale'] })
    map = new AMap.Map(mapRef.value, {
      viewMode: '2D', zoom: 13,
      center: [113.3090, 23.0810],
      mapStyle: 'amap://styles/whitesmoke',
    })
    map.addControl(new AMap.Scale({ position: 'LB' }))
    drawRouteBase2D()
    updateAMap2D()
  } catch (e) { console.error('AMap init failed:', e) }
}

// 静态：绘制区间背景折线（整条航线的灰色底线）
function drawRouteBase2D() {
  if (!map || !AMap) return
  map.add(new AMap.Polyline({
    path: ROUTE_COORDS.map(c => [c[0], c[1]]),
    strokeColor: '#cbd5e1', strokeWeight: 3, strokeOpacity: 0.6,
  }))

  // 区间边界点标记
  for (let z = 1; z < numZones.value; z++) {
    const p = posOnRoute(z / numZones.value)
    map.add(new AMap.CircleMarker({
      center: [p.lng, p.lat], radius: 5,
      fillColor: '#64748b', fillOpacity: 0.8, strokeColor: '#fff', strokeWeight: 1.5,
    }))
  }
}

function updateAMap2D() {
  if (!map || !AMap) return
  dynamicOverlays.forEach(o => { try { map.remove(o) } catch {} })
  dynamicOverlays = []

  const n = numZones.value

  // 每个区间的彩色分段折线
  for (let z = 0; z < n; z++) {
    const t0 = z / n, t1 = (z + 1) / n
    const pts = []
    for (let k = 0; k <= 8; k++) {
      const t = t0 + (t1 - t0) * k / 8
      const p = posOnRoute(t)
      pts.push([p.lng, p.lat])
    }
    const zone = zoneStatus.value[z]
    const color = zone.conflict ? '#dc2626' : zone.occupants.length ? zone.color : '#94a3b8'
    const weight = zone.occupants.length ? 5 : 3
    const poly = new AMap.Polyline({ path: pts, strokeColor: color, strokeWeight: weight, strokeOpacity: 0.9 })
    map.add(poly)
    dynamicOverlays.push(poly)
  }

  // 无人机标记 + 缓冲圆
  droneStates.forEach(d => {
    const pos = posOnRoute(d.t)

    // 检测是否与其他无人机缓冲球相交
    const isConflict = droneStates.some(other => {
      if (other.id === d.id) return false
      const op = posOnRoute(other.t)
      return haversine(pos, op) < bufferRadius.value * 2
    })

    const circleColor = isConflict ? '#dc2626' : d.color

    const circle = new AMap.Circle({
      center: [pos.lng, pos.lat],
      radius: bufferRadius.value,
      strokeColor: circleColor, strokeWeight: 2, strokeOpacity: 0.85,
      fillColor: circleColor, fillOpacity: isConflict ? 0.22 : 0.10,
    })
    map.add(circle)
    dynamicOverlays.push(circle)

    const speedPct = Math.round(d.speedRatio * 100)
    const icon = d.status === 'stopped' ? '⏹' : d.status === 'slowing' ? '⚠️' : '🚁'
    const marker = new AMap.Marker({
      position: [pos.lng, pos.lat],
      content: `<div style="background:${d.color};color:#fff;padding:2px 7px;border-radius:4px;font-size:11px;white-space:nowrap;box-shadow:0 1px 4px rgba(0,0,0,.3)">${icon} ${d.name} ${speedPct}%</div>`,
      offset: new AMap.Pixel(-30, -14),
    })
    map.add(marker)
    dynamicOverlays.push(marker)
  })
}

function destroyAMap() {
  dynamicOverlays.forEach(o => { try { map?.remove(o) } catch {} })
  dynamicOverlays = []
  map?.destroy(); map = null
}

// ── 3D Cesium ─────────────────────────────────────────
let cesiumViewer = null
// 持久实体引用（避免每帧重建）
const cesiumDroneEntities = []
let cesiumZonePolylines = []
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
    destination: Cesium.Cartesian3.fromDegrees(113.3090, 23.0820, 6500),
    orientation: { heading: Cesium.Math.toRadians(15), pitch: Cesium.Math.toRadians(-48), roll: 0 },
  })
  buildCesiumEntities()
  cesium3DReady = true
}

function buildCesiumEntities() {
  if (!cesiumViewer) return
  cesiumViewer.entities.removeAll()
  cesiumDroneEntities.length = 0
  cesiumZonePolylines.length = 0

  const n = numZones.value

  // 区间折线（颜色用 CallbackProperty 动态更新）
  for (let z = 0; z < n; z++) {
    const t0 = z / n, t1 = (z + 1) / n
    const positions = []
    for (let k = 0; k <= 12; k++) {
      const t = t0 + (t1 - t0) * k / 12
      const p = posOnRoute(t)
      positions.push(Cesium.Cartesian3.fromDegrees(p.lng, p.lat, altAtT(t)))
    }
    const zIdx = z
    const entity = cesiumViewer.entities.add({
      polyline: {
        positions,
        width: new Cesium.CallbackProperty(() => zoneStatus.value[zIdx]?.occupants.length ? 8 : 4, false),
        material: new Cesium.ColorMaterialProperty(
          new Cesium.CallbackProperty(() => {
            const zone = zoneStatus.value[zIdx]
            if (!zone) return Cesium.Color.GRAY
            if (zone.conflict) return Cesium.Color.fromCssColorString('#dc2626')
            if (zone.occupants.length === 1) return Cesium.Color.fromCssColorString(zone.color)
            return Cesium.Color.fromCssColorString('#94a3b8').withAlpha(0.5)
          }, false)
        ),
        clampToGround: false,
        depthFailMaterial: new Cesium.ColorMaterialProperty(Cesium.Color.WHITE.withAlpha(0.15)),
      },
    })
    cesiumZonePolylines.push(entity)
  }

  // 区间边界竖线（垂直标记）
  for (let z = 1; z < n; z++) {
    const t = z / n
    const p = posOnRoute(t)
    const alt = altAtT(t)
    cesiumViewer.entities.add({
      polyline: {
        positions: [
          Cesium.Cartesian3.fromDegrees(p.lng, p.lat, alt - 60),
          Cesium.Cartesian3.fromDegrees(p.lng, p.lat, alt + 60),
        ],
        width: 2,
        material: Cesium.Color.WHITE.withAlpha(0.55),
      },
    })
    cesiumViewer.entities.add({
      position: Cesium.Cartesian3.fromDegrees(p.lng, p.lat, alt + 70),
      label: {
        text: `Z${z-1}|Z${z}`,
        font: '11px monospace',
        fillColor: Cesium.Color.WHITE,
        showBackground: true,
        backgroundColor: Cesium.Color.BLACK.withAlpha(0.5),
        backgroundPadding: new Cesium.Cartesian2(4, 2),
        pixelOffset: new Cesium.Cartesian2(0, 0),
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
        scale: 0.9,
      },
    })
  }

  // 每架无人机：billboard + 缓冲球（用 CallbackProperty 动态颜色）
  droneStates.forEach(d => {
    const initP = posOnRoute(d.t)
    const posProperty = new Cesium.ConstantPositionProperty(
      Cesium.Cartesian3.fromDegrees(initP.lng, initP.lat, altAtT(d.t))
    )
    const cesiumBaseColor = Cesium.Color.fromCssColorString(d.color)

    const isConflictFn = () => droneStates.some(other => {
      if (other.id === d.id) return false
      const op = posOnRoute(other.t)
      const mp = posOnRoute(d.t)
      return haversine(mp, op) < bufferRadius.value * 2
    })

    // 缓冲球
    const sphereEntity = cesiumViewer.entities.add({
      position: posProperty,
      ellipsoid: {
        radii: new Cesium.Cartesian3(bufferRadius.value, bufferRadius.value, bufferRadius.value),
        material: new Cesium.ColorMaterialProperty(
          new Cesium.CallbackProperty(() =>
            isConflictFn()
              ? new Cesium.Color(1, 0.15, 0.15, 0.30)
              : cesiumBaseColor.withAlpha(0.18)
          , false)
        ),
        outline: true,
        outlineColor: new Cesium.CallbackProperty(() =>
          isConflictFn()
            ? Cesium.Color.fromCssColorString('#dc2626').withAlpha(0.75)
            : cesiumBaseColor.withAlpha(0.60)
        , false),
        slicePartitions: 20,
        stackPartitions: 20,
      },
    })

    // 无人机图标
    const droneEntity = cesiumViewer.entities.add({
      position: posProperty,
      billboard: {
        image: makeDroneCanvas(d.color),
        width: 36, height: 36,
        verticalOrigin: Cesium.VerticalOrigin.CENTER,
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
        eyeOffset: new Cesium.Cartesian3(0, 0, -20),
      },
      label: {
        text: new Cesium.CallbackProperty(() => {
          const pct = Math.round(d.speedRatio * 100)
          const icon = d.status === 'stopped' ? '⏹' : d.status === 'slowing' ? '▼' : '▶'
          return `${d.name}\n${icon} ${pct}%`
        }, false),
        font: '11px monospace',
        fillColor: Cesium.Color.WHITE,
        showBackground: true,
        backgroundColor: new Cesium.CallbackProperty(() =>
          isConflictFn()
            ? Cesium.Color.fromCssColorString('#dc2626').withAlpha(0.85)
            : cesiumBaseColor.withAlpha(0.85)
        , false),
        backgroundPadding: new Cesium.Cartesian2(5, 3),
        pixelOffset: new Cesium.Cartesian2(0, -55),
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
      },
    })

    cesiumDroneEntities.push({ d, posProperty, droneEntity, sphereEntity })
  })

  cesiumViewer.scene.requestRender()
}

function updateCesium3D() {
  if (!cesiumViewer || !cesium3DReady) return
  for (const { d, posProperty } of cesiumDroneEntities) {
    const p = posOnRoute(d.t)
    posProperty.setValue(Cesium.Cartesian3.fromDegrees(p.lng, p.lat, altAtT(d.t)))
  }
  cesiumViewer.scene.requestRender()
}

function destroyCesium() {
  cesium3DReady = false
  cesiumDroneEntities.length = 0
  cesiumZonePolylines.length = 0
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

function onParamChange() {
  if (viewMode.value === '3D' && cesium3DReady) buildCesiumEntities()
  else if (viewMode.value === '2D') { destroyAMap() }
}

// ── 辅助工具 ──────────────────────────────────────────
function speedBarColor(ratio) {
  if (ratio < 0.15) return '#dc2626'
  if (ratio < 0.5)  return '#f59e0b'
  return '#22c55e'
}
function statusLabel(s) {
  if (s === 'stopped') return '等待'
  if (s === 'slowing') return '减速'
  return '正常'
}
function formatSimTime(s) {
  const m = Math.floor(s / 60), sec = Math.floor(s % 60)
  return `${String(m).padStart(2,'0')}:${String(sec).padStart(2,'0')}`
}

onUnmounted(() => {
  clearInterval(animTimer)
  destroyAMap()
  destroyCesium()
})
</script>

<style scoped>
.overlap-page { display: flex; height: 100%; overflow: hidden; }

/* ── 左侧面板 ── */
.control-panel {
  width: 310px; flex-shrink: 0; background: #fff; border-right: 1px solid #e5e7eb;
  overflow-y: auto; padding: 14px; display: flex; flex-direction: column; gap: 0;
}
.panel-header { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; font-size: 20px; }
.panel-header h2 { font-size: 15px; font-weight: 700; margin: 0; color: #111827; }
.section { border-top: 1px solid #f3f4f6; padding: 12px 0 2px; }
.section-title { font-size: 12px; font-weight: 600; color: #374151; margin: 0 0 10px; text-transform: uppercase; letter-spacing: .5px; }
.param-row { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; font-size: 12px; color: #6b7280; }
.param-row > span:first-child { width: 60px; flex-shrink: 0; }
.unit { color: #9ca3af; }

.sim-time-display { text-align: center; font-size: 24px; font-weight: 700; color: #2563eb; font-variant-numeric: tabular-nums; margin-bottom: 8px; }
.ctrl-btns { display: flex; gap: 8px; margin-bottom: 8px; }
.conflict-counter { font-size: 11px; color: #dc2626; text-align: center; padding: 4px 0; }

/* Zone table */
.zone-table { font-size: 11px; }
.zone-row { display: grid; grid-template-columns: 28px 1fr 80px; gap: 4px; align-items: center; padding: 3px 4px; border-radius: 4px; }
.zone-header { font-weight: 600; color: #9ca3af; background: #f9fafb; border-radius: 4px; margin-bottom: 2px; }
.zone-id { font-weight: 600; color: #374151; }
.zone-state { font-size: 11px; }
.zone-drone { color: #6b7280; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.zone-occupied { background: #f0fdf4; }
.zone-conflict { background: #fef2f2; }

/* Drone speed bars */
.drone-speed-row { display: flex; align-items: center; gap: 5px; margin-bottom: 7px; }
.drone-dot { width: 9px; height: 9px; border-radius: 50%; flex-shrink: 0; }
.drone-label { font-size: 11px; color: #374151; width: 55px; flex-shrink: 0; }
.speed-bar-wrap { flex: 1; height: 8px; background: #f3f4f6; border-radius: 4px; overflow: hidden; }
.speed-bar { height: 100%; border-radius: 4px; transition: width 0.2s, background 0.2s; }
.speed-pct { font-size: 11px; font-weight: 600; width: 32px; text-align: right; flex-shrink: 0; font-variant-numeric: tabular-nums; }
.status-chip { font-size: 10px; padding: 1px 5px; border-radius: 3px; flex-shrink: 0; }
.status-normal { background: #dcfce7; color: #16a34a; }
.status-slowing { background: #fef9c3; color: #ca8a04; }
.status-stopped { background: #fee2e2; color: #dc2626; }

/* Log */
.log-wrap { max-height: 130px; overflow-y: auto; }
.log-item { display: flex; gap: 6px; padding: 3px 0; border-bottom: 1px solid #f3f4f6; }
.log-time { font-size: 10px; color: #9ca3af; flex-shrink: 0; font-variant-numeric: tabular-nums; }
.log-msg { font-size: 10px; color: #374151; line-height: 1.4; }
.empty-tip { font-size: 11px; color: #9ca3af; text-align: center; padding: 8px 0; }

/* ── 右侧地图 ── */
.map-area { flex: 1; position: relative; overflow: hidden; }
.map-container { width: 100%; height: 100%; }

.mode-toggle-bar {
  position: absolute; top: 12px; left: 50%; transform: translateX(-50%);
  z-index: 100; background: rgba(255,255,255,0.95);
  padding: 6px 12px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.15);
}

.map-legend {
  position: absolute; bottom: 24px; right: 16px; background: rgba(255,255,255,0.95);
  border-radius: 8px; padding: 10px 14px; box-shadow: 0 2px 8px rgba(0,0,0,0.15); font-size: 11px; z-index: 100;
}
.legend-title { font-weight: 600; color: #374151; margin-bottom: 6px; font-size: 12px; }
.legend-item { display: flex; align-items: center; gap: 7px; margin-bottom: 4px; color: #6b7280; }
.legend-seg { display: inline-block; width: 24px; height: 5px; border-radius: 3px; flex-shrink: 0; }
.legend-ball { display: inline-block; width: 14px; height: 14px; border-radius: 50%; flex-shrink: 0; }

.info-badge {
  position: absolute; top: 12px; left: 16px; background: rgba(255,255,255,0.95);
  border-radius: 8px; padding: 8px 14px; box-shadow: 0 2px 8px rgba(0,0,0,0.12); z-index: 100;
}
.badge-route { font-size: 12px; font-weight: 600; color: #1e40af; }
.badge-conflict { font-size: 11px; color: #dc2626; margin-top: 3px; }
.badge-ok { font-size: 11px; color: #16a34a; margin-top: 3px; }
</style>
