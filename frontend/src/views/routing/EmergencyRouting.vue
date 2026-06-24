<!--
  应急航路规划
  场景：某架无人机在执飞途中电量不足/设备故障，需要立即规划一条
        就近降落至充电站/维修站的应急路线。
  路线渲染效果与常规路径规划保持一致：
    爬升=绿色 / 巡航=蓝色 / 下降=橙色，逐段着色折线 + 方向箭头。
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

      <!-- 告警原因筛选 -->
      <div class="section">
        <div class="sect-label">
          告警原因筛选
          <span class="filter-count">{{ filteredDrones.length }}/{{ DRONES.length }}</span>
        </div>
        <el-select v-model="reasonFilter" size="small" style="width:100%">
          <el-option v-for="r in ALERT_REASONS" :key="r.value" :label="r.label" :value="r.value" />
        </el-select>
      </div>

      <!-- 飞行中无人机列表 -->
      <div class="section">
        <div class="sect-label">
          飞行中无人机
          <span class="count-badge">{{ filteredDrones.length }}</span>
          <span class="hint-text">点击触发告警</span>
        </div>
        <div class="drone-list">
          <div v-for="d in filteredDrones" :key="d.id"
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
              <el-tag v-else :type="reasonTagType(d.alertReason)" size="small">{{ ALERT_REASON_LABELS[d.alertReason] }}</el-tag>
            </div>
            <div class="batt-bar-bg">
              <div class="batt-bar-fill" :style="{ width: d.battery+'%', background: battColor(d.battery) }"></div>
            </div>
          </div>
          <div v-if="filteredDrones.length === 0" class="empty-filter">暂无此类告警无人机</div>
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

        <!-- 就近站点列表 -->
        <div class="section">
          <div class="sect-label">就近站点（按距离排序）</div>
          <div class="station-list">
            <div v-for="(s, i) in sortedStations" :key="s.id"
              class="station-item"
              :class="{
                'selected': selectedStationId === s.id,
                'out-range': !s.inRange,
                'is-planning': planning && selectedStationId === s.id,
              }"
              @click="s.inRange && !planning && selectStation(s.id)">
              <span class="stn-rank">{{ i+1 }}</span>
              <div class="stn-info">
                <div class="stn-name">
                  <span class="stn-type-icon">{{ s.type === 'repair' ? '🔧' : '⚡' }}</span>
                  {{ s.name }}
                </div>
                <div class="stn-meta">
                  {{ formatDist(s.distance) }} &nbsp;·&nbsp;
                  {{ s.type === 'repair' ? '维修位' : '空位' }} {{ s.available }}/{{ s.capacity }}
                </div>
              </div>
              <div class="stn-safety" :class="`safety-${s.safetyKey}`">{{ s.safetyLabel }}</div>
            </div>
          </div>
          <div class="range-note">🔵 续航圆圈已显示在地图上</div>
        </div>
      </template>

      <!-- 规划中状态 -->
      <div class="section" v-if="planning">
        <div class="planning-status">
          <span class="planning-spinner"></span>
          <span>正在规划航线至 {{ selectedStation?.name }}…</span>
        </div>
      </div>

      <!-- 规划结果 -->
      <div class="section result-box" v-if="emergencyResult">
        <div class="result-title">✅ 应急路线已生成</div>
        <div class="result-rows">
          <div class="result-row"><span>目标站点</span><strong>{{ emergencyResult.stationName }}</strong></div>
          <div class="result-row"><span>飞行距离</span><strong>{{ formatDist(emergencyResult.distance) }}</strong></div>
          <div class="result-row"><span>预计到达</span><strong>{{ emergencyResult.eta }}分钟</strong></div>
          <div class="result-row"><span>航点数量</span><strong>{{ emergencyResult.waypoints.length }} 个</strong></div>
        </div>
        <!-- 相位分段说明 -->
        <div class="phase-legend-row">
          <span class="phase-pill" style="background:#22c55e20;color:#16a34a;border-color:#86efac">▲ 爬升</span>
          <span class="phase-pill" style="background:#3b82f620;color:#1d4ed8;border-color:#93c5fd">→ 巡航</span>
          <span class="phase-pill" style="background:#f59e0b20;color:#b45309;border-color:#fcd34d">▼ 下降</span>
        </div>
        <div class="batt-assess" :class="`assess-${emergencyResult.batteryAssess}`">
          {{ emergencyResult.batteryAssessText }}
        </div>
        <el-button type="primary" size="small" style="width:100%;margin-top:10px" @click="exportRoute">
          导出路线 JSON
        </el-button>
        <el-button size="small" style="width:100%;margin-top:6px" @click="cancelRoute">重新选站</el-button>
        <el-button size="small" style="width:100%;margin-top:6px" @click="resetAll">取消告警</el-button>
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
        <div class="leg-title">应急路线图例</div>
        <div class="leg-item"><span class="leg-line" style="background:#22c55e"></span>爬升阶段</div>
        <div class="leg-item"><span class="leg-line" style="background:#3b82f6"></span>巡航阶段</div>
        <div class="leg-item"><span class="leg-line" style="background:#f59e0b"></span>下降落地</div>
        <div class="leg-item"><span class="leg-icon">⚡</span>充电站</div>
        <div class="leg-item"><span class="leg-icon">🔧</span>维修站</div>
        <div class="leg-item"><span class="leg-icon">🚁</span>无人机</div>
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
import { SAMPLE_ROUTES } from '@/data/sampleRoutes'

