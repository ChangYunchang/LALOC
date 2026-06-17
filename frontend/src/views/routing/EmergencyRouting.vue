<!--
  应急航路规划
  场景：某架无人机在执飞途中电量不足/设备故障，需要立即规划一条
        就近降落至充电站的应急路线。
  操作流：
    ① 点击某架无人机的"触发告警"按钮（或系统自动检测低电量）
    ② 地图显示该无人机位置、续航圆圈、附近充电站距离排序
    ③ 选择目标充电站（默认推荐最近且在续航内的）
    ④ 一键生成应急路线，在地图上显示红色虚线路径
-->
<template>
  <div class="emergency-page">
    <!-- ── 左侧操作面板 ─────────────────────────────── -->
    <aside class="left-panel">
      <div class="panel-title">
        <span>🚨</span>
        <div>
          <div class="title-main">应急航路规划</div>
          <div class="title-sub">无人机低电量 / 故障 → 快速导航至充电站</div>
        </div>
      </div>

      <!-- 告警原因选择 -->
      <div class="section">
        <div class="sect-label">告警原因</div>
        <el-select v-model="alertReason" size="small" style="width:100%">
          <el-option v-for="r in ALERT_REASONS" :key="r.value" :label="r.label" :value="r.value" />
        </el-select>
      </div>

      <!-- 飞行中无人机列表 -->
      <div class="section">
        <div class="sect-label">
          飞行中无人机
          <span class="count-badge">{{ DRONES.length }}</span>
          <span class="hint-text">点击触发告警</span>
        </div>
        <div class="drone-list">
          <div v-for="d in DRONES" :key="d.id"
            class="drone-card"
            :class="{ 'is-alert': alertDroneId === d.id, 'low-batt': d.battery < 30 }"
            @click="triggerAlert(d.id)">
            <div class="drone-row1">
              <span class="drone-name">🚁 {{ d.name }}</span>
              <span class="batt-tag" :class="battClass(d.battery)">🔋 {{ d.battery }}%</span>
            </div>
            <div class="drone-route">{{ d.routeName }}</div>
            <div class="drone-row2">
              <span class="drone-region">📍 {{ d.region }}</span>
              <el-tag v-if="alertDroneId === d.id" type="danger" size="small" effect="dark">⚠ 告警中</el-tag>
              <el-tag v-else-if="d.battery < 25" type="warning" size="small">低电量</el-tag>
            </div>
            <div class="batt-bar-bg">
              <div class="batt-bar-fill" :style="{ width: d.battery+'%', background: battColor(d.battery) }"></div>
            </div>
          </div>
        </div>
      </div>

      <!-- 告警详情（选中无人机后显示） -->
      <template v-if="alertDrone">
        <div class="section alert-info-box">
          <div class="alert-header">
            <span class="alert-drone-name">{{ alertDrone.name }}</span>
            <el-tag type="danger" size="small" effect="dark">{{ currentReasonLabel }}</el-tag>
          </div>
          <div class="alert-stats">
            <div class="stat-item">
              <span class="stat-val" :style="{ color: battColor(alertDrone.battery) }">{{ alertDrone.battery }}%</span>
              <span class="stat-key">剩余电量</span>
            </div>
            <div class="stat-item">
              <span class="stat-val">{{ estMinutes }}<small>分</small></span>
              <span class="stat-key">可飞时间</span>
            </div>
            <div class="stat-item">
              <span class="stat-val">{{ (estRange/1000).toFixed(1) }}<small>km</small></span>
              <span class="stat-key">续航范围</span>
            </div>
          </div>
        </div>

        <!-- 就近充电站列表 -->
        <div class="section">
          <div class="sect-label">就近充电站（按距离排序）</div>
          <div class="station-list">
            <div v-for="(s, i) in sortedStations" :key="s.id"
              class="station-item"
              :class="{
                'selected': selectedStationId === s.id,
                'out-range': !s.inRange,
              }"
              @click="s.inRange && selectStation(s.id)">
              <span class="stn-rank">{{ i+1 }}</span>
              <div class="stn-info">
                <div class="stn-name">{{ s.name }}</div>
                <div class="stn-meta">
                  {{ formatDist(s.distance) }} &nbsp;·&nbsp; 空位 {{ s.available }}/{{ s.capacity }}
                </div>
              </div>
              <div class="stn-safety" :class="`safety-${s.safetyKey}`">{{ s.safetyLabel }}</div>
            </div>
          </div>
          <div class="range-note">🔵 续航圆圈已显示在地图上</div>
        </div>
      </template>

      <!-- 规划按钮 -->
      <div class="section" v-if="selectedStationId && !emergencyResult">
        <div class="selected-station-preview">
          <span>目标：{{ selectedStation?.name }}</span>
          <span>{{ formatDist(selectedStation?.distance) }}</span>
        </div>
        <el-button type="danger" style="width:100%;margin-top:8px" size="large"
          :loading="planning" @click="planRoute">
          🚁 立即规划应急路线
        </el-button>
        <el-button style="width:100%;margin-top:6px" size="small" @click="resetAll">取消告警</el-button>
      </div>

      <!-- 规划结果 -->
      <div class="section result-box" v-if="emergencyResult">
        <div class="result-title">✅ 应急路线已生成</div>
        <div class="result-rows">
          <div class="result-row"><span>目标充电站</span><strong>{{ emergencyResult.stationName }}</strong></div>
          <div class="result-row"><span>飞行距离</span><strong>{{ formatDist(emergencyResult.distance) }}</strong></div>
          <div class="result-row"><span>预计到达</span><strong>{{ emergencyResult.eta }}分钟</strong></div>
          <div class="result-row"><span>航点数量</span><strong>{{ emergencyResult.waypoints.length }} 个</strong></div>
        </div>
        <div class="batt-assess" :class="`assess-${emergencyResult.batteryAssess}`">
          {{ emergencyResult.batteryAssessText }}
        </div>
        <el-button type="primary" size="small" style="width:100%;margin-top:10px" @click="exportRoute">
          导出路线 JSON
        </el-button>
        <el-button size="small" style="width:100%;margin-top:6px" @click="resetAll">重置</el-button>
      </div>
    </aside>

    <!-- ── 右侧地图 ─────────────────────────────────── -->
    <div class="map-area">
      <div ref="mapRef" class="map-container"></div>

      <!-- 地图顶部状态条 -->
      <div class="map-topbar" v-if="alertDrone">
        <span class="pulse-dot"></span>
        <span>{{ alertDrone.name }} 触发{{ currentReasonLabel }}告警</span>
        <span class="topbar-region">位于 {{ alertDrone.region }}</span>
      </div>
      <div class="map-topbar idle" v-else>
        <span>地图已加载 · 点击左侧无人机触发应急告警</span>
      </div>

      <!-- 图例 -->
      <div class="map-legend">
        <div class="leg-item"><span class="leg-icon" style="color:#f59e0b">⚡</span>充电站</div>
        <div class="leg-item"><span class="leg-icon">🚁</span>无人机</div>
        <div class="leg-item"><span class="leg-line red-dash"></span>应急路线</div>
        <div class="leg-item"><span class="leg-line gray-line"></span>原始航线</div>
        <div class="leg-item"><span class="leg-circle"></span>续航范围</div>
      </div>

      <!-- 告警无人机信息浮窗（地图右下） -->
      <div class="drone-detail-float" v-if="emergencyResult">
        <div class="float-title">🚨 {{ alertDrone?.name }} → {{ emergencyResult.stationName }}</div>
        <div class="float-row">
          <span>剩余电量</span>
          <div class="float-batt-bar">
            <div :style="{ width: alertDrone?.battery + '%', background: battColor(alertDrone?.battery || 0) }"></div>
          </div>
          <span :style="{ color: battColor(alertDrone?.battery || 0) }">{{ alertDrone?.battery }}%</span>
        </div>
        <div class="float-row">
          <span>路线状态</span>
          <el-tag :type="emergencyResult.batteryAssess === 'safe' ? 'success' : emergencyResult.batteryAssess === 'marginal' ? 'warning' : 'danger'" size="small">
            {{ emergencyResult.batteryAssessText }}
          </el-tag>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import AMapLoader from '@amap/amap-jsapi-loader'
