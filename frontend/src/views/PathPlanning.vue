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
        <div class="param-item">
          <span>安全距离</span>
          <el-slider v-model="safetyMargin" :min="10" :max="200" :step="10" show-input input-size="small" />
        </div>
        <div class="param-item"><el-checkbox v-model="avoidNoFly">避开禁飞区</el-checkbox></div>
        <div class="param-item"><el-checkbox v-model="avoidHeightLimit">避开限高区</el-checkbox></div>
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
    </aside>

    <!-- 地图区 -->
    <div class="map-area">
      <div id="planning-map" ref="mapRef"></div>

      <!-- 2D/3D 切换 - 左上角 -->
      <div class="map-controls-topleft">
        <el-button-group>
          <el-button :type="viewMode === '2D' ? 'primary' : 'default'" @click="switchMode('2D')" size="small">
            2D 平面
          </el-button>
          <el-button :type="viewMode === '3D' ? 'primary' : 'default'" @click="switchMode('3D')" size="small">
            3D 实景
          </el-button>
        </el-button-group>
      </div>

      <!-- 图例 - 右下角 -->
      <div class="planning-legend">
        <div class="legend-item"><span class="lc" style="background:rgba(252,165,165,0.5);border-color:#dc2626;"></span>禁飞区</div>
        <div class="legend-item"><span class="lc" style="background:rgba(253,186,116,0.4);border-color:#ea580c;"></span>限高区</div>
        <div class="legend-item"><span class="ll" style="background:#2563eb;"></span>规划路径</div>
        <div class="legend-item"><span class="ld" style="background:#16a34a;"></span>起点</div>
        <div class="legend-item"><span class="ld" style="background:#dc2626;"></span>终点</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, shallowRef } from 'vue'
import AMapLoader from '@amap/amap-jsapi-loader'
import { ElMessage } from 'element-plus'
import { planPath } from '@/api/pathfinding'
import { getNoFlyZones, getHeightLimitZones } from '@/api/zones'

const mapRef = ref(null)
const map = shallowRef(null)
let AMap = null

const viewMode = ref('2D')
const startInput = ref('')
const endInput = ref('')
const startPoint = ref(null)
const endPoint = ref(null)
const waypoints = ref([])

const droneSpeed = ref(15)
const safetyMargin = ref(50)
const avoidNoFly = ref(true)
const avoidHeightLimit = ref(true)
const considerWeather = ref(true)

const pickingPoint = ref(null)
const planning = ref(false)
const planResult = ref(null)

let startMarker = null
let endMarker = null
let routeLine = null
let noFlyPolygons = []
let heightLimitPolygons = []

const amapKey = import.meta.env.VITE_AMAP_KEY
const amapSecurityCode = import.meta.env.VITE_AMAP_SECURITY_CODE

onMounted(async () => {
  window._AMapSecurityConfig = { securityJsCode: amapSecurityCode }

  try {
    AMap = await AMapLoader.load({
      key: amapKey,
      version: '2.0',
      plugins: ['AMap.Scale', 'AMap.ToolBar', 'AMap.Buildings', 'AMap.GeometryUtil'],
    })

    map.value = new AMap.Map('planning-map', {
      viewMode: '3D',
      pitch: 0,
      rotation: 0,
      zoom: 12,
      center: [113.2644, 23.1291],
      mapStyle: 'amap://styles/whitesmoke',
      features: ['bg', 'road', 'building', 'point'],
      buildingAnimation: true,
      rotateEnable: true,
      pitchEnable: true,
    })

    map.value.addControl(new AMap.Scale({ position: 'LB' }))
    map.value.addControl(new AMap.ToolBar({ position: 'RT', liteStyle: true }))

    // 白模建筑
    const buildings = new AMap.Buildings({
      zooms: [14, 20],
      heightFactor: 1.5,
      wallColor: 'rgba(255, 255, 255, 0.9)',
      roofColor: 'rgba(240, 240, 245, 0.95)',
      borderColor: 'rgba(200, 200, 210, 0.6)',
      borderWeight: 1,
    })
    map.value.add(buildings)

    map.value.on('click', onMapClick)

    // 加载禁飞区和限高区
    await loadZones()
  } catch (e) {
    console.error('地图加载失败:', e)
  }
})

