<!--
  安全缓冲区分析 — 统一页面（安全范围配置 + 缓冲区重叠分析）
  多条交叉航线，时间轴驱动无人机移动，实时检测缓冲区重叠
  2D/3D 双模式，安全范围配置与每架无人机联动
-->
<template>
  <div class="sba-page">
    <!-- 左侧面板 -->
    <aside class="sba-panel">
      <div class="panel-header">
        <span class="panel-icon">🛡️</span>
        <h2>安全缓冲区分析</h2>
        <el-tag size="small" :type="running ? 'success' : 'info'">{{ running ? '仿真中' : '已暂停' }}</el-tag>
      </div>

      <!-- 安全范围配置 -->
      <div class="section">
        <h3 class="section-title">安全范围配置</h3>
        <div class="param-row">
          <span>水平缓冲</span>
          <el-slider v-model="config.horizontalBuffer" :min="30" :max="500" :step="10"
            show-input input-size="small" style="flex:1" @change="onConfigChange" />
          <span class="unit">m</span>
        </div>
        <div class="param-row">
          <span>警戒距离</span>
          <el-slider v-model="config.warnDistance" :min="50" :max="800" :step="10"
            show-input input-size="small" style="flex:1" @change="onConfigChange" />
          <span class="unit">m</span>
        </div>
        <div class="param-row">
          <span>垂直间隔</span>
          <el-slider v-model="config.verticalBuffer" :min="10" :max="150" :step="5"
            show-input input-size="small" style="flex:1" @change="onConfigChange" />
          <span class="unit">m</span>
        </div>
        <div class="config-actions">
          <el-button size="small" type="primary" @click="applyConfig">应用配置</el-button>
          <el-button size="small" @click="resetConfig">恢复默认</el-button>
        </div>
      </div>

      <!-- 时间轴 -->
      <div class="section">
        <h3 class="section-title">时间轴控制 <span class="time-display">{{ formatTime(simTime) }}</span></h3>
        <div class="period-select-row">
          <span class="period-label">时段</span>
          <el-select v-model="selectedPeriod" size="small" style="flex:1" @change="onPeriodChange">
            <el-option v-for="p in timePeriods" :key="p.value" :label="p.label" :value="p.value" />
          </el-select>
        </div>
        <div class="timeline-row">
          <el-slider v-model="simTime" :min="0" :max="simDuration" :step="0.5"
            style="flex:1" @change="onTimeScrub" />
        </div>
        <div class="timeline-ticks">
          <span v-for="t in tickMarks" :key="t" class="tick">{{ formatTime(t) }}</span>
        </div>
        <div class="ctrl-row">
          <el-button size="small" :type="running ? 'warning' : 'primary'" @click="toggleSim">
            {{ running ? '⏸ 暂停' : '▶ 开始' }}
          </el-button>
          <el-button size="small" @click="resetSim">↺ 重置</el-button>
          <span class="speed-label">速度</span>
          <el-slider v-model="simSpeed" :min="0.5" :max="8" :step="0.5" show-input input-size="small" style="width:100px" />
          <span class="unit">×</span>
        </div>
      </div>

      <!-- 无人机状态 -->
      <div class="section">
        <h3 class="section-title">无人机状态 <span class="drone-count">{{ drones.length }} 架</span></h3>
        <div v-for="d in drones" :key="d.id" class="drone-item">
          <div class="drone-header">
            <span class="drone-dot" :style="{ background: d.color }"></span>
            <span class="drone-name">{{ d.name }}</span>
            <el-tag size="small" :type="d.status === 'conflict' ? 'danger' : d.status === 'warning' ? 'warning' : 'success'">
              {{ statusLabel[d.status] || '正常' }}
            </el-tag>
          </div>
          <div class="drone-info-row">
            <el-tag size="small" :type="d.type === '应急' ? 'danger' : d.type === '巡检' ? 'warning' : ''" style="font-size:9px;padding:0 4px;height:18px">{{ d.type }}</el-tag>
            <span class="drone-route">{{ d.routeName }}</span>
            <span class="drone-pos">{{ (d.progress * 100).toFixed(0) }}%</span>
            <span class="drone-alt">H{{ Math.round(d.altitude) }}m</span>
          </div>
        </div>
        <div v-if="conflictCount > 0" class="conflict-warn">
          ⚠️ {{ conflictCount }} 处缓冲区重叠，请查看事件日志
        </div>
      </div>

      <!-- 防撞事件日志 -->
      <div class="section log-section">
        <h3 class="section-title">防撞事件日志</h3>
        <div class="event-log" ref="logRef">
          <div v-for="(e, i) in eventLog" :key="i" class="event-item" :class="e.type">
            <span class="event-time">{{ e.time }}</span>
            <div class="event-body">
              <span class="event-msg">{{ e.msg }}</span>
              <span v-if="e.solution" class="event-solution">💡 {{ e.solution }}</span>
            </div>
          </div>
          <div v-if="eventLog.length === 0" class="empty-log">暂无事件 — 启动仿真以监测缓冲区重叠</div>
        </div>
      </div>
    </aside>

    <!-- 右侧地图区域 -->
    <div class="right-section">
      <!-- 2D/3D 切换栏 -->
      <div class="view-mode-bar">
        <div class="mode-btns">
          <button class="mode-btn" :class="{ active: viewMode === '2D' }" @click="switchMode('2D')">
            🗺 2D 平面
          </button>
          <button class="mode-btn" :class="{ active: viewMode === '3D' }" @click="switchMode('3D')">
            🌐 3D 缓冲球
          </button>
        </div>
        <span class="mode-tip" v-if="viewMode === '3D'">可拖拽旋转视角 · 红色球体 = 缓冲区重叠 · 垂直间隔 = 球体Z轴</span>
        <span class="mode-tip" v-else>彩色圆圈 = 安全缓冲圆 · 虚线 = 航线走廊</span>
        <div class="conflict-badge" v-if="conflictCount > 0">
          🔴 {{ conflictCount }} 处冲突
        </div>
      </div>

      <!-- 地图区 -->
      <div class="map-area">
        <div v-show="viewMode === '2D'" ref="mapRef" class="map-container"></div>
        <div v-show="viewMode === '3D'" ref="cesiumRef" class="map-container"></div>

        <!-- 图例 -->
        <div class="map-legend">
          <div class="legend-title">{{ viewMode === '3D' ? '3D 缓冲球' : '2D 缓冲圆' }}图例</div>
          <div class="legend-item">
            <span class="legend-swatch" style="background:#3b82f6;opacity:.45"></span>
            安全区（{{ config.horizontalBuffer }}m）
          </div>
          <div class="legend-item">
            <span class="legend-swatch" style="background:#f59e0b;opacity:.35"></span>
            警戒区（{{ config.warnDistance }}m）
          </div>
          <div class="legend-item">
            <span class="legend-swatch" style="background:#dc2626;opacity:.5"></span>
            冲突（球体相交）
          </div>
          <div class="legend-divider"></div>
          <div class="legend-item">
            <span class="legend-swatch" style="background:transparent;border:1px dashed #94a3b8"></span>
            航线走廊
          </div>
          <div class="legend-item" v-for="r in ROUTES" :key="r.id">
            <span class="legend-swatch" :style="{ background: r.color }"></span>
            {{ r.name }}
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

