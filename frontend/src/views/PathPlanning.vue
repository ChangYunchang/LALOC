<template>
  <div class="path-planning">
    <!-- 左侧控制面板 -->
    <aside class="control-panel">
      <div class="panel-section">
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

      <div class="panel-section">
        <h3 class="section-title">⚙️ 参数设置</h3>
        <div class="param-item">
          <span>无人机速度</span>
          <el-slider v-model="droneSpeed" :min="5" :max="30" :step="1" show-input input-size="small" />
        </div>
        <div class="param-item"><el-checkbox v-model="avoidNoFly">避开禁飞区</el-checkbox></div>
        <div class="param-item"><el-checkbox v-model="avoidHeightLimit">避开限高区</el-checkbox></div>
        <div class="param-item"><el-checkbox v-model="avoidBuildings">避开建筑物</el-checkbox></div>
        <div class="param-item"><el-checkbox v-model="considerWeather">考虑天气</el-checkbox></div>
      </div>

      <el-button type="primary" size="large" @click="doPlan" :loading="planning" :disabled="!startPoint || !endPoint" style="width:100%">
        🚁 开始路径规划
      </el-button>

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
import { ref, reactive, watch, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { planPath } from '@/api/pathfinding'
import { checkPoint } from '@/api/zones'
import MapContainer from '@/components/MapContainer.vue'
import { useMapStore } from '@/stores/map'

const mapStore = useMapStore()
const mapContainerRef = ref(null)

// ── 保存航线弹窗 ──────────────────────────────
const saveDialogVisible = ref(false)
const saveForm = reactive({ name: '', enterprise: '', person: '', notes: '' })

function openSaveDialog() {
  if (!planResult.value?.is_feasible) return
  const start = startPoint.value
  saveForm.name = start ? `${start.lng.toFixed(3)},${start.lat.toFixed(3)} → 规划航线` : '新规划航线'
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
    route_line: {
      type: 'LineString',
      coordinates: (r.path || []).map(p => [p.lng, p.lat]),
    },
    altitude_profile: r.altitude_profile || [],
    created_at: new Date().toISOString(),
  }
  mapStore.addSavedRoute(route)
  saveDialogVisible.value = false
  ElMessage.success('航线已保存至态势大屏航线列表')
}

const startInput = ref('')
const endInput = ref('')
const startPoint = ref(null)
const endPoint = ref(null)
const waypoints = ref([])

const droneSpeed = ref(15)
const avoidNoFly = ref(true)
const avoidHeightLimit = ref(true)
const avoidBuildings = ref(true)
const considerWeather = ref(true)

const pickingPoint = ref(null)
const planning = ref(false)
const planResult = ref(null)

// 自定义标记
let startMarker = null
let endMarker = null
let waypointMarkers = []
let pathLines = []
let lastPlanPath = null
let lastAltProfile = null

// 飞行阶段颜色映射
const PHASE_COLORS = {
  ascent: '#22c55e',
  cruise: '#3b82f6',
  descent: '#f59e0b',
  height_limit: '#ef4444',
  building: '#a855f7',
}

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

  // 检查点击位置是否在禁飞区/限高区内
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

function geocodeStart() {
  const c = parseCoords(startInput.value)
  if (c) startPoint.value = c
}
function geocodeEnd() {
  const c = parseCoords(endInput.value)
  if (c) endPoint.value = c
}

function addWaypoint() { waypoints.value.push({ input: '' }) }
function removeWaypoint(i) { waypoints.value.splice(i, 1) }

// ── 路径规划 ──────────────────────────────────
async function doPlan() {
  if (!startPoint.value || !endPoint.value) { ElMessage.warning('请先设置起点和终点'); return }
  planning.value = true
  try {
    const wpCoords = waypoints.value.map(wp => parseCoords(wp.input)).filter(Boolean)
    const result = await planPath({
      start: { ...startPoint.value, alt: 100 },
      end: { ...endPoint.value, alt: 100 },
      waypoints: wpCoords.map(c => ({ ...c, alt: 100 })),
      drone_speed: droneSpeed.value,
      avoid_no_fly: avoidNoFly.value,
      avoid_height_limit: avoidHeightLimit.value,
      avoid_buildings: avoidBuildings.value,
      consider_weather: considerWeather.value,
    })
    planResult.value = result
    drawRouteOnMap(result.path, result.altitude_profile)
    ElMessage.success('路径规划完成')
  } catch (e) {
    ElMessage.error('路径规划失败: ' + (e.message || '未知错误'))
  } finally { planning.value = false }
}

// ── 在地图上绘制规划路径 ──────────────────────
async function drawRouteOnMap(pathPoints, altitudeProfile) {
  const mapRef = mapContainerRef.value
  if (!mapRef || !pathPoints?.length) return

  // 保存数据以便模式切换后重绘
  lastPlanPath = pathPoints
  lastAltProfile = altitudeProfile

  clearOldPath()
  mapRef.clearPlanPath()

  // 等待地图引擎准备好
  await new Promise(r => setTimeout(r, 300))

  // 添加起点标记
  startMarker = mapRef.addMarker(pathPoints[0].lng, pathPoints[0].lat, '#16a34a')
  // 添加终点标记
  const end = pathPoints[pathPoints.length - 1]
  endMarker = mapRef.addMarker(end.lng, end.lat, '#dc2626')
  // 添加途经点标记
  const activeWaypoints = waypoints.value
    .map(wp => parseCoords(wp.input))
    .filter(Boolean)
  for (const wp of activeWaypoints) {
    const m = mapRef.addMarker(wp.lng, wp.lat, '#2563eb')
    if (m) waypointMarkers.push(m)
  }

  // 绘制路径线
  mapRef.drawPlanPath(pathPoints, altitudeProfile)
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

.map-area { flex: 1; position: relative; }

</style>