onUnmounted(() => {
  if (map.value) map.value.destroy()
})

// 加载禁飞区/限高区
async function loadZones() {
  try {
    const [noFlyData, heightData] = await Promise.all([getNoFlyZones(), getHeightLimitZones()])

    // 渲染禁飞区
    if (noFlyData?.features) {
      noFlyData.features.forEach((f) => {
        if (!f.geometry) return
        const coords = f.geometry.coordinates[0].map((c) => new AMap.LngLat(c[0], c[1]))
        const polygon = new AMap.Polygon({
          path: coords,
          strokeColor: '#dc2626', strokeWeight: 2, strokeOpacity: 0.8,
          fillColor: '#fca5a5', fillOpacity: 0.3,
          strokeStyle: 'dashed', strokeDasharray: [8, 4],
          cursor: 'pointer', zIndex: 50,
        })
        const name = f.properties?.name || '禁飞区'
        polygon.on('click', () => {
          new AMap.InfoWindow({
            content: `<div style="padding:8px 12px;"><b style="color:#dc2626">${name}</b><br/><span style="color:#6b7280;font-size:12px">${f.properties?.reason || ''}</span></div>`,
            offset: new AMap.Pixel(0, -10),
          }).open(map.value, polygon.getBounds().getCenter())
        })
        map.value.add(polygon)
        noFlyPolygons.push(polygon)
      })
    }

    // 渲染限高区
    if (heightData?.features) {
      heightData.features.forEach((f) => {
        if (!f.geometry) return
        const coords = f.geometry.coordinates[0].map((c) => new AMap.LngLat(c[0], c[1]))
        const polygon = new AMap.Polygon({
          path: coords,
          strokeColor: '#ea580c', strokeWeight: 2, strokeOpacity: 0.8,
          fillColor: '#fdba74', fillOpacity: 0.25,
          cursor: 'pointer', zIndex: 40,
        })
        const name = f.properties?.name || '限高区'
        const alt = f.properties?.max_altitude || 120
        polygon.on('click', () => {
          new AMap.InfoWindow({
            content: `<div style="padding:8px 12px;"><b style="color:#ea580c">${name}</b><br/><span style="color:#6b7280;font-size:12px">限高 ${alt} 米</span></div>`,
            offset: new AMap.Pixel(0, -10),
          }).open(map.value, polygon.getBounds().getCenter())
        })
        map.value.add(polygon)
        heightLimitPolygons.push(polygon)
      })
    }
  } catch (e) {
    console.error('加载区域数据失败:', e)
  }
}

// 切换 2D/3D
function switchMode(mode) {
  viewMode.value = mode
  if (!map.value) return
  if (mode === '3D') {
    map.value.setPitch(55)
    map.value.setRotation(-30)
    map.value.setZoomAndCenter(14.5, [113.2644, 23.1291])
  } else {
    map.value.setPitch(0)
    map.value.setRotation(0)
    map.value.setZoomAndCenter(12, [113.2644, 23.1291])
  }
}

function onMapClick(e) {
  if (!pickingPoint.value) return
  const lnglat = { lng: e.lnglat.getLng(), lat: e.lnglat.getLat() }

  if (pickingPoint.value === 'start') {
    startPoint.value = lnglat
    startInput.value = `${lnglat.lng.toFixed(6)}, ${lnglat.lat.toFixed(6)}`
    updateStartMarker(lnglat)
  } else if (pickingPoint.value === 'end') {
    endPoint.value = lnglat
    endInput.value = `${lnglat.lng.toFixed(6)}, ${lnglat.lat.toFixed(6)}`
    updateEndMarker(lnglat)
  }
  pickingPoint.value = null
  ElMessage.success('选点完成')
}

function pickPoint(type) {
  pickingPoint.value = pickingPoint.value === type ? null : type
  if (pickingPoint.value) ElMessage.info('请在地图上点击选择位置')
}