// ═══════════════════════════════════════════════════════════
// Cesium 动态加载
// ═══════════════════════════════════════════════════════════
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

// ═══════════════════════════════════════════════════════════
// 交叉航线定义（4条航线穿过广州核心区域，多处交叉）
// ═══════════════════════════════════════════════════════════
const ROUTES = [
  {
    id: 'route-a', name: '番禺→天河纵向线', color: '#3b82f6',
    pts: [[113.3100, 23.0700], [113.3120, 23.0850], [113.3160, 23.1000], [113.3200, 23.1150], [113.3245, 23.1300]],
  },
  {
    id: 'route-b', name: '白云→海珠斜穿线', color: '#8b5cf6',
    pts: [[113.2900, 23.1550], [113.3000, 23.1350], [113.3120, 23.1180], [113.3220, 23.1020], [113.3300, 23.0880]],
  },
  {
    id: 'route-c', name: '荔湾→黄埔横向线', color: '#10b981',
    pts: [[113.2550, 23.1120], [113.2750, 23.1140], [113.3000, 23.1160], [113.3220, 23.1180], [113.3450, 23.1200]],
  },
  {
    id: 'route-d', name: '越秀→番禺斜穿线', color: '#f59e0b',
    pts: [[113.2800, 23.1400], [113.2900, 23.1250], [113.3050, 23.1080], [113.3180, 23.0920], [113.3300, 23.0780]],
  },
]

// ═══════════════════════════════════════════════════════════
// 工具函数
// ═══════════════════════════════════════════════════════════
function latLngDistM(a, b) {
  const M_PER_LNG = Math.cos((a[1] + b[1]) / 2 * Math.PI / 180) * 111320
  return Math.sqrt(((b[0] - a[0]) * M_PER_LNG) ** 2 + ((b[1] - a[1]) * 111320) ** 2)
}

function dist3D(a, b) {
  const M_PER_LNG = Math.cos(a.lat * Math.PI / 180) * 111320
  const dx = (b.lng - a.lng) * M_PER_LNG
  const dy = (b.lat - a.lat) * 111320
  const dz = (b.alt || 0) - (a.alt || 0)
  return Math.sqrt(dx * dx + dy * dy + dz * dz)
}

// 预计算每条航线的累计距离
const routeMeta = ROUTES.map(r => {
  const cumDist = [0]
  for (let i = 1; i < r.pts.length; i++) {
    cumDist.push(cumDist[i - 1] + latLngDistM(r.pts[i - 1], r.pts[i]))
  }
  return { ...r, cumDist, totalLen: cumDist[cumDist.length - 1] }
})

// 在航线上按进度 [0,1] 插值位置 + 高度
function posOnRoute(routeIdx, t) {
  const r = routeMeta[routeIdx]
  const target = t * r.totalLen
  let seg = 0
  for (let i = 0; i < r.cumDist.length - 1; i++) {
    if (target <= r.cumDist[i + 1]) { seg = i; break }
    seg = i
  }
  const segLen = r.cumDist[seg + 1] - r.cumDist[seg] || 1
  const local = (target - r.cumDist[seg]) / segLen
  const a = r.pts[seg], b = r.pts[Math.min(seg + 1, r.pts.length - 1)]
  const lng = a[0] + (b[0] - a[0]) * local
  const lat = a[1] + (b[1] - a[1]) * local
  // 高度：起飞/降落段 + 巡航段
  let alt
  if (t < 0.10) alt = 30 + (120 - 30) * (t / 0.10)
  else if (t > 0.90) alt = 30 + (120 - 30) * ((1 - t) / 0.10)
  else alt = 120
  return { lng, lat, alt }
}