import { ElMessage } from 'element-plus'

// ── 常量数据 ──────────────────────────────────────────
const ALERT_REASONS = [
  { value: 'low_battery', label: '⚡ 电量严重不足' },
  { value: 'device_fault', label: '🔧 设备故障迫降' },
  { value: 'comm_loss',   label: '📡 通信失联备降' },
  { value: 'weather',     label: '🌩 极端天气绕避' },
  { value: 'nfz_expand',  label: '🚫 临时禁区扩展' },
]

// 广州地区无人机充电站（真实地名定位）
const CHARGING_STATIONS = [
  { id: 1, name: '天河智慧充电站', lng: 113.3320, lat: 23.1400, available: 5, capacity: 8 },
  { id: 2, name: '海珠东充电站',   lng: 113.3450, lat: 23.0870, available: 3, capacity: 6 },
  { id: 3, name: '番禺南充电站',   lng: 113.2820, lat: 23.0380, available: 7, capacity: 10 },
  { id: 4, name: '黄埔港区充电站', lng: 113.4150, lat: 23.1080, available: 6, capacity: 8 },
  { id: 5, name: '荔湾西关充电站', lng: 113.2530, lat: 23.1240, available: 2, capacity: 5 },
  { id: 6, name: '越秀中心充电站', lng: 113.2820, lat: 23.1330, available: 4, capacity: 6 },
]