// ── 常量数据 ──────────────────────────────────────────
const ALERT_REASONS = [
  { value: 'all',          label: '全部告警' },
  { value: 'low_battery',  label: '⚡ 电量严重不足' },
  { value: 'device_fault', label: '🔧 设备故障迫降' },
  { value: 'comm_loss',    label: '📡 通信失联备降' },
]

const ALERT_REASON_LABELS = {
  low_battery:  '⚡ 电量不足',
  device_fault: '🔧 设备故障',
  comm_loss:    '📡 通信失联',
}

// 充电/维修站 — 均位于示例航线的关键节点附近
const CHARGING_STATIONS = [
  // 天河枢纽：航线 1/2/3/5/8/9 均经过 [113.3245,23.1201]，站点略偏东北
  { id: 1, name: '天河枢纽充电站', lng: 113.3260, lat: 23.1218, available: 5, capacity: 8,  type: 'charge' },
  // 白云交叉：航线 1/3/5/6/7 经过 [113.3100,23.1050]，站点略偏西南
  { id: 2, name: '白云路口充电站', lng: 113.3085, lat: 23.1038, available: 3, capacity: 6,  type: 'charge' },
  // 番禺起点：航线 1/9 起点 [113.2671,23.0900]，旁边设维修站
  { id: 3, name: '番禺起点维修站', lng: 113.2655, lat: 23.0885, available: 7, capacity: 10, type: 'repair' },
  // 黄埔西侧：航线 3/4 经过 [113.3580,23.1050]，站点略偏东
  { id: 4, name: '黄埔西侧充电站', lng: 113.3600, lat: 23.1062, available: 6, capacity: 8,  type: 'charge' },
  // 荔湾起点：航线 5/7 起点/经点 [113.2671,23.1380]，站点略偏西
  { id: 5, name: '荔湾起点充电站', lng: 113.2650, lat: 23.1395, available: 2, capacity: 5,  type: 'charge' },
  // 越秀南：航线 6/9 起点 [113.3100,23.0750]，设维修站
  { id: 6, name: '越秀南维修站',   lng: 113.3115, lat: 23.0735, available: 4, capacity: 6,  type: 'repair' },
]

// 飞行中无人机 — routeCoords 直接取 SAMPLE_ROUTES 的 Catmull-Rom 插值点，保证与态势大屏一致
const DRONES = [
  {
    id: 1, name: 'GZ-A001', battery: 18, alertReason: 'low_battery',
    routeName: '番禺→天河干线', region: '天河南路上空',
    position: { lng: 113.3100, lat: 23.1050 },
    routeCoords: SAMPLE_ROUTES[0].pts,
  },
  {
    id: 2, name: 'GZ-A002', battery: 63, alertReason: 'comm_loss',
    routeName: '白云→天河横线', region: '白云中路上空',
    position: { lng: 113.3100, lat: 23.1380 },
    routeCoords: SAMPLE_ROUTES[1].pts,
  },
  {
    id: 3, name: 'GZ-B001', battery: 31, alertReason: 'device_fault',
    routeName: '黄埔→白云线', region: '黄埔大道上空',
    position: { lng: 113.3400, lat: 23.1201 },
    routeCoords: SAMPLE_ROUTES[2].pts,
  },
  {
    id: 4, name: 'GZ-B002', battery: 47, alertReason: 'device_fault',
    routeName: '番禺→天河南线', region: '番禺大桥上空',
    position: { lng: 113.3100, lat: 23.0900 },
    routeCoords: SAMPLE_ROUTES[8].pts,
  },
  {
    id: 5, name: 'GZ-C001', battery: 76, alertReason: 'comm_loss',
    routeName: '越秀纵向线', region: '越秀中山大道上空',
    position: { lng: 113.3100, lat: 23.1200 },
    routeCoords: SAMPLE_ROUTES[5].pts,
  },
]