// ═══════════════════════════════════════════════════════════
// 各时段无人机编队（不同时段：不同机型、不同位置、不同数量）
// ═══════════════════════════════════════════════════════════
const PERIOD_DRONES = {
  // 早高峰 — 物流干线密集，8架无人机，集中在南北向航线
  morning: [
    { id: 1, name: 'WL-A01', type: '物流', routeIdx: 0, startProgress: 0.05, speed: 2800, color: '#3b82f6' },
    { id: 2, name: 'WL-A02', type: '物流', routeIdx: 0, startProgress: 0.28, speed: 2600, color: '#60a5fa' },
    { id: 3, name: 'WL-B01', type: '物流', routeIdx: 1, startProgress: 0.10, speed: 2700, color: '#8b5cf6' },
    { id: 4, name: 'WL-B02', type: '物流', routeIdx: 1, startProgress: 0.45, speed: 2500, color: '#a78bfa' },
    { id: 5, name: 'XJ-C01', type: '巡检', routeIdx: 2, startProgress: 0.02, speed: 3000, color: '#10b981' },
    { id: 6, name: 'XJ-C02', type: '巡检', routeIdx: 2, startProgress: 0.38, speed: 2800, color: '#34d399' },
    { id: 7, name: 'WL-D01', type: '物流', routeIdx: 3, startProgress: 0.15, speed: 2600, color: '#f59e0b' },
    { id: 8, name: 'WL-D02', type: '物流', routeIdx: 3, startProgress: 0.52, speed: 2400, color: '#fbbf24' },
  ],
  // 午间 — 低峰时段，4架（以巡检+应急为主）
  noon: [
    { id: 1, name: 'XJ-A01', type: '巡检', routeIdx: 0, startProgress: 0.22, speed: 2200, color: '#3b82f6' },
    { id: 2, name: 'YJ-B01', type: '应急', routeIdx: 1, startProgress: 0.38, speed: 3000, color: '#ef4444' },
    { id: 3, name: 'XJ-C01', type: '巡检', routeIdx: 2, startProgress: 0.08, speed: 2100, color: '#10b981' },
    { id: 4, name: 'WL-D01', type: '物流', routeIdx: 3, startProgress: 0.55, speed: 2300, color: '#f59e0b' },
  ],
  // 下午 — 物流恢复，6架，东西向航线增多
  afternoon: [
    { id: 1, name: 'WL-A01', type: '物流', routeIdx: 0, startProgress: 0.00, speed: 2700, color: '#3b82f6' },
    { id: 2, name: 'XJ-A02', type: '巡检', routeIdx: 0, startProgress: 0.42, speed: 2400, color: '#60a5fa' },
    { id: 3, name: 'WL-B01', type: '物流', routeIdx: 1, startProgress: 0.12, speed: 2600, color: '#8b5cf6' },
    { id: 4, name: 'WL-C01', type: '物流', routeIdx: 2, startProgress: 0.05, speed: 2800, color: '#10b981' },
    { id: 5, name: 'WL-C02', type: '物流', routeIdx: 2, startProgress: 0.55, speed: 2500, color: '#34d399' },
    { id: 6, name: 'XJ-D01', type: '巡检', routeIdx: 3, startProgress: 0.18, speed: 2300, color: '#f59e0b' },
  ],
  // 晚高峰 — 返程高峰，8架，东西向+南北向全开
  evening: [
    { id: 1, name: 'WL-A01', type: '物流', routeIdx: 0, startProgress: 0.50, speed: 2900, color: '#3b82f6' },
    { id: 2, name: 'WL-A02', type: '物流', routeIdx: 0, startProgress: 0.75, speed: 2700, color: '#60a5fa' },
    { id: 3, name: 'WL-B01', type: '物流', routeIdx: 1, startProgress: 0.60, speed: 2800, color: '#8b5cf6' },
    { id: 4, name: 'WL-B02', type: '物流', routeIdx: 1, startProgress: 0.85, speed: 2600, color: '#a78bfa' },
    { id: 5, name: 'YJ-C01', type: '应急', routeIdx: 2, startProgress: 0.30, speed: 3200, color: '#ef4444' },
    { id: 6, name: 'WL-C02', type: '物流', routeIdx: 2, startProgress: 0.65, speed: 2600, color: '#10b981' },
    { id: 7, name: 'WL-D01', type: '物流', routeIdx: 3, startProgress: 0.48, speed: 2700, color: '#f59e0b' },
    { id: 8, name: 'XJ-D02', type: '巡检', routeIdx: 3, startProgress: 0.82, speed: 2300, color: '#fbbf24' },
  ],
}

// ═══════════════════════════════════════════════════════════
// 时段配置
// ═══════════════════════════════════════════════════════════
const timePeriods = [
  { value: 'morning',   label: '早高峰（08:00-10:00）', baseHour: 8,  simMins: 120 },
  { value: 'noon',      label: '午间（11:00-13:00）',   baseHour: 11, simMins: 120 },
  { value: 'afternoon', label: '下午（14:00-17:00）',   baseHour: 14, simMins: 180 },
  { value: 'evening',   label: '晚高峰（17:00-20:00）', baseHour: 17, simMins: 180 },
]
const selectedPeriod = ref('morning')
const simDuration = ref(timePeriods[0].simMins)

// ═══════════════════════════════════════════════════════════
// 响应式状态
// ═══════════════════════════════════════════════════════════
const config = reactive({
  horizontalBuffer: 150,
  warnDistance: 350,
  verticalBuffer: 40,
})

const simTime = ref(0)        // 当前仿真时间（分钟）
const simSpeed = ref(2)       // 仿真速度倍率
const running = ref(false)
const viewMode = ref('2D')
const eventLog = ref([])
const logRef = ref(null)
const mapRef = ref(null)
const cesiumRef = ref(null)

const tickMarks = computed(() => {
  const d = simDuration.value
  const step = d <= 180 ? d / 4 : d / 6
  const marks = []
  for (let i = 0; i <= (d <= 180 ? 4 : 6); i++) marks.push(Math.round(i * step))
  return marks
})

const statusLabel = { normal: '正常', warning: '警戒', conflict: '⚠ 冲突' }

// 无人机实时状态（按当前时段初始化）
const drones = reactive([])