// 飞行中的无人机（位置在各自航线中途）
const DRONES = [
  { id: 1, name: 'GZ-A001', battery: 18, routeName: '天河→番禺干线', region: '天河南路上空',
    position: { lng: 113.3100, lat: 23.0870 },
    routeCoords: [[113.3245,23.1201],[113.3100,23.0870],[113.2994,23.0500]] },
  { id: 2, name: 'GZ-A002', battery: 63, routeName: '白云→荔湾横线', region: '白云中路上空',
    position: { lng: 113.2800, lat: 23.1420 },
    routeCoords: [[113.2994,23.1540],[113.2800,23.1420],[113.2500,23.1050]] },
  { id: 3, name: 'GZ-B001', battery: 31, routeName: '黄埔→天河东线', region: '黄埔大道上空',
    position: { lng: 113.3850, lat: 23.1180 },
    routeCoords: [[113.4500,23.1100],[113.3850,23.1180],[113.3400,23.1201]] },
  { id: 4, name: 'GZ-B002', battery: 47, routeName: '番禺物流专线', region: '番禺大桥上空',
    position: { lng: 113.2994, lat: 23.0650 },
    routeCoords: [[113.3100,23.0750],[113.2994,23.0650],[113.2850,23.0500]] },
  { id: 5, name: 'GZ-C001', battery: 76, routeName: '越秀→南沙纵线', region: '中山大道上空',
    position: { lng: 113.3100, lat: 23.1200 },
    routeCoords: [[113.3100,23.1380],[113.3100,23.1200],[113.3100,23.0500]] },
]

const EST_RANGE_PER_PCT = 140  // 每 1% 电量约可飞 140m（保守估计，留安全余量）
const DRONE_SPEED_MS = 15

// ── 响应式状态 ────────────────────────────────────────
const alertReason = ref('low_battery')
const alertDroneId = ref(null)
const selectedStationId = ref(null)
const emergencyResult = ref(null)
const planning = ref(false)
const mapRef = ref(null)

let AMap = null, map = null
let stationMarkers = [], droneOverlays = [], alertOverlays = [], routeOverlays = []

// ── 计算属性 ──────────────────────────────────────────
const alertDrone = computed(() => DRONES.find(d => d.id === alertDroneId.value) || null)
const currentReasonLabel = computed(() => ALERT_REASONS.find(r => r.value === alertReason.value)?.label || '')
const estRange = computed(() => alertDrone.value ? alertDrone.value.battery * EST_RANGE_PER_PCT : 0)
const estMinutes = computed(() => {
  if (!alertDrone.value) return 0
  return Math.round(estRange.value / DRONE_SPEED_MS / 60 * 10) / 10
})

const sortedStations = computed(() => {
  if (!alertDrone.value) return []
  const pos = alertDrone.value.position
  return CHARGING_STATIONS.map(s => {
    const dist = haversine(pos, { lat: s.lat, lng: s.lng })
    const inRange = dist <= estRange.value
    const safe = dist <= estRange.value * 0.75
    return {
      ...s, distance: dist, inRange,
      safetyKey: safe ? 'safe' : inRange ? 'marginal' : 'out',
      safetyLabel: safe ? '✅ 充足' : inRange ? '⚠️ 勉强' : '❌ 超出',
    }
  }).sort((a, b) => a.distance - b.distance)
})

const selectedStation = computed(() => sortedStations.value.find(s => s.id === selectedStationId.value) || null)

