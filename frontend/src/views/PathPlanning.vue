<template>
  <div class="path-planning">
    <!-- 左侧控制面板 -->
    <aside class="control-panel">
      <!-- ═══ 规划模式选择器（顶层） ═══ -->
      <div class="mode-selector">
        <el-radio-group v-model="planningMode" size="small">
          <el-radio-button value="points">📍 选点规划</el-radio-button>
          <el-radio-button value="patrol">🌲 林场/农田巡视巡逻</el-radio-button>
        </el-radio-group>
      </div>

      <!-- ═══ 巡逻子模式选择 ═══ -->
      <div v-if="planningMode === 'patrol'" class="mode-selector sub-selector">
        <el-radio-group v-model="patrolMode" size="small">
          <el-radio-button value="line">✈️ 沿线飞行</el-radio-button>
          <el-radio-button value="polygon">🔷 空域巡回</el-radio-button>
        </el-radio-group>
      </div>

      <!-- ═══ 选点规划：起终点设置 ═══ -->
      <div v-if="planningMode === 'points'" class="panel-section">
        <h3 class="section-title">📍 起终点设置</h3>

        <div class="point-input">
          <label>起点</label>
          <div class="input-row">
            <el-input v-model="startInput" placeholder="输入坐标 (lng,lat)" size="small" @keyup.enter="geocodeStart">
              <template #prefix><span style="color:#16a34a">●</span></template>
            </el-input>
            <el-button size="small" @click="pickPoint('start')">
              {{ pickingPoint === 'start' ? '取消' : '地图选点' }}
            </el-button>
          </div>
        </div>

        <div v-for="(wp, index) in waypoints" :key="index" class="point-input">
          <label>途经点 {{ index + 1 }}</label>
          <div class="input-row">
            <el-input v-model="waypoints[index].input" :placeholder="`途经点 ${index + 1}`" size="small">
              <template #prefix><span style="color:#2563eb">●</span></template>
            </el-input>
            <el-button size="small" @click="pickPoint('waypoint-' + index)">
              {{ pickingPoint === 'waypoint-' + index ? '取消' : '选点' }}
            </el-button>
            <el-button size="small" type="danger" @click="removeWaypoint(index)">删除</el-button>
          </div>
        </div>

        <el-button type="primary" size="small" plain @click="addWaypoint" style="width:100%;margin-bottom:12px">
          + 添加途经点
        </el-button>

        <div class="point-input">
          <label>终点</label>
          <div class="input-row">
            <el-input v-model="endInput" placeholder="输入坐标 (lng,lat)" size="small" @keyup.enter="geocodeEnd">
              <template #prefix><span style="color:#dc2626">●</span></template>
            </el-input>
            <el-button size="small" @click="pickPoint('end')">
              {{ pickingPoint === 'end' ? '取消' : '地图选点' }}
            </el-button>
          </div>
        </div>
      </div>

      <!-- ═══ 沿线飞行设置 ═══ -->
      <div v-if="planningMode === 'patrol' && patrolMode === 'line'" class="panel-section">
        <h3 class="section-title">✈️ 沿线飞行设置</h3>
        <p class="mode-desc">在地图上绘制飞行线，系统将沿线生成巡视航线，自动跟随地形起伏</p>
        <el-button
          @click="startLineDrawing"
          :type="isDrawingLine ? 'warning' : 'primary'"
          style="width:100%;margin-bottom:8px"
        >
          {{ isDrawingLine ? '取消绘制' : '开始绘制飞行线' }}
        </el-button>
        <p v-if="isDrawingLine" class="drawing-hint">
          🖱️ 左键点击添加顶点 · 右键/Enter 完成 · Esc 取消
        </p>
        <div v-if="linePath" class="drawing-status">
          <span>✅ 已绘制 <strong>{{ linePath.length }}</strong> 个航路点</span>
          <el-button size="small" text type="danger" @click="clearLine">清除重绘</el-button>
        </div>
      </div>

      <!-- ═══ 空域巡回设置 ═══ -->
      <div v-if="planningMode === 'patrol' && patrolMode === 'polygon'" class="panel-section">
        <h3 class="section-title">🔷 空域巡回设置</h3>
        <p class="mode-desc">在地图上绘制多边形空域，系统根据空域生成巡逻路线，自动跟随地形起伏</p>
        <el-button
          @click="startPolygonDrawing"
          :type="isDrawingPolygon ? 'warning' : 'primary'"
          style="width:100%;margin-bottom:8px"
        >
          {{ isDrawingPolygon ? '取消绘制' : '开始绘制空域' }}
        </el-button>
        <p v-if="isDrawingPolygon" class="drawing-hint">
          🖱️ 左键点击添加顶点 · 点击首点/右键/Enter 闭合 · Esc 取消
        </p>
        <div v-if="polygonCoords" class="drawing-status">
          <span>✅ 已绘制 <strong>{{ polygonCoords.length }}</strong> 个顶点的空域</span>
          <el-button size="small" text type="danger" @click="clearPolygon">清除重绘</el-button>
        </div>

        <!-- 巡逻模式 + 参数 -->
        <div v-if="polygonCoords" style="margin-top:12px">
          <div class="param-item">
            <span>巡逻模式</span>
            <el-radio-group v-model="patrolPattern" size="small">
              <el-radio value="boundary">边界巡逻</el-radio>
              <el-radio value="lawnmower">犁地式覆盖</el-radio>
            </el-radio-group>
          </div>

          <template v-if="patrolPattern === 'lawnmower'">
            <div class="param-item">
              <span>条带间距 (m)</span>
              <el-slider v-model="stripSpacing" :min="30" :max="500" :step="10" show-input input-size="small" />
            </div>
            <div class="param-item">
              <span>巡逻方向 (°)</span>
              <el-slider v-model="patrolAngle" :min="0" :max="180" :step="15" show-input input-size="small" />
            </div>
          </template>

          <el-button type="success" size="small" @click="doGeneratePatrolRoute" style="width:100%;margin-top:6px">
            🔄 生成巡逻路线
          </el-button>

          <div v-if="generatedWaypoints" class="drawing-status" style="margin-top:8px">
            <span>✅ 已生成 <strong>{{ generatedWaypoints.length }}</strong> 个巡逻航路点</span>
          </div>
        </div>
      </div>

      <!-- ═══ 参数设置 ═══ -->
      <div class="panel-section">
        <h3 class="section-title">⚙️ 参数设置</h3>

        <!-- 巡逻模式：离地飞行高度 -->
        <div v-if="planningMode === 'patrol'" class="param-item">
          <span>离地飞行高度</span>
          <div class="slider-row">
            <el-slider v-model="terrainAgl" :min="30" :max="200" :step="10" show-input input-size="small" />
            <span class="unit">m</span>
          </div>
        </div>

        <div class="param-item">
          <span>无人机速度</span>
          <el-slider v-model="droneSpeed" :min="5" :max="30" :step="1" show-input input-size="small" />
        </div>

        <div class="param-item"><el-checkbox v-model="avoidNoFly">避开禁飞区</el-checkbox></div>
        <div class="param-item"><el-checkbox v-model="avoidHeightLimit">避开限高区</el-checkbox></div>

        <!-- 选点规划专属：建筑物避让 -->
        <template v-if="planningMode === 'points'">
          <div class="param-item"><el-checkbox v-model="avoidBuildings">避开建筑物</el-checkbox></div>
          <div v-if="avoidBuildings" class="param-item param-item--indent">
            <div class="param-label-row">
              <span>强制飞行限高</span>
              <span class="param-hint">低于限高的建筑从上方飞越；高于限高的建筑群强制水平绕行（不会超过此高度）</span>
            </div>
            <div class="slider-row">
              <el-slider v-model="suggestedAlt" :min="50" :max="250" :step="10" show-input input-size="small" />
              <span class="unit">m</span>
            </div>
          </div>
        </template>

        <div class="param-item"><el-checkbox v-model="considerWeather">考虑天气</el-checkbox></div>
      </div>

      <el-button type="primary" size="large" @click="doPlan" :loading="planning" :disabled="!canPlan" style="width:100%">
        🚁 开始路径规划
      </el-button>

      <div v-if="planProgress !== null" class="plan-progress">
        <div class="plan-progress-label">
          <span>{{ planProgressLabel || '计算真实建筑绕行航线' }}</span>
          <span>{{ planProgress }}%</span>
        </div>
        <el-progress :percentage="planProgress" :stroke-width="10" :show-text="false" status="success" />
      </div>

      <div v-if="planResult" class="result-section">
        <h3 class="section-title">📋 规划结果</h3>
        <div class="result-item">
          <span class="result-label">总距离</span>
          <span class="result-value">{{ (planResult.total_distance / 1000).toFixed(2) }} km</span>
        </div>
        <div class="result-item">
          <span class="result-label">预计时间</span>
          <span class="result-value">{{ formatTime(planResult.estimated_time) }}</span>
        </div>
        <div class="result-item">
          <span class="result-label">可行性</span>
          <span class="result-value" :style="{ color: planResult.is_feasible ? '#16a34a' : '#dc2626' }">
            {{ planResult.is_feasible ? '✅ 可行' : '⚠️ 有风险' }}
          </span>
        </div>
        <div v-if="planResult.warnings?.length > 0" class="warnings">
          <div v-for="(w, i) in planResult.warnings" :key="i" class="warning-item">⚠️ {{ w }}</div>
        </div>
        <!-- 飞行阶段图例 -->
        <div class="phase-legend">
          <div class="legend-title">飞行阶段</div>
          <div v-for="(ph, key) in PHASE_LEGEND" :key="key" class="legend-item">
            <span class="legend-dot" :style="{ background: ph.color }"></span>
            <span>{{ ph.label }}</span>
          </div>
        </div>
      </div>

      <el-button
        v-if="planResult?.is_feasible"
        type="success"
        size="large"
        style="width:100%"
        @click="openSaveDialog"
      >
        💾 保存航线
      </el-button>
    </aside>

    <!-- 保存航线弹窗 -->
    <el-dialog v-model="saveDialogVisible" title="保存航线信息" width="440px" append-to-body>
      <el-form :model="saveForm" label-width="80px">
        <el-form-item label="航线名称" required>
          <el-input v-model="saveForm.name" placeholder="请输入航线名称" />
        </el-form-item>
        <el-form-item label="所属企业" required>
          <el-input v-model="saveForm.enterprise" placeholder="请输入企业名称" />
        </el-form-item>
        <el-form-item label="负责人" required>
          <el-input v-model="saveForm.person" placeholder="请输入负责人姓名" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="saveForm.notes" type="textarea" :rows="2" placeholder="可选备注" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="saveDialogVisible = false">取消</el-button>
        <el-button
          type="primary"
          :disabled="!saveForm.name || !saveForm.enterprise || !saveForm.person"
          @click="confirmSaveRoute"
        >确认保存</el-button>
      </template>
    </el-dialog>

    <!-- 地图区 — 使用统一的 MapContainer 组件 -->
    <div class="map-area">
      <MapContainer ref="mapContainerRef" />

    </div>
  </div>