function rebuildDroneList() {
  drones.length = 0
  const defs = PERIOD_DRONES[selectedPeriod.value] || PERIOD_DRONES.morning
  defs.forEach(d => {
    const pos = posOnRoute(d.routeIdx, d.startProgress)
    drones.push({
      ...d,
      progress: d.startProgress,
      lng: pos.lng, lat: pos.lat, altitude: pos.alt,
      status: 'normal',
      routeName: ROUTES[d.routeIdx].name,
      bufferR: config.horizontalBuffer,
    })
  })
}
rebuildDroneList()

// ═══════════════════════════════════════════════════════════
// 冲突检测
// ═══════════════════════════════════════════════════════════
const conflictCount = computed(() => drones.filter(d => d.status === 'conflict').length)

function detectConflicts() {
  // 更新所有无人机位置
  drones.forEach(d => {
    const pos = posOnRoute(d.routeIdx, d.progress)
    d.lng = pos.lng; d.lat = pos.lat; d.altitude = pos.alt
    d.bufferR = config.horizontalBuffer
  })

  // 先全部重置为 normal，再由后续检测升级为 warning/conflict
  drones.forEach(d => { d.status = 'normal' })

  // 两两检测
  const conflicts = []
  for (let i = 0; i < drones.length; i++) {
    for (let j = i + 1; j < drones.length; j++) {
      const a = drones[i], b = drones[j]
      const d3 = dist3D(a, b)
      const hDist = Math.sqrt(
        ((b.lng - a.lng) * Math.cos(a.lat * Math.PI / 180) * 111320) ** 2 +
        ((b.lat - a.lat) * 111320) ** 2
      )
      const vDist = Math.abs(b.altitude - a.altitude)
      const r = config.horizontalBuffer

      if (d3 < r * 2) {
        const prevA = a.status, prevB = b.status
        a.status = 'conflict'; b.status = 'conflict'

        // 同一航线上的前后机 → 追越冲突
        const sameRoute = a.routeIdx === b.routeIdx
        // 不同航线交叉 → 交叉冲突
        const crossRoute = !sameRoute

        if (prevA !== 'conflict' || prevB !== 'conflict') {
          let solution = ''
          if (vDist < config.verticalBuffer) {
            // 垂直方向也重叠 → 严重冲突
            const altA = Math.max(a.altitude, b.altitude) + config.verticalBuffer + 10
            solution = `严重交叉冲突！建议${a.name}爬升至${Math.round(altA)}m以上，${b.name}保持${Math.round(b.altitude)}m，垂直错开≥${config.verticalBuffer}m`
          } else if (crossRoute) {
            // 交叉航线 → 建议时间错开
            const behind = a.progress < b.progress ? a : b
            const ahead = a.progress < b.progress ? b : a
            const waitSec = Math.round(r * 2 / (behind.speed / 3600))
            solution = `交叉航线冲突（水平距${Math.round(hDist)}m）。建议${behind.name}减速等待约${waitSec}s，让${ahead.name}先行通过交叉点`
          } else {
            // 同航线 → 保持间距
            const behind = a.progress < b.progress ? a : b
            solution = `同航线追越冲突。建议${behind.name}减速至50%速度，保持≥${r * 2}m安全间距`
          }
          conflicts.push({ drones: [a.name, b.name], hDist, vDist, solution, sameRoute, crossRoute })
        }
      } else if (d3 < r * 3) {
        // 警戒区（只在还不是 conflict 时设为 warning）
        if (a.status !== 'conflict') a.status = 'warning'
        if (b.status !== 'conflict') b.status = 'warning'
      }
      // else: 已在开头重置为 normal，无需再处理
    }
  }
  return conflicts
}

// ═══════════════════════════════════════════════════════════
// 事件日志
// ═══════════════════════════════════════════════════════════
function addLog(type, msg, solution = '') {
  const period = timePeriods.find(p => p.value === selectedPeriod.value)
  const baseHour = period?.baseHour || 8
  const totalMins = baseHour * 60 + simTime.value
  const h = Math.floor(totalMins / 60) % 24
  const m = Math.floor(totalMins % 60)
  const time = `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`
  eventLog.value.unshift({ type, time, msg, solution })
  if (eventLog.value.length > 80) eventLog.value.pop()
}