// ── 工具函数 ──────────────────────────────────────────
function haversine(a, b) {
  const R = 6371000
  const dLat = (b.lat - a.lat) * Math.PI / 180
  const dLng = (b.lng - a.lng) * Math.PI / 180
  const s = Math.sin(dLat/2)**2 + Math.cos(a.lat*Math.PI/180)*Math.cos(b.lat*Math.PI/180)*Math.sin(dLng/2)**2
  return R * 2 * Math.atan2(Math.sqrt(s), Math.sqrt(1-s))
}
function formatDist(m) {
  if (!m) return '—'
  return m < 1000 ? `${Math.round(m)}m` : `${(m/1000).toFixed(1)}km`
}
function battColor(p) {
  if (p <= 20) return '#dc2626'
  if (p <= 35) return '#f59e0b'
  return '#16a34a'
}
function battClass(p) {
  if (p <= 20) return 'batt-red'
  if (p <= 35) return 'batt-yellow'
  return 'batt-green'
}

// ── AMap 初始化 ───────────────────────────────────────
async function initMap() {
  if (!mapRef.value) return
  window._AMapSecurityConfig = { securityJsCode: import.meta.env.VITE_AMAP_SECURITY_CODE }
  try {
    if (!AMap) AMap = await AMapLoader.load({ key: import.meta.env.VITE_AMAP_KEY, version: '2.0', plugins: ['AMap.Scale'] })
    map = new AMap.Map(mapRef.value, {
      viewMode: '2D', zoom: 12,
      center: [113.3244, 23.1050],
      mapStyle: 'amap://styles/whitesmoke',
    })
    map.addControl(new AMap.Scale({ position: 'LB' }))
    renderStations()
    renderDroneRoutes()
  } catch (e) { console.error('AMap init failed:', e) }
}

// ── 渲染充电站（始终可见） ────────────────────────────
function renderStations() {
  stationMarkers.forEach(m => { try { map.remove(m) } catch {} })
  stationMarkers = []
  CHARGING_STATIONS.forEach(s => {
    const isSelected = selectedStationId.value === s.id
    const isInRange = alertDrone.value
      ? haversine(alertDrone.value.position, { lat: s.lat, lng: s.lng }) <= estRange.value
      : true
    const bg = isSelected ? '#16a34a' : isInRange ? '#f59e0b' : '#94a3b8'
    const m = new AMap.Marker({
      position: [s.lng, s.lat],
      content: `<div style="background:${bg};color:#fff;padding:4px 10px;border-radius:6px;font-size:11px;font-weight:600;box-shadow:0 2px 6px rgba(0,0,0,.25);white-space:nowrap;border:2px solid #fff;text-align:center">
        ⚡ ${s.name}<br><span style="font-size:10px;opacity:.85">空位 ${s.available}/${s.capacity}</span>
      </div>`,
      offset: new AMap.Pixel(-50, -30),
      zIndex: isSelected ? 300 : 150,
    })
    map.add(m)
    stationMarkers.push(m)
  })
}

// ── 渲染所有无人机及其航线 ───────────────────────────
function renderDroneRoutes() {
  droneOverlays.forEach(o => { try { map.remove(o) } catch {} })
  droneOverlays = []
  DRONES.forEach(d => {
    const isAlert = alertDroneId.value === d.id
    // 原始航线（灰色）
    const routeLine = new AMap.Polyline({
      path: d.routeCoords.map(c => [c[0], c[1]]),
      strokeColor: isAlert ? '#475569' : '#94a3b8',
      strokeWeight: isAlert ? 2.5 : 1.5,
      strokeOpacity: isAlert ? 0.75 : 0.4,
    })
    map.add(routeLine)
    droneOverlays.push(routeLine)

    // 无人机当前位置标记
    const bg = isAlert ? '#dc2626' : battColor(d.battery)
    const icon = isAlert ? '🚨' : '🚁'
    const cssClass = isAlert ? ' em-alert-marker' : ''
    const m = new AMap.Marker({
      position: [d.position.lng, d.position.lat],
      content: `<div class="${cssClass.trim()}" style="background:${bg};color:#fff;padding:4px 10px;border-radius:6px;font-size:12px;font-weight:${isAlert?700:500};box-shadow:0 2px 8px rgba(0,0,0,.3);white-space:nowrap;border:2px solid #fff">
        ${icon} ${d.name} 🔋${d.battery}%
      </div>`,
      offset: new AMap.Pixel(-42, -16),
      zIndex: isAlert ? 400 : 100,
    })
    map.add(m)
    droneOverlays.push(m)
  })
}