</template>

<script setup>
import { ref, reactive, watch, computed, onMounted, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { planPath } from '@/api/pathfinding'
import { checkPoint } from '@/api/zones'
import MapContainer from '@/components/MapContainer.vue'
import { useMapStore } from '@/stores/map'
import { generateBoundaryPatrol, generateLawnmowerPatrol } from '@/utils/patrolRouteGenerator'
import { SAMPLE_ROUTES } from '@/data/sampleRoutes'

const mapStore = useMapStore()
const mapContainerRef = ref(null)

// 地图就绪后绘制示例航线静态背景（相位着色、无动画）
// 用 mapStore.map watcher 代替 setTimeout，避免 AMap 未初始化完就调用
onMounted(() => {
  if (mapStore.map) {
    nextTick(() => mapContainerRef.value?.drawBackgroundRoutes(SAMPLE_ROUTES))
  }
})
watch(() => mapStore.map, (newMap) => {
  if (newMap && mapContainerRef.value) {
    mapContainerRef.value.drawBackgroundRoutes(SAMPLE_ROUTES)
  }
})

// ── 规划模式（顶层） ──────────────────────────
const planningMode = ref('points')  // 'points' | 'patrol'
// ── 巡逻子模式 ────────────────────────────────
const patrolMode = ref('line')      // 'line' | 'polygon'

// ── 选点规划状态 ──────────────────────────────
const startInput = ref('')
const endInput = ref('')
const startPoint = ref(null)
const endPoint = ref(null)
const waypoints = ref([])

// ── 沿线飞行状态 ──────────────────────────────
const isDrawingLine = ref(false)
const linePath = ref(null)

// ── 空域巡回状态 ──────────────────────────────
const isDrawingPolygon = ref(false)
const polygonCoords = ref(null)
const patrolPattern = ref('boundary')
const stripSpacing = ref(100)
const patrolAngle = ref(0)
const generatedWaypoints = ref(null)

// ── 参数 ──────────────────────────────────────
const droneSpeed = ref(15)
const terrainAgl = ref(80)        // 巡逻模式离地飞行高度
const suggestedAlt = ref(120)     // 选点模式强制飞行限高
const avoidNoFly = ref(true)
const avoidHeightLimit = ref(true)
const avoidBuildings = ref(true)
const considerWeather = ref(true)

// ── 选点交互 ──────────────────────────────────
const pickingPoint = ref(null)
const planning = ref(false)
const planResult = ref(null)
const planProgress = ref(null)
const planProgressLabel = ref('')

// 自定义标记
let startMarker = null
let endMarker = null
let waypointMarkers = []
let lastPlanPath = null
let lastAltProfile = null

// ── 飞行阶段颜色映射 ──────────────────────────
const PHASE_LEGEND = {
  ascent:     { color: '#22c55e', label: '起飞爬升段' },
  cruise:     { color: '#3b82f6', label: '巡航段' },
  descent:    { color: '#f59e0b', label: '降落下降段' },
  building:   { color: '#a855f7', label: '建筑物避让段' },
  height_limit: { color: '#ef4444', label: '限高区绕行段' },
}

// ── 保存航线弹窗 ──────────────────────────────
const saveDialogVisible = ref(false)
const saveForm = reactive({ name: '', enterprise: '', person: '', notes: '' })

function openSaveDialog() {
  if (!planResult.value?.is_feasible) return
  if (planningMode.value === 'points') {
    const start = startPoint.value
    saveForm.name = start ? `${start.lng.toFixed(3)},${start.lat.toFixed(3)} → 规划航线` : '新规划航线'
  } else if (patrolMode.value === 'line') {
    saveForm.name = '沿线飞行巡视航线'
  } else {
    saveForm.name = patrolPattern.value === 'boundary' ? '边界巡逻航线' : '犁地式覆盖巡逻航线'
  }
  saveForm.enterprise = ''
  saveForm.person = ''
  saveForm.notes = ''
  saveDialogVisible.value = true
}

function confirmSaveRoute() {
  if (!saveForm.name || !saveForm.enterprise || !saveForm.person) {
    ElMessage.warning('请填写完整信息')
    return
  }
  const r = planResult.value
  const route = {
    id: Date.now(),
    name: saveForm.name,
    enterprise: saveForm.enterprise,
    responsible_person: saveForm.person,
    notes: saveForm.notes,
    status: 'planned',
    total_distance: r.total_distance,
    estimated_time: r.estimated_time,
    waypoints: r.path || [],
    route_line: { type: 'LineString', coordinates: (r.path || []).map(p => [p.lng, p.lat]) },
    altitude_profile: r.altitude_profile || [],
    created_at: new Date().toISOString(),
  }
  mapStore.addSavedRoute(route)
  saveDialogVisible.value = false
  ElMessage.success('航线已保存至态势大屏航线列表')
}

// ── 是否可以规划 ──────────────────────────────
const canPlan = computed(() => {
  if (planningMode.value === 'points') return startPoint.value && endPoint.value
  if (planningMode.value === 'patrol' && patrolMode.value === 'line') return linePath.value && linePath.value.length >= 2
  if (planningMode.value === 'patrol' && patrolMode.value === 'polygon') return generatedWaypoints.value && generatedWaypoints.value.length >= 2
  return false
})

// ── 模式或子模式切换时清理 ───────────────────
watch([planningMode, patrolMode], () => {
  const mapRef = mapContainerRef.value
  mapRef?.stopDrawing()
  mapRef?.clearDrawing()
  mapRef?.removeClickHandler()
  pickingPoint.value = null
  isDrawingLine.value = false
  isDrawingPolygon.value = false
  clearOldPath()
  mapRef?.clearPlanPath()
  planResult.value = null
  planProgress.value = null
})

// ── 2D/3D 切换时重绘规划路径 ──────────────────
watch(() => mapContainerRef.value?.viewMode, () => {
  redrawAfterModeSwitch()
})

// ── 地图点击选点 ──────────────────────────────
watch(pickingPoint, (val) => {
  if (val) {
    mapContainerRef.value?.addClickHandler(onMapClick)
  } else {
    mapContainerRef.value?.removeClickHandler()
  }
})

async function onMapClick(pos) {
  if (!pickingPoint.value) return
  const mapRef = mapContainerRef.value

  try {
    const check = await checkPoint(pos.lng, pos.lat)
    if (check.in_no_fly_zone) {
      ElMessage.error('该位置在禁飞区内，无法选点')
      pickingPoint.value = null
      return
    }
    if (check.height_limits?.length > 0) {
      const limits = check.height_limits.map(l => l.max_altitude ? `${l.max_altitude}m` : l.name).join(', ')
      ElMessage.warning(`该位置在限高区内 (${limits})，请谨慎选择`)
    }
  } catch {
    // API 调用失败时仍允许选点
  }

  if (pickingPoint.value === 'start') {
    startPoint.value = pos
    startInput.value = `${pos.lng.toFixed(6)}, ${pos.lat.toFixed(6)}`
    if (startMarker) mapRef?.removeMarker(startMarker)
    startMarker = mapRef?.addMarker(pos.lng, pos.lat, '#16a34a')
    ElMessage.success('起点已设置')
  } else if (pickingPoint.value === 'end') {
    endPoint.value = pos
    endInput.value = `${pos.lng.toFixed(6)}, ${pos.lat.toFixed(6)}`
    if (endMarker) mapRef?.removeMarker(endMarker)
    endMarker = mapRef?.addMarker(pos.lng, pos.lat, '#dc2626')
    ElMessage.success('终点已设置')
  } else if (pickingPoint.value.startsWith('waypoint-')) {
    const idx = parseInt(pickingPoint.value.split('-')[1])
    if (waypoints.value[idx]) {
      waypoints.value[idx].input = `${pos.lng.toFixed(6)}, ${pos.lat.toFixed(6)}`
      if (waypointMarkers[idx]) mapRef?.removeMarker(waypointMarkers[idx])
      waypointMarkers[idx] = mapRef?.addMarker(pos.lng, pos.lat, '#2563eb')
      ElMessage.success(`途经点 ${idx + 1} 已设置`)
    }
  }
  pickingPoint.value = null
}

function pickPoint(type) {
  if (pickingPoint.value === type) {
    pickingPoint.value = null
    return
  }
  pickingPoint.value = type
  ElMessage.info('请在地图上点击选择位置')
}

function parseCoords(input) {
  const parts = input.split(',').map((s) => parseFloat(s.trim()))
  return parts.length === 2 && !isNaN(parts[0]) && !isNaN(parts[1]) ? { lng: parts[0], lat: parts[1] } : null
}

function geocodeStart() { const c = parseCoords(startInput.value); if (c) startPoint.value = c }
function geocodeEnd() { const c = parseCoords(endInput.value); if (c) endPoint.value = c }
function addWaypoint() { waypoints.value.push({ input: '' }) }
function removeWaypoint(i) { waypoints.value.splice(i, 1) }

// ── 沿线飞行绘制 ──────────────────────────────
function startLineDrawing() {
  const mapRef = mapContainerRef.value
  if (!mapRef) return
  if (isDrawingLine.value) {
    mapRef.stopDrawing()
    isDrawingLine.value = false
    ElMessage.info('已取消绘制')
    return
  }
  linePath.value = null
  isDrawingLine.value = true
  mapRef.clearDrawing()
  mapRef.startDrawLine((path) => {
    linePath.value = path
    isDrawingLine.value = false
    ElMessage.success(`已绘制飞行线，共 ${path.length} 个航路点`)
  })
}

function clearLine() {
  mapContainerRef.value?.clearDrawing()
  linePath.value = null
  isDrawingLine.value = false
}

// ── 空域巡回绘制 ──────────────────────────────
function startPolygonDrawing() {
  const mapRef = mapContainerRef.value
  if (!mapRef) return
  if (isDrawingPolygon.value) {
    mapRef.stopDrawing()
    isDrawingPolygon.value = false
    ElMessage.info('已取消绘制')
    return
  }
  polygonCoords.value = null
  generatedWaypoints.value = null
  isDrawingPolygon.value = true
  mapRef.clearDrawing()
  mapRef.startDrawPolygon((path) => {
    polygonCoords.value = path
    isDrawingPolygon.value = false
    ElMessage.success(`已绘制空域，共 ${path.length} 个顶点`)
  })
}

function clearPolygon() {
  mapContainerRef.value?.clearDrawing()
  polygonCoords.value = null
  generatedWaypoints.value = null
  isDrawingPolygon.value = false
}

function doGeneratePatrolRoute() {
  if (!polygonCoords.value) return
  try {
    if (patrolPattern.value === 'boundary') {
      generatedWaypoints.value = generateBoundaryPatrol(polygonCoords.value)
    } else {
      generatedWaypoints.value = generateLawnmowerPatrol(polygonCoords.value, {
        stripSpacing: stripSpacing.value,
        angle: patrolAngle.value,
      })
    }
    ElMessage.success(`已生成 ${generatedWaypoints.value.length} 个巡逻航路点`)
  } catch (e) {
    ElMessage.error('巡逻路线生成失败: ' + (e.message || '未知错误'))
  }
}

// ── 路径规划 ──────────────────────────────────
async function doPlan() {
  let start, end, waypointsList

  if (planningMode.value === 'points') {
    if (!startPoint.value || !endPoint.value) { ElMessage.warning('请先设置起点和终点'); return }
    start = { ...startPoint.value, alt: 100 }
    end = { ...endPoint.value, alt: 100 }
    waypointsList = waypoints.value.map(wp => parseCoords(wp.input)).filter(Boolean).map(c => ({ ...c, alt: 100 }))
  } else if (patrolMode.value === 'line') {
    if (!linePath.value || linePath.value.length < 2) { ElMessage.warning('请先绘制飞行线（至少2个点）'); return }
    const pts = linePath.value
    start = { lng: pts[0].lng, lat: pts[0].lat, alt: terrainAgl.value }
    end = { lng: pts[pts.length - 1].lng, lat: pts[pts.length - 1].lat, alt: terrainAgl.value }
    waypointsList = pts.slice(1, -1).map(p => ({ lng: p.lng, lat: p.lat, alt: terrainAgl.value }))
  } else {
    if (!generatedWaypoints.value || generatedWaypoints.value.length < 2) { ElMessage.warning('请先绘制空域并生成巡逻路线'); return }
    const pts = generatedWaypoints.value
    start = { lng: pts[0].lng, lat: pts[0].lat, alt: terrainAgl.value }
    end = { lng: pts[pts.length - 1].lng, lat: pts[pts.length - 1].lat, alt: terrainAgl.value }
    waypointsList = pts.slice(1, -1).map(p => ({ lng: p.lng, lat: p.lat, alt: terrainAgl.value }))
  }

  planning.value = true
  planProgress.value = 3
  planProgressLabel.value = '正在请求规划数据...'
  try {
    const result = await planPath({
      start, end,
      waypoints: waypointsList,
      drone_speed: droneSpeed.value,
      suggested_alt: planningMode.value === 'points' ? suggestedAlt.value : terrainAgl.value,
      avoid_no_fly: avoidNoFly.value,
      avoid_height_limit: avoidHeightLimit.value,
      avoid_buildings: planningMode.value === 'points' ? avoidBuildings.value : false,
      consider_weather: considerWeather.value,
    })
    if (result.blocked_in_no_fly) {
      planResult.value = null
      planProgress.value = null
      clearOldPath()
      mapContainerRef.value?.clearPlanPath?.()
      const names = (result.blocked_points || []).map(b => b.label).join('、')
      ElMessageBox.alert(
        `${names || '部分点位'} 位于禁飞区内，无法为其规划航线。请将该点移出禁飞区后重试。`,
        '无法规划航线',
        { type: 'error', confirmButtonText: '我知道了' }
      )
      return
    }
    planResult.value = result
    drawRouteOnMap(result.path, result.altitude_profile)
    ElMessage.success('路径规划完成')
  } catch (e) {
    planProgress.value = null
    ElMessage.error('路径规划失败: ' + (e.message || '未知错误'))
  } finally { planning.value = false }
}

// ── 在地图上绘制规划路径 ──────────────────────
async function drawRouteOnMap(pathPoints, altitudeProfile) {
  const mapRef = mapContainerRef.value
  if (!mapRef || !pathPoints?.length) return

  lastPlanPath = pathPoints
  lastAltProfile = altitudeProfile

  clearOldPath()
  mapRef.clearPlanPath()

  let adjustedPath = pathPoints
  let adjustedProfile = altitudeProfile

  let controlPts
  if (planningMode.value === 'points') {
    const activeWaypoints = waypoints.value.map(wp => parseCoords(wp.input)).filter(Boolean)
    controlPts = [
      { lng: startPoint.value.lng, lat: startPoint.value.lat },
      ...activeWaypoints.map(w => ({ lng: w.lng, lat: w.lat })),
      { lng: endPoint.value.lng, lat: endPoint.value.lat },
    ]
  } else if (patrolMode.value === 'line') {
    controlPts = (linePath.value || []).map(p => ({ lng: p.lng, lat: p.lat }))
  } else {
    controlPts = (generatedWaypoints.value || []).map(p => ({ lng: p.lng, lat: p.lat }))
  }

  // 起终点标记
  startMarker = mapRef.addMarker(adjustedPath[0].lng, adjustedPath[0].lat, '#16a34a')
  const endPt = adjustedPath[adjustedPath.length - 1]
  endMarker = mapRef.addMarker(endPt.lng, endPt.lat, '#dc2626')

  // 途经点标记
  if (planningMode.value === 'points') {
    const activeWaypoints = waypoints.value.map(wp => parseCoords(wp.input)).filter(Boolean)
    for (const wp of activeWaypoints) {
      const m = mapRef.addMarker(wp.lng, wp.lat, '#2563eb')
      if (m) waypointMarkers.push(m)
    }
  } else if (controlPts.length > 2) {
    const step = patrolMode.value === 'polygon' ? Math.max(1, Math.floor(controlPts.length / 20)) : 1
    for (let i = 1; i < controlPts.length - 1; i += step) {
      const m = mapRef.addMarker(controlPts[i].lng, controlPts[i].lat, '#2563eb')
      if (m) waypointMarkers.push(m)
    }
  }

  const cruiseAlt = planningMode.value === 'points' ? suggestedAlt.value : terrainAgl.value
  const useBuildings = planningMode.value === 'points' ? avoidBuildings.value : false

  if (mapRef.viewMode === '3D' && planningMode.value === 'points') {
    planProgress.value = 18
    planProgressLabel.value = '计算真实建筑绕行航线'
    mapRef.drawPlanPath(adjustedPath, adjustedProfile, {
      cruiseAlt,
      avoidBuildings: useBuildings,
      avoidNoFly: avoidNoFly.value,
      controlPts,
      onProgress: (frac, label) => {
        planProgress.value = Math.round(18 + frac * 82)
        planProgressLabel.value = label || ''
        if (frac >= 1) setTimeout(() => { planProgress.value = null }, 800)
      },
    })
  } else if (mapRef.viewMode === '3D') {
    mapRef.drawPlanPath(adjustedPath, adjustedProfile, {
      cruiseAlt,
      avoidBuildings: useBuildings,
      avoidNoFly: avoidNoFly.value,
      controlPts,
    })
    planProgress.value = null
  } else {
    mapRef.drawPlanPath(adjustedPath, adjustedProfile, {
      cruiseAlt,
      avoidBuildings: useBuildings,
      avoidNoFly: avoidNoFly.value,
      controlPts,
    })
    planProgress.value = null
  }
}

function redrawAfterModeSwitch() {
  if (lastPlanPath) {
    setTimeout(() => drawRouteOnMap(lastPlanPath, lastAltProfile), 500)
  }
}

function clearOldPath() {
  if (startMarker) { mapContainerRef.value?.removeMarker(startMarker); startMarker = null }
  if (endMarker) { mapContainerRef.value?.removeMarker(endMarker); endMarker = null }
  waypointMarkers.forEach(m => mapContainerRef.value?.removeMarker(m))
  waypointMarkers = []
}

function formatTime(s) {
  if (!s) return '--'
  const m = Math.floor(s / 60)
  if (m > 60) return `${Math.floor(m / 60)}小时${m % 60}分钟`
  return `${m}分${Math.floor(s % 60)}秒`
}
</script>

<style scoped>
.path-planning { display: flex; width: 100%; height: 100%; }

.control-panel {
  width: 360px; padding: 16px; overflow-y: auto;
  background: #f8f9fa; border-right: 1px solid #e5e7eb;
  display: flex; flex-direction: column; gap: 16px;
}

.mode-selector {
  display: flex; justify-content: center;
  padding: 4px; background: #f1f5f9; border-radius: 10px;
}
.mode-selector .el-radio-group { width: 100%; display: flex; }
.mode-selector :deep(.el-radio-button) { flex: 1; }
.mode-selector :deep(.el-radio-button__inner) {
  width: 100%; font-size: 12px; padding: 6px 4px;
}
.sub-selector {
  margin-top: -8px;
  padding: 3px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px;
}

.mode-desc {
  font-size: 12px; color: #6b7280; margin-bottom: 8px; line-height: 1.4;
}
.drawing-hint {
  font-size: 12px; color: #2563eb; margin: 6px 0; padding: 6px 10px;
  background: #eff6ff; border-radius: 6px; border: 1px solid #bfdbfe;
}
.drawing-status {
  display: flex; align-items: center; justify-content: space-between;
  font-size: 13px; color: #374151; margin-top: 8px;
  padding: 6px 10px; background: #f0fdf4; border-radius: 6px;
  border: 1px solid #bbf7d0;
}

.panel-section {
  background: #ffffff; border: 1px solid #e5e7eb;
  border-radius: 12px; padding: 16px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
}

.section-title { font-size: 14px; font-weight: 600; margin-bottom: 12px; color: #1f2937; }
.point-input { margin-bottom: 10px; }
.point-input label { display: block; font-size: 12px; color: #6b7280; margin-bottom: 4px; }
.input-row { display: flex; gap: 8px; }
.input-row .el-input { flex: 1; }
.param-item { margin-bottom: 10px; }
.param-item span { font-size: 13px; color: #6b7280; }
.param-item--indent { padding: 8px 10px; background: #f9fafb; border-radius: 8px; border: 1px solid #e5e7eb; margin-top: -4px; }
.param-label-row { display: flex; align-items: baseline; gap: 6px; margin-bottom: 6px; }
.param-hint { font-size: 11px; color: #9ca3af; flex: 1; line-height: 1.3; }
.slider-row { display: flex; align-items: center; gap: 8px; }
.slider-row .el-slider { flex: 1; }
.unit { font-size: 13px; color: #6b7280; flex-shrink: 0; }

.plan-progress {
  margin-top: 12px; padding: 12px 14px;
  background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 10px;
}
.plan-progress-label {
  display: flex; justify-content: space-between;
  font-size: 12px; color: #15803d; margin-bottom: 8px; font-weight: 500;
}

.result-section {
  background: #ffffff; border: 1px solid #e5e7eb;
  border-radius: 12px; padding: 16px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
}

.result-item { display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px solid #f3f4f6; }
.result-item:last-child { border-bottom: none; }
.result-label { font-size: 13px; color: #6b7280; }
.result-value { font-size: 14px; font-weight: 600; color: #2563eb; }
.warnings { margin-top: 12px; }
.warning-item { font-size: 12px; color: #ea580c; margin-bottom: 4px; }

.phase-legend { margin-top: 12px; padding-top: 10px; border-top: 1px solid #f3f4f6; }
.legend-title { font-size: 11px; font-weight: 600; color: #9ca3af; margin-bottom: 6px; text-transform: uppercase; letter-spacing: .5px; }
.legend-item { display: flex; align-items: center; gap: 8px; margin-bottom: 5px; font-size: 12px; color: #374151; }
.legend-dot { width: 28px; height: 5px; border-radius: 3px; flex-shrink: 0; }

.map-area { flex: 1; position: relative; }
</style>