function formatTime(mins) {
  const period = timePeriods.find(p => p.value === selectedPeriod.value)
  const baseHour = period?.baseHour || 8
  const totalMins = baseHour * 60 + mins
  const h = Math.floor(totalMins / 60) % 24
  const m = Math.floor(totalMins % 60)
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`
}

// ═══════════════════════════════════════════════════════════
// 仿真循环
// ═══════════════════════════════════════════════════════════
let simTimer = null
let lastTs = 0

function tick(ts) {
  if (!running.value) return
  if (lastTs === 0) lastTs = ts
  const realDt = Math.min((ts - lastTs) / 1000, 0.1)
  lastTs = ts

  // 推进仿真时间
  const simDt = realDt * simSpeed.value * 60 // 换算为仿真秒
  simTime.value += simDt / 60 // 转为分钟
  if (simTime.value >= simDuration.value) {
    simTime.value = simDuration.value
    pauseSim()
    addLog('info', '仿真周期结束，所有无人机已完成巡检')
    detectConflicts()
    updateView()
    return
  }

  // 推进每架无人机
  drones.forEach(d => {
    const rMeta = routeMeta[d.routeIdx]
    const distPerSec = d.speed / 3600 // m/s
    const progressDelta = (distPerSec * simDt) / rMeta.totalLen
    d.progress += progressDelta
    if (d.progress >= 1.0) d.progress -= 1.0 // 循环
    if (d.progress < 0) d.progress += 1.0
  })

  // 冲突检测
  const newConflicts = detectConflicts()
  newConflicts.forEach(c => {
    addLog('danger',
      `⚠️ ${c.drones[0]} 与 ${c.drones[1]} 缓冲区重叠（水平距${Math.round(c.hDist)}m，垂直距${Math.round(c.vDist)}m）`,
      c.solution
    )
  })

  updateView()
  simTimer = requestAnimationFrame(tick)
}

function pauseSim() {
  running.value = false
  if (simTimer) { cancelAnimationFrame(simTimer); simTimer = null }
}

function toggleSim() {
  if (running.value) {
    pauseSim()
    addLog('info', '仿真暂停')
  } else {
    if (simTime.value >= simDuration.value) simTime.value = 0
    running.value = true
    lastTs = 0
    simTimer = requestAnimationFrame(tick)
    addLog('info', '仿真启动 — 监测交叉航线缓冲区重叠')
  }
}

function resetSim() {
  pauseSim()
  simTime.value = 0
  eventLog.value = []
  // 重建无人机列表（重置所有进度）
  rebuildDroneList()
  detectConflicts()
  updateView()
  addLog('info', '仿真已重置 — 时间归零')
}

function onTimeScrub() {
  // 用户拖动时间轴时，按比例推进所有无人机
  drones.forEach(d => {
    const rMeta = routeMeta[d.routeIdx]
    const elapsedMins = simTime.value
    const distTraveled = (d.speed / 60) * elapsedMins
    d.progress = (d.startProgress + distTraveled / rMeta.totalLen) % 1.0
    const pos = posOnRoute(d.routeIdx, d.progress)
    d.lng = pos.lng; d.lat = pos.lat; d.altitude = pos.alt
  })
  detectConflicts()
  updateView()
}

// 时段切换
function onPeriodChange() {
  const period = timePeriods.find(p => p.value === selectedPeriod.value)
  if (!period) return
  pauseSim()
  simTime.value = 0
  simDuration.value = period.simMins
  eventLog.value = []
  rebuildDroneList()
  detectConflicts()
  updateView()
  if (viewMode.value === '3D' && cesium3DReady) buildCesiumEntities()
  addLog('info', `切换至「${period.label}」时段，${drones.length}架无人机在线`)
}

// ═══════════════════════════════════════════════════════════
// 视图更新分发
// ═══════════════════════════════════════════════════════════
function updateView() {
  if (viewMode.value === '2D') updateAMap2D()
  else updateCesium3D()
}

// ═══════════════════════════════════════════════════════════
// 2D AMap
// ═══════════════════════════════════════════════════════════
let AMap = null, map = null
let routeLines2D = []
let droneMarkers2D = {}
let bufferCircles2D = {}
let warnCircles2D = {}

async function initAMap() {
  if (!mapRef.value || map) return
  window._AMapSecurityConfig = { securityJsCode: import.meta.env.VITE_AMAP_SECURITY_CODE }
  try {
    if (!AMap) AMap = await AMapLoader.load({ key: import.meta.env.VITE_AMAP_KEY, version: '2.0', plugins: ['AMap.Scale'] })
    map = new AMap.Map(mapRef.value, {
      viewMode: '2D', zoom: 12,
      center: [113.3100, 23.1150],
      mapStyle: 'amap://styles/whitesmoke',
    })
    map.addControl(new AMap.Scale({ position: 'LB' }))
    drawRouteLines()
    updateAMap2D()
  } catch (e) { console.error('AMap init failed:', e) }
}

function drawRouteLines() {
  if (!map || !AMap) return
  ROUTES.forEach(r => {
    const line = new AMap.Polyline({
      path: r.pts.map(([lng, lat]) => [lng, lat]),
      strokeColor: r.color, strokeWeight: 2.5, strokeOpacity: 0.5,
      strokeStyle: 'dashed', strokeDasharray: [8, 6],
      lineJoin: 'round', lineCap: 'round', zIndex: 5,
    })
    map.add(line)
    routeLines2D.push(line)
    // 起终点标注
    ;[r.pts[0], r.pts[r.pts.length - 1]].forEach(([lng, lat]) => {
      const dot = new AMap.CircleMarker({
        center: [lng, lat], radius: 4,
        strokeColor: r.color, strokeWeight: 1.5,
        fillColor: r.color, fillOpacity: 0.8, zIndex: 15,
      })
      map.add(dot)
      routeLines2D.push(dot)
    })
  })
}

function updateAMap2D() {
  if (!map || !AMap) return

  drones.forEach(d => {
    const center = new AMap.LngLat(d.lng, d.lat)
    const isConflict = d.status === 'conflict'
    const isWarning = d.status === 'warning'
    const bufColor = isConflict ? '#dc2626' : isWarning ? '#f59e0b' : d.color
    const bufOpacity = isConflict ? 0.28 : isWarning ? 0.18 : 0.10

    // 警戒圆
    if (!warnCircles2D[d.id]) {
      warnCircles2D[d.id] = new AMap.Circle({
        center, radius: config.warnDistance,
        strokeColor: '#f59e0b', strokeWeight: 1, strokeOpacity: 0.4,
        fillColor: '#f59e0b', fillOpacity: 0.04,
      })
      map.add(warnCircles2D[d.id])
    } else {
      warnCircles2D[d.id].setCenter(center)
      warnCircles2D[d.id].setRadius(config.warnDistance)
    }

    // 安全缓冲圆
    if (!bufferCircles2D[d.id]) {
      bufferCircles2D[d.id] = new AMap.Circle({
        center, radius: config.horizontalBuffer,
        strokeColor: bufColor, strokeWeight: 2, strokeOpacity: 0.85,
        fillColor: bufColor, fillOpacity: bufOpacity,
      })
      map.add(bufferCircles2D[d.id])
    } else {
      bufferCircles2D[d.id].setCenter(center)
      bufferCircles2D[d.id].setRadius(config.horizontalBuffer)
      bufferCircles2D[d.id].setOptions({
        strokeColor: bufColor, fillColor: bufColor, fillOpacity: bufOpacity,
      })
    }

    // 无人机标签
    const icon = isConflict ? '⚠️' : isWarning ? '🔶' : '🚁'
    const label = `${icon} ${d.name}`
    if (!droneMarkers2D[d.id]) {
      droneMarkers2D[d.id] = new AMap.Marker({
        position: center,
        content: `<div class="sba-drone-tag" style="background:${bufColor}">${label}</div>`,
        offset: new AMap.Pixel(-30, -12),
      })
      map.add(droneMarkers2D[d.id])
    } else {
      droneMarkers2D[d.id].setPosition(center)
      droneMarkers2D[d.id].setContent(`<div class="sba-drone-tag" style="background:${bufColor}">${label}</div>`)
    }
  })
}

function destroyAMap() {
  Object.values(droneMarkers2D).forEach(m => { try { map?.remove(m) } catch {} })
  Object.values(bufferCircles2D).forEach(c => { try { map?.remove(c) } catch {} })
  Object.values(warnCircles2D).forEach(c => { try { map?.remove(c) } catch {} })
  routeLines2D.forEach(o => { try { map?.remove(o) } catch {} })
  droneMarkers2D = {}; bufferCircles2D = {}; warnCircles2D = {}; routeLines2D = []
  map?.destroy(); map = null
}

// ═══════════════════════════════════════════════════════════
// 3D Cesium
// ═══════════════════════════════════════════════════════════
let cesiumViewer = null
let cesium3DReady = false
const cesiumDronePositions = {} // Cesium ConstantPositionProperty per drone

function makeDroneCanvas(color, size = 32) {
  const cv = document.createElement('canvas'); cv.width = size; cv.height = size
  const ctx = cv.getContext('2d')
  const c = size / 2
  ctx.strokeStyle = '#fff'; ctx.lineWidth = 2
  ctx.beginPath(); ctx.moveTo(c, c - c * 0.6); ctx.lineTo(c, c + c * 0.6); ctx.stroke()
  ctx.beginPath(); ctx.moveTo(c - c * 0.6, c); ctx.lineTo(c + c * 0.6, c); ctx.stroke()
  ;[[-1, -1], [1, -1], [-1, 1], [1, 1]].forEach(([sx, sy]) => {
    ctx.beginPath(); ctx.arc(c + sx * c * 0.6, c + sy * c * 0.6, c * 0.18, 0, Math.PI * 2)
    ctx.fillStyle = color; ctx.fill()
    ctx.strokeStyle = '#fff'; ctx.lineWidth = 1; ctx.stroke()
  })
  ctx.beginPath(); ctx.arc(c, c, c * 0.14, 0, Math.PI * 2)
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
    destination: Cesium.Cartesian3.fromDegrees(113.3080, 23.1150, 3500),
    orientation: { heading: Cesium.Math.toRadians(-15), pitch: Cesium.Math.toRadians(-45), roll: 0 },
  })
  cesium3DReady = true
  buildCesiumEntities()
}

function buildCesiumEntities() {
  if (!cesiumViewer || !cesium3DReady) return
  cesiumViewer.entities.removeAll()
  Object.keys(cesiumDronePositions).forEach(k => delete cesiumDronePositions[k])

  // 绘制航线（虚线）
  ROUTES.forEach(r => {
    const positions = r.pts.flatMap(([lng, lat]) => {
      const t = r.pts.findIndex(p => p[0] === lng && p[1] === lat) / (r.pts.length - 1)
      const alt = t < 0.1 ? 30 + 90 * t / 0.1 : t > 0.9 ? 30 + 90 * (1 - t) / 0.1 : 120
      return [lng, lat, alt]
    })
    cesiumViewer.entities.add({
      polyline: {
        positions: Cesium.Cartesian3.fromDegreesArrayHeights(positions),
        width: 2,
        material: new Cesium.PolylineDashMaterialProperty({
          color: Cesium.Color.fromCssColorString(r.color).withAlpha(0.5),
          dashLength: 16,
        }),
        clampToGround: false,
      },
    })
  })

  // 为每架无人机创建实体
  drones.forEach(d => {
    const initPos = Cesium.Cartesian3.fromDegrees(d.lng, d.lat, d.altitude)
    const posProp = new Cesium.ConstantPositionProperty(initPos)
    cesiumDronePositions[d.id] = posProp

    // 警戒外球（线框）
    cesiumViewer.entities.add({
      position: posProp,
      ellipsoid: {
        radii: new Cesium.CallbackProperty(() => {
          const w = config.warnDistance
          const v = config.verticalBuffer * 1.4  // 垂直警戒范围按比例放大
          return new Cesium.Cartesian3(w, w, v)
        }, false),
        material: Cesium.Color.fromCssColorString('#f59e0b').withAlpha(0.03),
        outline: true,
        outlineColor: Cesium.Color.fromCssColorString('#f59e0b').withAlpha(0.25),
        slicePartitions: 12, stackPartitions: 12,
      },
    })

    // 安全缓冲球（垂直间隔 = 球体Z轴半径）
    cesiumViewer.entities.add({
      position: posProp,
      ellipsoid: {
        radii: new Cesium.CallbackProperty(() => {
          const h = config.horizontalBuffer
          const v = config.verticalBuffer  // ← 垂直安全距离直接控制 Z 轴
          return new Cesium.Cartesian3(h, h, v)
        }, false),
        material: new Cesium.ColorMaterialProperty(
          new Cesium.CallbackProperty(() => {
            const isC = d.status === 'conflict'
            const isW = d.status === 'warning'
            const col = isC ? '#dc2626' : isW ? '#f59e0b' : d.color
            return Cesium.Color.fromCssColorString(col).withAlpha(isC ? 0.40 : isW ? 0.25 : 0.18)
          }, false)
        ),
        outline: true,
        outlineColor: new Cesium.CallbackProperty(() => {
          const isC = d.status === 'conflict'
          const isW = d.status === 'warning'
          const col = isC ? '#dc2626' : isW ? '#f59e0b' : d.color
          return Cesium.Color.fromCssColorString(col).withAlpha(isC ? 0.90 : isW ? 0.70 : 0.55)
        }, false),
        slicePartitions: 24, stackPartitions: 24,
      },
    })

    // 到地面的竖向指示线
    cesiumViewer.entities.add({
      polyline: {
        positions: new Cesium.CallbackProperty(() => {
          const p = posProp.getValue(cesiumViewer.clock.currentTime)
          if (!p) return []
          const cart = Cesium.Cartographic.fromCartesian(p)
          return [Cesium.Cartesian3.fromDegrees(
            Cesium.Math.toDegrees(cart.longitude),
            Cesium.Math.toDegrees(cart.latitude), 0
          ), p]
        }, false),
        width: 1,
        material: new Cesium.ColorMaterialProperty(
          new Cesium.CallbackProperty(() => {
            return (d.status === 'conflict'
              ? Cesium.Color.fromCssColorString('#dc2626')
              : Cesium.Color.fromCssColorString(d.color)).withAlpha(0.3)
          }, false)
        ),
      },
    })

    // 无人机 billboard
    cesiumViewer.entities.add({
      position: posProp,
      billboard: {
        image: makeDroneCanvas(d.color),
        width: 32, height: 32,
        verticalOrigin: Cesium.VerticalOrigin.CENTER,
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
      },
      label: {
        text: new Cesium.CallbackProperty(() => {
          const icon = d.status === 'conflict' ? '⚠' : d.status === 'warning' ? '◆' : '▶'
          return `${d.name}\n${icon} H${Math.round(d.altitude)}m`
        }, false),
        font: '10px sans-serif',
        fillColor: Cesium.Color.WHITE,
        showBackground: true,
        backgroundColor: new Cesium.CallbackProperty(() => {
          const col = d.status === 'conflict' ? '#dc2626' : d.status === 'warning' ? '#f59e0b' : d.color
          return Cesium.Color.fromCssColorString(col).withAlpha(0.88)
        }, false),
        backgroundPadding: new Cesium.Cartesian2(4, 3),
        pixelOffset: new Cesium.Cartesian2(0, -44),
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
      },
    })

    // 冲突时的红色告警环
    cesiumViewer.entities.add({
      position: posProp,
      ellipse: {
        semiMajorAxis: new Cesium.CallbackProperty(() => config.horizontalBuffer, false),
        semiMinorAxis: new Cesium.CallbackProperty(() => config.horizontalBuffer, false),
        material: Cesium.Color.fromCssColorString('#dc2626').withAlpha(0.10),
        outline: true,
        outlineColor: Cesium.Color.fromCssColorString('#dc2626').withAlpha(0.7),
        outlineWidth: 2,
        height: new Cesium.CallbackProperty(() => d.altitude, false),
        show: new Cesium.CallbackProperty(() => d.status === 'conflict', false),
      },
    })
  })

  cesiumViewer.scene.requestRender()
}

function updateCesium3D() {
  if (!cesiumViewer || !cesium3DReady) return
  drones.forEach(d => {
    const prop = cesiumDronePositions[d.id]
    if (prop) prop.setValue(Cesium.Cartesian3.fromDegrees(d.lng, d.lat, d.altitude))
  })
  cesiumViewer.scene.requestRender()
}

function destroyCesium() {
  cesium3DReady = false
  Object.keys(cesiumDronePositions).forEach(k => delete cesiumDronePositions[k])
  if (cesiumViewer && !cesiumViewer.isDestroyed()) cesiumViewer.destroy()
  cesiumViewer = null
}

// ═══════════════════════════════════════════════════════════
// 模式切换
// ═══════════════════════════════════════════════════════════
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

// ═══════════════════════════════════════════════════════════
// 配置变更
// ═══════════════════════════════════════════════════════════
function onConfigChange() {
  detectConflicts()
  updateView()
}

function applyConfig() {
  onConfigChange()
  const n = conflictCount.value
  if (n > 0) {
    ElMessage.warning(`配置已应用：水平缓冲${config.horizontalBuffer}m，垂直间隔${config.verticalBuffer}m，${n}处冲突`)
  } else {
    ElMessage.success(`配置已应用：水平缓冲${config.horizontalBuffer}m，垂直间隔${config.verticalBuffer}m，无冲突`)
  }
  addLog('info', `安全配置更新：水平${config.horizontalBuffer}m / 垂直${config.verticalBuffer}m / 警戒${config.warnDistance}m`)
}

function resetConfig() {
  config.horizontalBuffer = 150
  config.warnDistance = 350
  config.verticalBuffer = 40
  onConfigChange()
  ElMessage.info('已恢复默认安全配置')
  addLog('info', '安全配置恢复默认值')
}

// ═══════════════════════════════════════════════════════════
// 生命周期
// ═══════════════════════════════════════════════════════════
onMounted(async () => {
  await initAMap()
  addLog('info', '系统初始化完成，4条交叉航线，8架无人机，监测缓冲区重叠')
})

onUnmounted(() => {
  pauseSim()
  destroyAMap()
  destroyCesium()
})
</script>

<style scoped>
.sba-page { display: flex; height: 100%; overflow: hidden; }

/* ── 左侧面板 ───────────────────────────── */
.sba-panel {
  width: 310px; flex-shrink: 0; background: #fff; border-right: 1px solid #e5e7eb;
  overflow-y: auto; padding: 14px;
}
.panel-header { display: flex; align-items: center; gap: 8px; margin-bottom: 14px; flex-wrap: wrap; }
.panel-header h2 { font-size: 15px; font-weight: 700; color: #111827; margin: 0; flex: 1; }
.panel-icon { font-size: 20px; }
.section { border-top: 1px solid #f3f4f6; padding-top: 12px; margin-bottom: 12px; }
.section-title { font-size: 13px; font-weight: 600; color: #374151; margin: 0 0 10px; display: flex; align-items: center; gap: 6px; }
.drone-count { font-size: 11px; font-weight: 400; color: #9ca3af; }
.time-display { font-size: 13px; font-weight: 700; color: #2563eb; margin-left: auto; font-variant-numeric: tabular-nums; }

.param-row { display: flex; align-items: center; gap: 6px; margin-bottom: 8px; }
.param-row > span:first-child { font-size: 12px; color: #6b7280; width: 58px; flex-shrink: 0; }
.unit { font-size: 12px; color: #9ca3af; flex-shrink: 0; }
.config-actions { display: flex; gap: 6px; margin-top: 4px; }

/* 时间轴 */
.timeline-row { display: flex; align-items: center; }
.timeline-ticks { display: flex; justify-content: space-between; padding: 0 2px; margin-top: -4px; margin-bottom: 6px; }
.tick { font-size: 10px; color: #9ca3af; }
.period-select-row { display: flex; align-items: center; gap: 6px; margin-bottom: 8px; }
.period-label { font-size: 12px; color: #6b7280; width: 28px; flex-shrink: 0; }
.ctrl-row { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.speed-label { font-size: 12px; color: #6b7280; margin-left: 4px; }

/* 无人机状态 */
.drone-item { margin-bottom: 6px; padding: 5px 7px; background: #f9fafb; border-radius: 6px; border: 1px solid #f3f4f6; }
.drone-header { display: flex; align-items: center; gap: 6px; margin-bottom: 3px; }
.drone-dot { width: 9px; height: 9px; border-radius: 50%; flex-shrink: 0; }
.drone-name { font-size: 12px; font-weight: 500; color: #374151; flex: 1; }
.drone-info-row { display: flex; gap: 10px; padding-left: 15px; }
.drone-route { font-size: 10px; color: #9ca3af; }
.drone-pos { font-size: 10px; color: #6b7280; }
.drone-alt { font-size: 10px; color: #6b7280; font-weight: 500; }
.conflict-warn {
  margin-top: 8px; padding: 7px 10px; background: #fef2f2; border: 1px solid #fecaca;
  border-radius: 6px; font-size: 11px; color: #dc2626; line-height: 1.5;
}

/* 事件日志 */
.log-section { flex: 1; min-height: 0; }
.event-log { max-height: 170px; overflow-y: auto; }
.event-item { display: flex; gap: 6px; padding: 5px 0; border-bottom: 1px solid #f9fafb; font-size: 11px; }
.event-time { color: #9ca3af; flex-shrink: 0; font-variant-numeric: tabular-nums; }
.event-body { flex: 1; min-width: 0; }
.event-msg { color: #374151; display: block; }
.event-solution { color: #2563eb; display: block; margin-top: 2px; font-style: italic; }
.event-item.danger .event-msg { color: #dc2626; font-weight: 600; }
.event-item.warn .event-msg { color: #d97706; }
.event-item.success .event-msg { color: #16a34a; }
.empty-log { text-align: center; color: #d1d5db; font-size: 12px; padding: 20px 0; }

/* ── 右侧区域 ───────────────────────────── */
.right-section { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
.view-mode-bar {
  flex-shrink: 0; height: 46px; padding: 0 16px;
  background: #fff; border-bottom: 1px solid #e5e7eb;
  display: flex; align-items: center; gap: 12px;
}
.mode-btns { display: flex; gap: 2px; background: #f3f4f6; padding: 3px; border-radius: 8px; }
.mode-btn {
  padding: 5px 16px; border: none; border-radius: 6px; font-size: 13px; font-weight: 500;
  cursor: pointer; color: #6b7280; background: transparent; transition: all .15s; white-space: nowrap;
}
.mode-btn.active { background: #2563eb; color: #fff; box-shadow: 0 1px 3px rgba(37,99,235,.4); }
.mode-tip { font-size: 12px; color: #9ca3af; flex: 1; }
.conflict-badge {
  padding: 4px 10px; background: #fef2f2; border: 1px solid #fecaca;
  border-radius: 6px; font-size: 12px; color: #dc2626; font-weight: 600; flex-shrink: 0;
}

/* 地图区 */
.map-area { flex: 1; position: relative; overflow: hidden; }
.map-container { width: 100%; height: 100%; }

/* 图例 */
.map-legend {
  position: absolute; bottom: 18px; right: 14px; background: rgba(255,255,255,0.95);
  border-radius: 8px; padding: 10px 14px; box-shadow: 0 2px 8px rgba(0,0,0,.15);
  font-size: 11px; z-index: 10; pointer-events: none; max-height: 60%; overflow-y: auto;
}
.legend-title { font-weight: 600; color: #374151; margin-bottom: 6px; font-size: 12px; }
.legend-item { display: flex; align-items: center; gap: 7px; margin-bottom: 3px; color: #6b7280; }
.legend-swatch { width: 20px; height: 10px; border-radius: 3px; flex-shrink: 0; }
.legend-divider { border-top: 1px solid #e5e7eb; margin: 5px 0; }
</style>

<!-- 全局样式：AMap 标签 -->
<style>
.sba-drone-tag {
  color: #fff; padding: 3px 7px; border-radius: 4px; font-size: 11px;
  white-space: nowrap; box-shadow: 0 1px 4px rgba(0,0,0,.3); font-weight: 500;
}
</style>