// ── 渲染续航圆圈和告警覆盖 ───────────────────────────
function renderAlertOverlays() {
  alertOverlays.forEach(o => { try { map.remove(o) } catch {} })
  alertOverlays = []
  if (!alertDrone.value) return

  const d = alertDrone.value
  // 续航圆圈（蓝色虚线）
  const circle = new AMap.Circle({
    center: [d.position.lng, d.position.lat],
    radius: estRange.value,
    strokeColor: '#2563eb', strokeWeight: 2,
    strokeOpacity: 0.5, strokeStyle: 'dashed',
    fillColor: '#2563eb', fillOpacity: 0.04,
  })
  map.add(circle)
  alertOverlays.push(circle)

  // 安全边界圆（75% 续航，绿色）
  const safeCircle = new AMap.Circle({
    center: [d.position.lng, d.position.lat],
    radius: estRange.value * 0.75,
    strokeColor: '#16a34a', strokeWeight: 1.5,
    strokeOpacity: 0.35, strokeStyle: 'dashed',
    fillColor: '#16a34a', fillOpacity: 0.03,
  })
  map.add(safeCircle)
  alertOverlays.push(safeCircle)

  // 标注"续航边界"文字
  const edgePt = new AMap.LngLat(d.position.lng + estRange.value / 111000, d.position.lat)
  const rangeLabel = new AMap.Text({
    position: edgePt,
    text: `续航 ${formatDist(estRange.value)}`,
    style: { fontSize: '11px', color: '#2563eb', background: 'rgba(255,255,255,0.8)', padding: '2px 6px', borderRadius: '4px', border: '1px solid #bfdbfe' },
  })
  map.add(rangeLabel)
  alertOverlays.push(rangeLabel)

  map.setCenter([d.position.lng, d.position.lat])
  map.setZoom(13)
}

// ── 绘制应急路线 ──────────────────────────────────────
function drawEmergencyRoute(waypoints) {
  routeOverlays.forEach(o => { try { map.remove(o) } catch {} })
  routeOverlays = []

  // 红色虚线应急路线
  const line = new AMap.Polyline({
    path: waypoints.map(w => [w.lng, w.lat]),
    strokeColor: '#dc2626', strokeWeight: 3,
    strokeStyle: 'dashed', strokeDasharray: [12, 6],
    strokeOpacity: 0.9, lineJoin: 'round', lineCap: 'round',
  })
  map.add(line)
  routeOverlays.push(line)

  // 箭头方向折线（稍细）
  const arrowLine = new AMap.Polyline({
    path: waypoints.map(w => [w.lng, w.lat]),
    strokeColor: '#dc2626', strokeWeight: 1,
    strokeOpacity: 0.3, showDir: true,
  })
  map.add(arrowLine)
  routeOverlays.push(arrowLine)

  // 起点标记（出发）
  const startM = new AMap.Marker({
    position: [waypoints[0].lng, waypoints[0].lat],
    content: `<div style="background:#dc2626;color:#fff;padding:4px 10px;border-radius:6px;font-size:12px;font-weight:700;box-shadow:0 2px 8px rgba(220,38,38,.5);border:2px solid #fff;white-space:nowrap">
      📍 ${alertDrone.value?.name} 出发
    </div>`,
    offset: new AMap.Pixel(-48, -18),
    zIndex: 500,
  })
  map.add(startM)
  routeOverlays.push(startM)

  // 终点标记（目标充电站，高亮绿色）
  const endW = waypoints[waypoints.length - 1]
  const endM = new AMap.Marker({
    position: [endW.lng, endW.lat],
    content: `<div style="background:#16a34a;color:#fff;padding:5px 12px;border-radius:6px;font-size:12px;font-weight:700;box-shadow:0 2px 8px rgba(22,163,74,.5);border:2px solid #fff;white-space:nowrap">
      ⚡ ${selectedStation.value?.name}
    </div>`,
    offset: new AMap.Pixel(-52, -20),
    zIndex: 500,
  })
  map.add(endM)
  routeOverlays.push(endM)

  // 中间航点
  waypoints.slice(1, -1).forEach((w, i) => {
    const m = new AMap.CircleMarker({
      center: [w.lng, w.lat], radius: 5,
      fillColor: '#f59e0b', fillOpacity: 0.9,
      strokeColor: '#fff', strokeWeight: 1.5,
    })
    map.add(m)
    routeOverlays.push(m)
  })

  // 地图自适应显示整条路线
  setTimeout(() => { try { map.setFitView([line], false, [80, 80, 80, 80]) } catch {} }, 100)
}