const EST_RANGE_PER_PCT = 140  // 每 1% 电量约可飞 140m（保守估计，留安全余量）
const DRONE_SPEED_MS = 15

// 应急路线相位颜色（与 Amap2DView PLAN_PHASE_COLORS 一致）
const PHASE_COLORS = {
  ascent:  '#22c55e',
  cruise:  '#3b82f6',
  descent: '#f59e0b',
}

// ── 响应式状态 ────────────────────────────────────────
const reasonFilter = ref('all')       // 列表筛选器（不影响已触发告警的原因）
const alertDroneId = ref(null)
const selectedStationId = ref(null)
const emergencyResult = ref(null)
const planning = ref(false)
const mapRef = ref(null)

let AMap = null, map = null
let stationMarkers = [], droneOverlays = [], alertOverlays = [], routeOverlays = []

// ── 计算属性 ──────────────────────────────────────────
const alertDrone = computed(() => DRONES.find(d => d.id === alertDroneId.value) || null)
const currentReasonLabel = computed(() => ALERT_REASON_LABELS[alertDrone.value?.alertReason] || '')
const filteredDrones = computed(() =>
  reasonFilter.value === 'all' ? DRONES : DRONES.filter(d => d.alertReason === reasonFilter.value)
)
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
function reasonTagType(reason) {
  if (reason === 'low_battery')  return 'warning'
  if (reason === 'device_fault') return 'danger'
  if (reason === 'comm_loss')    return 'info'
  return 'info'
}