function parseCoords(input) {
  const parts = input.split(',').map((s) => parseFloat(s.trim()))
  return parts.length === 2 && !isNaN(parts[0]) && !isNaN(parts[1]) ? { lng: parts[0], lat: parts[1] } : null
}

function geocodeStart() { const c = parseCoords(startInput.value); if (c) { startPoint.value = c; updateStartMarker(c) } }
function geocodeEnd() { const c = parseCoords(endInput.value); if (c) { endPoint.value = c; updateEndMarker(c) } }

function updateStartMarker(pos) {
  if (!map.value || !AMap) return
  if (startMarker) map.value.remove(startMarker)
  startMarker = new AMap.Marker({
    position: [pos.lng, pos.lat],
    content: '<div style="background:#16a34a;color:#fff;padding:4px 10px;border-radius:6px;font-weight:600;font-size:12px;box-shadow:0 2px 4px rgba(0,0,0,0.15);">起点</div>',
    offset: new AMap.Pixel(-20, -15), anchor: 'center',
  })
  map.value.add(startMarker)
}

function updateEndMarker(pos) {
  if (!map.value || !AMap) return
  if (endMarker) map.value.remove(endMarker)
  endMarker = new AMap.Marker({
    position: [pos.lng, pos.lat],
    content: '<div style="background:#dc2626;color:#fff;padding:4px 10px;border-radius:6px;font-weight:600;font-size:12px;box-shadow:0 2px 4px rgba(0,0,0,0.15);">终点</div>',
    offset: new AMap.Pixel(-20, -15), anchor: 'center',
  })
  map.value.add(endMarker)
}

function addWaypoint() { waypoints.value.push({ input: '' }) }
function removeWaypoint(i) { waypoints.value.splice(i, 1) }

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
      safety_margin: safetyMargin.value,
      avoid_no_fly: avoidNoFly.value,
      avoid_height_limit: avoidHeightLimit.value,
      consider_weather: considerWeather.value,
    })
    planResult.value = result
    drawRoute(result.path)
    ElMessage.success('路径规划完成')
  } catch (e) {
    ElMessage.error('路径规划失败: ' + (e.message || '未知错误'))
  } finally { planning.value = false }
}

function drawRoute(pathPoints) {
  if (!map.value || !AMap || !pathPoints?.length) return
  if (routeLine) map.value.remove(routeLine)
  routeLine = new AMap.Polyline({
    path: pathPoints.map(p => [p.lng, p.lat]),
    strokeColor: '#2563eb', strokeWeight: 5, strokeOpacity: 0.9,
    showDir: true, lineJoin: 'round', lineCap: 'round', zIndex: 100,
  })
  map.value.add(routeLine)
  map.value.setFitView([routeLine, startMarker, endMarker].filter(Boolean))
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
#planning-map { width: 100%; height: 100%; }

/* 2D/3D 按钮 - 左上角 */
.map-controls-topleft {
  position: absolute; top: 15px; left: 15px; z-index: 100;
}
.map-controls-topleft .el-button {
  background: #ffffff !important; border-color: #d1d5db !important;
  color: #374151 !important; box-shadow: 0 1px 3px rgba(0,0,0,0.1) !important; font-size: 13px;
}
.map-controls-topleft .el-button--primary {
  background: #2563eb !important; border-color: #2563eb !important; color: #ffffff !important;
}

/* 图例 - 右下角 */
.planning-legend {
  position: absolute; bottom: 35px; right: 15px; z-index: 100;
  background: rgba(255,255,255,0.95); border: 1px solid #e5e7eb;
  border-radius: 10px; padding: 10px 14px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
}
.legend-item { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; font-size: 12px; color: #374151; }
.legend-item:last-child { margin-bottom: 0; }
.lc { width: 14px; height: 14px; border-radius: 3px; border: 2px solid; }
.ll { width: 18px; height: 3px; border-radius: 2px; }
.ld { width: 10px; height: 10px; border-radius: 50%; margin: 0 4px; }
</style>