// ── 操作函数 ──────────────────────────────────────────
function triggerAlert(droneId) {
  if (alertDroneId.value === droneId) {
    resetAll(); return
  }
  emergencyResult.value = null
  selectedStationId.value = null
  alertDroneId.value = droneId
  const d = DRONES.find(d => d.id === droneId)
  if (d && d.battery < 30) alertReason.value = 'low_battery'
  ElMessage({ type: 'warning', message: `${d?.name} 已触发告警：${ALERT_REASONS.find(r=>r.value===alertReason.value)?.label}` })
}

function selectStation(stationId) {
  selectedStationId.value = stationId
  renderStations()
}

async function planRoute() {
  if (!alertDrone.value || !selectedStation.value) return
  planning.value = true
  await new Promise(r => setTimeout(r, 900))

  const from = alertDrone.value.position
  const to = { lng: selectedStation.value.lng, lat: selectedStation.value.lat }
  const dist = selectedStation.value.distance

  // 生成绕行航点（轻微偏置模拟规避）
  const mid1Lng = from.lng + (to.lng - from.lng) * 0.35 + 0.004
  const mid1Lat = from.lat + (to.lat - from.lat) * 0.35
  const mid2Lng = from.lng + (to.lng - from.lng) * 0.70 - 0.002
  const mid2Lat = from.lat + (to.lat - from.lat) * 0.70 + 0.003

  const waypoints = [
    { lng: from.lng, lat: from.lat, alt: 120, remark: `${alertDrone.value.name} 当前位置` },
    { lng: mid1Lng, lat: mid1Lat, alt: 150, remark: '上升爬高·绕避节点1' },
    { lng: mid2Lng, lat: mid2Lat, alt: 130, remark: '水平巡航·绕避节点2' },
    { lng: to.lng, lat: to.lat, alt: 20, remark: `落地·${selectedStation.value.name}` },
  ]

  const eta = +(dist / DRONE_SPEED_MS / 60).toFixed(1)
  const needed = dist / EST_RANGE_PER_PCT
  const batt = alertDrone.value.battery
  const assessKey = batt >= needed * 1.3 ? 'safe' : batt >= needed ? 'marginal' : 'insufficient'
  const assessText = {
    safe: `✅ 电量充足（剩余 ${batt}%，需要约 ${needed.toFixed(0)}%）`,
    marginal: `⚠️ 电量勉强（剩余 ${batt}%，接近需要量）`,
    insufficient: `❌ 电量不足（剩余 ${batt}%，不足以到达）`,
  }[assessKey]

  emergencyResult.value = {
    stationName: selectedStation.value.name,
    distance: dist,
    eta,
    waypoints,
    batteryAssess: assessKey,
    batteryAssessText: assessText,
  }

  drawEmergencyRoute(waypoints)
  renderDroneRoutes()

  ElMessage({ type: assessKey === 'insufficient' ? 'warning' : 'success',
    message: `应急路线已生成 → ${selectedStation.value.name}，预计 ${eta} 分钟` })
  planning.value = false
}

function resetAll() {
  alertDroneId.value = null
  selectedStationId.value = null
  emergencyResult.value = null
  alertOverlays.forEach(o => { try { map?.remove(o) } catch {} }); alertOverlays = []
  routeOverlays.forEach(o => { try { map?.remove(o) } catch {} }); routeOverlays = []
  renderStations()
  renderDroneRoutes()
  map?.setCenter([113.3244, 23.1050])
  map?.setZoom(12)
}

function exportRoute() {
  if (!emergencyResult.value) return
  const data = {
    drone: alertDrone.value?.name,
    reason: currentReasonLabel.value,
    target_station: emergencyResult.value.stationName,
    distance_m: Math.round(emergencyResult.value.distance),
    eta_minutes: emergencyResult.value.eta,
    waypoints: emergencyResult.value.waypoints,
    generated_at: new Date().toISOString(),
  }
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
  const a = document.createElement('a'); a.href = URL.createObjectURL(blob)
  a.download = `emergency_route_${alertDrone.value?.name}_${Date.now()}.json`; a.click()
}

// ── watch ─────────────────────────────────────────────
watch(alertDroneId, () => {
  renderDroneRoutes()
  renderAlertOverlays()
  renderStations()
})
watch(selectedStationId, () => renderStations())