// ── 路径规划算法 ──────────────────────────────────────
// 与常规路径规划相同思路：插值生成路径点，计算高度剖面（爬升/巡航/下降）
function buildEmergencyPath(from, to, cruiseAlt = 120) {
  const STEPS = 24
  const ASCENT_R  = 0.15  // 前 15% 爬升
  const DESCENT_R = 0.15  // 后 15% 下降

  // 在起终点之间加一个略偏的中间控制点，避免纯直线
  const dx = to.lng - from.lng
  const dy = to.lat - from.lat
  // 沿垂直方向偏移 25%（自然弧线感）
  const perpLng = -dy * 0.25
  const perpLat =  dx * 0.25
  const midLng = (from.lng + to.lng) / 2 + perpLng
  const midLat = (from.lat + to.lat) / 2 + perpLat

  // 二次贝塞尔插值（P0→P1→P2）
  const pts = []
  for (let i = 0; i < STEPS; i++) {
    const t = i / (STEPS - 1)
    const mt = 1 - t
    const lng = mt * mt * from.lng + 2 * mt * t * midLng + t * t * to.lng
    const lat = mt * mt * from.lat + 2 * mt * t * midLat + t * t * to.lat
    pts.push({ lng: parseFloat(lng.toFixed(6)), lat: parseFloat(lat.toFixed(6)) })
  }

  // 高度剖面（与 sampleRoutes.js buildRoute 同算法）
  const altitude_profile = pts.map((_, i) => {
    const t = i / (STEPS - 1)
    if (t <= ASCENT_R) {
      const a = t / ASCENT_R
      return { index: i, alt: Math.round(20 + (cruiseAlt - 20) * Math.sin(a * Math.PI / 2)), phase: 'ascent' }
    }
    if (t >= 1 - DESCENT_R) {
      const a = (1 - t) / DESCENT_R
      return { index: i, alt: Math.round(20 + (cruiseAlt - 20) * Math.sin(a * Math.PI / 2)), phase: 'descent' }
    }
    return { index: i, alt: cruiseAlt, phase: 'cruise' }
  })

  return { pts, altitude_profile }
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

// ── 渲染充电/维修站（始终可见） ──────────────────────
function renderStations() {
  stationMarkers.forEach(m => { try { map.remove(m) } catch {} })
  stationMarkers = []
  CHARGING_STATIONS.forEach(s => {
    const isSelected = selectedStationId.value === s.id
    const isInRange = alertDrone.value
      ? haversine(alertDrone.value.position, { lat: s.lat, lng: s.lng }) <= estRange.value
      : true
    const bg = isSelected ? '#16a34a' : isInRange ? (s.type === 'repair' ? '#7c3aed' : '#f59e0b') : '#94a3b8'
    const icon = s.type === 'repair' ? '🔧' : '⚡'
    const label = s.type === 'repair' ? '维修站' : '充电站'
    // 选中时显示完整信息（含容量），其余只显示图标+名称，避免标注过宽导致重叠
    const contentHtml = isSelected
      ? `<div style="background:${bg};color:#fff;padding:4px 10px;border-radius:6px;font-size:11px;font-weight:600;box-shadow:0 2px 6px rgba(0,0,0,.25);white-space:nowrap;border:2px solid #fff;text-align:center">
          ${icon} ${s.name}<br><span style="font-size:10px;opacity:.85">${label} · 空位 ${s.available}/${s.capacity}</span>
        </div>`
      : `<div style="background:${bg};color:#fff;padding:3px 7px;border-radius:5px;font-size:11px;font-weight:600;box-shadow:0 1px 4px rgba(0,0,0,.2);white-space:nowrap;border:2px solid #fff">
          ${icon} ${s.name}
        </div>`
    const m = new AMap.Marker({
      position: [s.lng, s.lat],
      content: contentHtml,
      // 充电/维修站标注锚点在标注正下方（向上偏移），与无人机标注（向下偏移）方向相反，避免重叠
      offset: new AMap.Pixel(-50, -(isSelected ? 48 : 30)),
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
    const routeLine = new AMap.Polyline({
      path: d.routeCoords.map(c => [c[0], c[1]]),
      strokeColor: isAlert ? '#475569' : '#94a3b8',
      strokeWeight: isAlert ? 2.5 : 1.5,
      strokeOpacity: isAlert ? 0.75 : 0.4,
    })
    map.add(routeLine)
    droneOverlays.push(routeLine)

    const bg = isAlert ? '#dc2626' : battColor(d.battery)
    const icon = isAlert ? '🚨' : '🚁'
    const cssClass = isAlert ? 'em-alert-marker' : ''
    const m = new AMap.Marker({
      position: [d.position.lng, d.position.lat],
      content: `<div class="${cssClass}" style="background:${bg};color:#fff;padding:4px 10px;border-radius:6px;font-size:12px;font-weight:${isAlert?700:500};box-shadow:0 2px 8px rgba(0,0,0,.3);white-space:nowrap;border:2px solid #fff">
        ${icon} ${d.name} 🔋${d.battery}%
      </div>`,
      // 无人机标注锚点在标注正上方（向下偏移），充电站标注向上偏移，两类标注方向相反，位置接近时不互遮
      offset: new AMap.Pixel(-42, 8),
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
  const circle = new AMap.Circle({
    center: [d.position.lng, d.position.lat],
    radius: estRange.value,
    strokeColor: '#2563eb', strokeWeight: 2,
    strokeOpacity: 0.5, strokeStyle: 'dashed',
    fillColor: '#2563eb', fillOpacity: 0.04,
  })
  map.add(circle)
  alertOverlays.push(circle)

  const safeCircle = new AMap.Circle({
    center: [d.position.lng, d.position.lat],
    radius: estRange.value * 0.75,
    strokeColor: '#16a34a', strokeWeight: 1.5,
    strokeOpacity: 0.35, strokeStyle: 'dashed',
    fillColor: '#16a34a', fillOpacity: 0.03,
  })
  map.add(safeCircle)
  alertOverlays.push(safeCircle)

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

// ── 绘制应急路线（相位着色，与常规路径规划效果一致） ──
function drawEmergencyRoute(pts, altProfile) {
  routeOverlays.forEach(o => { try { map.remove(o) } catch {} })
  routeOverlays = []
  if (!pts?.length || !altProfile?.length) return

  // 找相位切换边界
  const boundaries = [0]
  for (let i = 1; i < altProfile.length; i++) {
    if (altProfile[i].phase !== altProfile[i - 1].phase) boundaries.push(i)
  }
  boundaries.push(altProfile.length - 1)

  // 逐段绘制相位着色折线
  for (let b = 0; b < boundaries.length - 1; b++) {
    const startIdx = boundaries[b]
    const endIdx   = boundaries[b + 1]
    const phase    = altProfile[startIdx].phase
    const color    = PHASE_COLORS[phase] || '#3b82f6'
    const segPts   = pts.slice(startIdx, endIdx + 1).map(p => [p.lng, p.lat])
    if (segPts.length < 2) continue

    const line = new AMap.Polyline({
      path: segPts,
      strokeColor: color,
      strokeWeight: 4,
      strokeOpacity: 0.92,
      lineJoin: 'round', lineCap: 'round',
      zIndex: 100,
    })
    map.add(line)
    routeOverlays.push(line)
  }

  // 方向箭头（半透明叠在路线上）
  const arrowLine = new AMap.Polyline({
    path: pts.map(p => [p.lng, p.lat]),
    strokeColor: '#64748b', strokeWeight: 1,
    strokeOpacity: 0.25, showDir: true, zIndex: 99,
  })
  map.add(arrowLine)
  routeOverlays.push(arrowLine)

  // 起点：在无人机位置正上方加"出发"小气泡，与无人机标记（在右下方）错开不重叠
  const stn = selectedStation.value
  const startM = new AMap.Marker({
    position: [pts[0].lng, pts[0].lat],
    content: `<div style="background:#7f1d1d;color:#fff;padding:3px 8px;border-radius:5px;font-size:11px;font-weight:600;opacity:.92;white-space:nowrap">
      🛫 出发
    </div>`,
    offset: new AMap.Pixel(-22, -52),   // 出发气泡在无人机标记正上方，不与其重叠
    zIndex: 490,
  })
  map.add(startM)
  routeOverlays.push(startM)

  // 终点：在站点标记正下方加"到达"小气泡，与站点标记（在正上方）错开
  const endP = pts[pts.length - 1]
  const endIcon = stn?.type === 'repair' ? '🔧' : '⚡'
  const endM = new AMap.Marker({
    position: [endP.lng, endP.lat],
    content: `<div style="background:#14532d;color:#fff;padding:3px 8px;border-radius:5px;font-size:11px;font-weight:600;opacity:.92;white-space:nowrap">
      ${endIcon} 目标到达
    </div>`,
    offset: new AMap.Pixel(-36, 10),    // 到达气泡在站点标记正下方，不与其重叠
    zIndex: 490,
  })
  map.add(endM)
  routeOverlays.push(endM)

  // 巡航段中间航点（蓝色小圆点）
  pts.forEach((p, i) => {
    if (i === 0 || i === pts.length - 1) return
    if (altProfile[i]?.phase !== 'cruise') return
    if (i % 4 !== 0) return  // 每 4 个点取 1 个，避免过密
    const dot = new AMap.CircleMarker({
      center: [p.lng, p.lat], radius: 4,
      fillColor: '#3b82f6', fillOpacity: 0.85,
      strokeColor: '#fff', strokeWeight: 1.5, zIndex: 110,
    })
    map.add(dot)
    routeOverlays.push(dot)
  })

  // 自适应视图
  setTimeout(() => {
    try { map.setFitView(routeOverlays.filter(o => o instanceof AMap.Polyline), false, [80, 80, 80, 80]) } catch {}
  }, 100)
}

// ── 操作函数 ──────────────────────────────────────────
function triggerAlert(droneId) {
  if (alertDroneId.value === droneId) { resetAll(); return }
  emergencyResult.value = null
  selectedStationId.value = null
  alertDroneId.value = droneId
  const d = DRONES.find(d => d.id === droneId)
  ElMessage({ type: 'warning', message: `${d?.name} 已触发告警：${ALERT_REASON_LABELS[d?.alertReason] || '未知原因'}` })
}

function selectStation(stationId) {
  if (planning.value) return
  selectedStationId.value = stationId
  emergencyResult.value = null
  routeOverlays.forEach(o => { try { map?.remove(o) } catch {} })
  routeOverlays = []
  renderStations()
  planRoute()
}

function cancelRoute() {
  emergencyResult.value = null
  selectedStationId.value = null
  routeOverlays.forEach(o => { try { map?.remove(o) } catch {} })
  routeOverlays = []
  renderStations()
}

async function planRoute() {
  if (!alertDrone.value || !selectedStation.value || planning.value) return
  planning.value = true
  await new Promise(r => setTimeout(r, 600))

  const from = alertDrone.value.position
  const to   = { lng: selectedStation.value.lng, lat: selectedStation.value.lat }
  const dist = selectedStation.value.distance

  // 使用贝塞尔+高度剖面算法（与常规路径规划同思路）
  const { pts, altitude_profile } = buildEmergencyPath(from, to)

  const eta      = +(dist / DRONE_SPEED_MS / 60).toFixed(1)
  const needed   = dist / EST_RANGE_PER_PCT
  const batt     = alertDrone.value.battery
  const assessKey = batt >= needed * 1.3 ? 'safe' : batt >= needed ? 'marginal' : 'insufficient'
  const assessText = {
    safe:         `✅ 电量充足（剩余 ${batt}%，需要约 ${needed.toFixed(0)}%）`,
    marginal:     `⚠️ 电量勉强（剩余 ${batt}%，接近需要量）`,
    insufficient: `❌ 电量不足（剩余 ${batt}%，不足以到达）`,
  }[assessKey]

  emergencyResult.value = {
    stationName: selectedStation.value.name,
    distance: dist,
    eta,
    waypoints: pts.map((p, i) => ({
      lng: p.lng, lat: p.lat,
      alt: altitude_profile[i]?.alt ?? 120,
      phase: altitude_profile[i]?.phase ?? 'cruise',
    })),
    batteryAssess: assessKey,
    batteryAssessText: assessText,
  }

  drawEmergencyRoute(pts, altitude_profile)

  ElMessage({
    type: assessKey === 'insufficient' ? 'warning' : 'success',
    message: `应急路线已生成 → ${selectedStation.value.name}，预计 ${eta} 分钟`,
  })
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
.filter-count { font-size: 10px; color: #6b7280; font-weight: 400; letter-spacing: 0; margin-left: 2px; }
.hint-text { font-size: 10px; color: #9ca3af; font-weight: 400; letter-spacing: 0; }
.empty-filter { text-align: center; font-size: 12px; color: #9ca3af; padding: 14px 0; }

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
.stn-name { font-size: 12px; font-weight: 600; color: #374151; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; display: flex; align-items: center; gap: 4px; }
.stn-type-icon { font-size: 13px; flex-shrink: 0; }
.stn-meta { font-size: 10px; color: #9ca3af; margin-top: 1px; }
.stn-safety { font-size: 11px; white-space: nowrap; flex-shrink: 0; }
.safety-safe     { color: #16a34a; }
.safety-marginal { color: #ca8a04; }
.safety-out      { color: #dc2626; }
.range-note { font-size: 10px; color: #6b7280; text-align: center; padding: 2px 0; }

/* Planning status */
.planning-status {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 12px; background: #fff7ed; border: 1px solid #fed7aa;
  border-radius: 8px; font-size: 12px; color: #c2410c; font-weight: 600;
}
.planning-spinner {
  display: inline-block; width: 14px; height: 14px; flex-shrink: 0;
  border: 2px solid #fed7aa; border-top-color: #ea580c;
  border-radius: 50%; animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.station-item.is-planning {
  border-color: #ea580c; background: #fff7ed;
  animation: planningPulse 1s ease-in-out infinite;
}
@keyframes planningPulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(234, 88, 12, 0.3); }
  50%       { box-shadow: 0 0 0 5px rgba(234, 88, 12, 0); }
}

/* Result box */
.result-box { background: #f0fdf4; border-radius: 8px; padding: 10px; border: 1px solid #bbf7d0; }
.result-title { font-size: 13px; font-weight: 700; color: #16a34a; margin-bottom: 8px; }
.result-rows { display: flex; flex-direction: column; gap: 4px; margin-bottom: 8px; }
.result-row { display: flex; justify-content: space-between; font-size: 12px; color: #374151; }
.result-row strong { color: #111827; }
.phase-legend-row { display: flex; gap: 6px; margin-bottom: 8px; flex-wrap: wrap; }
.phase-pill {
  font-size: 10px; padding: 2px 8px; border-radius: 10px;
  border: 1px solid; font-weight: 600;
}
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
.leg-title { font-size: 10px; font-weight: 700; color: #6b7280; text-transform: uppercase; letter-spacing: .5px; margin-bottom: 6px; }
.leg-item { display: flex; align-items: center; gap: 7px; margin-bottom: 5px; color: #6b7280; }
.leg-item:last-child { margin-bottom: 0; }
.leg-icon { font-size: 14px; }
.leg-line { display: inline-block; width: 28px; height: 3px; border-radius: 2px; flex-shrink: 0; }
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