onMounted(() => { if (mapRef.value) initMap() })
watch(mapRef, el => { if (el && !map) initMap() })
onUnmounted(() => { map?.destroy() })
</script>

<!-- 全局样式：AMap 注入的 DOM 无法使用 scoped -->
<style>
@keyframes emergencyPulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(220, 38, 38, 0.5); }
  50%       { box-shadow: 0 0 0 14px rgba(220, 38, 38, 0); }
}
.em-alert-marker {
  animation: emergencyPulse 1.4s ease-in-out infinite;
  border-radius: 6px;
}
</style>

<style scoped>
.emergency-page { display: flex; height: 100%; overflow: hidden; }

/* ── 左侧面板 ── */
.left-panel {
  width: 320px; flex-shrink: 0; overflow-y: auto; background: #fff;
  border-right: 1px solid #e5e7eb; padding: 14px; display: flex; flex-direction: column; gap: 0;
}
.panel-title { display: flex; align-items: flex-start; gap: 10px; font-size: 20px; margin-bottom: 12px; }
.title-main { font-size: 15px; font-weight: 700; color: #111827; }
.title-sub  { font-size: 11px; color: #9ca3af; margin-top: 2px; }

.section { border-top: 1px solid #f3f4f6; padding: 12px 0 4px; }
.sect-label {
  font-size: 11px; font-weight: 600; color: #6b7280; text-transform: uppercase;
  letter-spacing: .6px; margin-bottom: 8px; display: flex; align-items: center; gap: 6px;
}
.count-badge { background: #2563eb; color: #fff; font-size: 10px; padding: 1px 6px; border-radius: 10px; font-weight: 700; }
.hint-text { font-size: 10px; color: #9ca3af; font-weight: 400; letter-spacing: 0; }

/* Drone cards */
.drone-list { display: flex; flex-direction: column; gap: 6px; }
.drone-card {
  border: 1.5px solid #e5e7eb; border-radius: 8px; padding: 9px 10px;
  cursor: pointer; transition: all .15s; background: #fafafa;
}
.drone-card:hover { border-color: #93c5fd; background: #eff6ff; }
.drone-card.is-alert { border-color: #dc2626; background: #fef2f2; }
.drone-card.low-batt { border-color: #fbbf24; }
.drone-row1 { display: flex; justify-content: space-between; align-items: center; margin-bottom: 2px; }
.drone-name { font-size: 13px; font-weight: 600; color: #111827; }
.batt-tag { font-size: 11px; font-weight: 600; padding: 2px 6px; border-radius: 4px; }
.batt-tag.batt-red    { background: #fee2e2; color: #dc2626; }
.batt-tag.batt-yellow { background: #fef9c3; color: #ca8a04; }
.batt-tag.batt-green  { background: #dcfce7; color: #16a34a; }
.drone-route { font-size: 11px; color: #6b7280; margin-bottom: 4px; }
.drone-row2 { display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px; }
.drone-region { font-size: 10px; color: #9ca3af; }
.batt-bar-bg { height: 4px; background: #f3f4f6; border-radius: 2px; overflow: hidden; }
.batt-bar-fill { height: 100%; border-radius: 2px; transition: width .3s; }

/* Alert info */
.alert-info-box { background: #fef2f2; border-radius: 8px; padding: 10px; border: 1px solid #fecaca; }
.alert-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
.alert-drone-name { font-size: 14px; font-weight: 700; color: #dc2626; }
.alert-stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; }
.stat-item { text-align: center; background: #fff; border-radius: 6px; padding: 6px 4px; }
.stat-val { display: block; font-size: 18px; font-weight: 700; color: #111827; font-variant-numeric: tabular-nums; }
.stat-val small { font-size: 11px; font-weight: 400; color: #9ca3af; }
.stat-key { display: block; font-size: 10px; color: #9ca3af; margin-top: 1px; }

/* Station list */
.station-list { display: flex; flex-direction: column; gap: 4px; margin-bottom: 6px; }
.station-item {
  display: flex; align-items: center; gap: 8px; padding: 7px 9px;
  border: 1.5px solid #e5e7eb; border-radius: 7px; cursor: pointer; transition: all .12s;
}
.station-item:hover:not(.out-range) { border-color: #93c5fd; background: #eff6ff; }
.station-item.selected { border-color: #16a34a; background: #f0fdf4; }
.station-item.out-range { opacity: 0.5; cursor: not-allowed; }
.stn-rank { width: 18px; height: 18px; background: #e5e7eb; border-radius: 50%; font-size: 10px; font-weight: 700; color: #6b7280; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.stn-info { flex: 1; min-width: 0; }
.stn-name { font-size: 12px; font-weight: 600; color: #374151; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.stn-meta { font-size: 10px; color: #9ca3af; margin-top: 1px; }
.stn-safety { font-size: 11px; white-space: nowrap; flex-shrink: 0; }
.safety-safe     { color: #16a34a; }
.safety-marginal { color: #ca8a04; }
.safety-out      { color: #dc2626; }
.range-note { font-size: 10px; color: #6b7280; text-align: center; padding: 2px 0; }

/* Selected station preview */
.selected-station-preview {
  display: flex; justify-content: space-between;
  padding: 8px 10px; background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 6px;
  font-size: 12px; color: #15803d; font-weight: 600;
}

/* Result box */
.result-box { background: #f0fdf4; border-radius: 8px; padding: 10px; border: 1px solid #bbf7d0; }
.result-title { font-size: 13px; font-weight: 700; color: #16a34a; margin-bottom: 8px; }
.result-rows { display: flex; flex-direction: column; gap: 4px; margin-bottom: 8px; }
.result-row { display: flex; justify-content: space-between; font-size: 12px; color: #374151; }
.result-row strong { color: #111827; }
.batt-assess { font-size: 11px; padding: 5px 8px; border-radius: 6px; line-height: 1.5; }
.assess-safe         { background: #dcfce7; color: #15803d; }
.assess-marginal     { background: #fef9c3; color: #854d0e; }
.assess-insufficient { background: #fee2e2; color: #b91c1c; }

/* ── 右侧地图 ── */
.map-area { flex: 1; position: relative; overflow: hidden; }
.map-container { width: 100%; height: 100%; }

.map-topbar {
  position: absolute; top: 0; left: 0; right: 0; z-index: 100;
  background: rgba(220, 38, 38, 0.9); color: #fff;
  padding: 8px 16px; font-size: 13px; font-weight: 600;
  display: flex; align-items: center; gap: 10px;
}
.map-topbar.idle { background: rgba(30, 64, 175, 0.85); font-weight: 400; font-size: 12px; }
.topbar-region { font-size: 11px; font-weight: 400; opacity: 0.85; }

.pulse-dot {
  width: 10px; height: 10px; border-radius: 50%; background: #fff;
  flex-shrink: 0; animation: pulseDot 1s ease-in-out infinite;
}
@keyframes pulseDot {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(0.7); }
}

.map-legend {
  position: absolute; bottom: 20px; right: 14px;
  background: rgba(255,255,255,0.95); border-radius: 8px;
  padding: 10px 14px; box-shadow: 0 2px 8px rgba(0,0,0,0.15);
  font-size: 11px; z-index: 100;
}
.leg-item { display: flex; align-items: center; gap: 7px; margin-bottom: 5px; color: #6b7280; }
.leg-item:last-child { margin-bottom: 0; }
.leg-icon { font-size: 14px; }
.leg-drone { font-size: 13px; }
.leg-line { display: inline-block; width: 28px; height: 3px; border-radius: 2px; flex-shrink: 0; }
.red-dash { background: repeating-linear-gradient(90deg, #dc2626 0 8px, transparent 8px 14px); }
.gray-line { background: #94a3b8; }
.leg-circle { display: inline-block; width: 14px; height: 14px; border-radius: 50%; flex-shrink: 0; border: 2px dashed #2563eb; background: rgba(37,99,235,0.05); }

/* 浮窗 */
.drone-detail-float {
  position: absolute; bottom: 20px; left: 14px;
  background: rgba(255,255,255,0.97); border-radius: 10px;
  padding: 12px 14px; box-shadow: 0 3px 12px rgba(0,0,0,0.15);
  min-width: 210px; z-index: 100;
}
.float-title { font-size: 12px; font-weight: 700; color: #111827; margin-bottom: 8px; }
.float-row { display: flex; align-items: center; gap: 8px; font-size: 11px; color: #6b7280; margin-bottom: 5px; }
.float-row > span:first-child { width: 55px; flex-shrink: 0; }
.float-batt-bar { flex: 1; height: 8px; background: #f3f4f6; border-radius: 4px; overflow: hidden; }
.float-batt-bar > div { height: 100%; border-radius: 4px; transition: width .3s; }
</style>
