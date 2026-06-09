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
        <div class="legend-group-title">区域</div>
        <div class="legend-item"><span class="lc" style="background:rgba(252,165,165,0.5);border-color:#dc2626;"></span>禁飞区</div>
        <div class="legend-item"><span class="lc" style="background:rgba(253,186,116,0.4);border-color:#ea580c;"></span>限高区</div>
        <div class="legend-divider"></div>
        <div class="legend-group-title">飞行阶段</div>
        <div class="legend-item"><span class="ll" style="background:#22c55e;"></span>爬升段</div>
        <div class="legend-item"><span class="ll" style="background:#3b82f6;"></span>巡航段</div>
        <div class="legend-item"><span class="ll" style="background:#f59e0b;"></span>下降段</div>
        <div class="legend-item"><span class="ll" style="background:#ef4444;"></span>限高区飞行</div>
        <div class="legend-divider"></div>
        <div class="legend-item"><span class="ld" style="background:#16a34a;"></span>起点</div>
        <div class="legend-item"><span class="ld" style="background:#dc2626;"></span>终点</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import AMapLoader from '@amap/amap-jsapi-loader'
import { ElMessage } from 'element-plus'
import { planPath } from '@/api/pathfinding'
import { getNoFlyZones, getHeightLimitZones } from '@/api/zones'

const mapRef = ref(null)
let mapInstance = null
let AMap = null

// ── 中键旋转 ──────────────────────────────────
let isRotating = false
let rotStartX = 0
let rotStartY = 0
let rotStartRotation = 0
let rotStartPitch = 0

function initMiddleButtonRotation(mapObj, container) {
  container.addEventListener('mousedown', (e) => {
    if (e.button === 1) {
      e.preventDefault()
      isRotating = true
      rotStartX = e.clientX
      rotStartY = e.clientY
      rotStartRotation = mapObj.getRotation()
      rotStartPitch = mapObj.getPitch()
    }
  })
  document.addEventListener('mousemove', (e) => {
    if (!isRotating) return
    mapObj.setRotation(rotStartRotation + (e.clientX - rotStartX) * 0.3)
    mapObj.setPitch(Math.max(0, Math.min(75, rotStartPitch - (e.clientY - rotStartY) * 0.3)))
  })
  document.addEventListener('mouseup', (e) => {
    if (e.button === 1) isRotating = false
  })
  container.addEventListener('auxclick', (e) => {
    if (e.button === 1) e.preventDefault()
  })
}

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
let routeLines = []  // 分段 Polyline 数组
let noFlyPolygons = []
let heightLimitPolygons = []
let buildingsLayer = null

// 飞行阶段颜色映射
const PHASE_COLORS = {
  ascent: '#22c55e',        // 绿色 - 爬升
  cruise: '#3b82f6',        // 蓝色 - 巡航
  descent: '#f59e0b',       // 琥珀色 - 下降
  height_limit: '#ef4444',  // 红色 - 限高区飞行
}

const amapKey = import.meta.env.VITE_AMAP_KEY
const amapSecurityCode = import.meta.env.VITE_AMAP_SECURITY_CODE

// ── 保存规划状态（地图重建后恢复）──────────────────
let lastPlanPath = null
let lastAltProfile = null

// ── 创建地图实例 ──────────────────────────────────
function createMapInstance(mode) {
  const mapObj = new AMap.Map('planning-map', {
    viewMode: mode === '3D' ? '3D' : '2D',
    pitch: mode === '3D' ? 55 : 0,
    rotation: mode === '3D' ? -30 : 0,
    zoom: mode === '3D' ? 14.5 : 12,
    center: [113.2644, 23.1291],
    mapStyle: 'amap://styles/whitesmoke',
    features: mode === '3D' ? ['bg', 'road', 'building', 'point'] : ['bg', 'road', 'point'],
    buildingAnimation: false,
    rotateEnable: mode === '3D',
    pitchEnable: mode === '3D',
    jogEnable: true,
    animateEnable: true,
  })

  mapObj.addControl(new AMap.Scale({ position: 'LB' }))

  // 中键旋转
  initMiddleButtonRotation(mapObj, mapRef.value)

  // 3D 建筑图层（仅 3D 模式）
  if (mode === '3D') {
    buildingsLayer = new AMap.Buildings({
      zooms: [14, 20],
      heightFactor: 1.5,
      wallColor: 'rgba(255, 255, 255, 0.9)',
      roofColor: 'rgba(240, 240, 245, 0.95)',
      borderColor: 'rgba(200, 200, 210, 0.6)',
      borderWeight: 1,
    })
    mapObj.add(buildingsLayer)
  } else {
    buildingsLayer = null
  }

  mapObj.on('click', onMapClick)

  mapInstance = mapObj

  // 加载禁飞区/限高区
  loadZones()

  // 恢复路径（drawRoute 会同时处理起终点标记）
  if (lastPlanPath) {
    drawRoute(lastPlanPath, lastAltProfile)
  } else {
    // 没有路径时，仅显示起终点标记
    if (startPoint.value) updateStartMarker(startPoint.value)
    if (endPoint.value) updateEndMarker(endPoint.value)
  }
}

onMounted(async () => {
  window._AMapSecurityConfig = { securityJsCode: amapSecurityCode }

  try {
    AMap = await AMapLoader.load({
      key: amapKey,
      version: '2.0',
      plugins: ['AMap.Scale', 'AMap.Buildings', 'AMap.GeometryUtil'],
    })

    createMapInstance('2D')
  } catch (e) {
    console.error('地图加载失败:', e)
  }
})

onUnmounted(() => {
  if (mapInstance) mapInstance.destroy()
})

// 加载禁飞区/限高区
async function loadZones() {
  try {
    const [noFlyData, heightData] = await Promise.all([getNoFlyZones(), getHeightLimitZones()])

    // 清除旧多边形
    noFlyPolygons.forEach(p => p.setMap(null))
    heightLimitPolygons.forEach(p => p.setMap(null))
    noFlyPolygons = []
    heightLimitPolygons = []

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
          }).open(mapInstance, polygon.getBounds().getCenter())
        })
        mapInstance.add(polygon)
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
          }).open(mapInstance, polygon.getBounds().getCenter())
        })
        mapInstance.add(polygon)
        heightLimitPolygons.push(polygon)
      })
    }
  } catch (e) {
    console.error('加载区域数据失败:', e)
  }
}

// 切换 2D/3D（销毁重建地图）
function switchMode(mode) {
  if (viewMode.value === mode) return
  viewMode.value = mode

  // 销毁旧地图
  if (mapInstance) {
    mapInstance.destroy()
    mapInstance = null
  }

  // 清除引用
  startMarker = null
  endMarker = null
  routeLines.forEach(line => { try { line.setMap(null) } catch {} })
  routeLines = []
  noFlyPolygons = []
  heightLimitPolygons = []

  // 创建新地图
  createMapInstance(mode)
}

function onMapClick(e) {
  if (!pickingPoint.value || !mapInstance) return
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
  if (!mapInstance || !AMap) return
  if (startMarker) mapInstance.remove(startMarker)
  startMarker = new AMap.Marker({
    position: [pos.lng, pos.lat],
    content: '<div style="width:12px;height:12px;background:#16a34a;border-radius:50%;border:2px solid #fff;box-shadow:0 0 4px rgba(0,0,0,0.3);"></div>',
    offset: new AMap.Pixel(-6, -6), anchor: 'center',
  })
  mapInstance.add(startMarker)
}

function updateEndMarker(pos) {
  if (!mapInstance || !AMap) return
  if (endMarker) mapInstance.remove(endMarker)
  endMarker = new AMap.Marker({
    position: [pos.lng, pos.lat],
    content: '<div style="width:12px;height:12px;background:#dc2626;border-radius:50%;border:2px solid #fff;box-shadow:0 0 4px rgba(0,0,0,0.3);"></div>',
    offset: new AMap.Pixel(-6, -6), anchor: 'center',
  })
  mapInstance.add(endMarker)
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
    drawRoute(result.path, result.altitude_profile)
    ElMessage.success('路径规划完成')
  } catch (e) {
    ElMessage.error('路径规划失败: ' + (e.message || '未知错误'))
  } finally { planning.value = false }
}

function drawRoute(pathPoints, altitudeProfile) {
  if (!mapInstance || !AMap || !pathPoints?.length) return

  // 清除旧的分段线和标记
  routeLines.forEach(line => mapInstance.remove(line))
  routeLines = []
  if (startMarker) { mapInstance.remove(startMarker); startMarker = null }
  if (endMarker) { mapInstance.remove(endMarker); endMarker = null }

  // 保存路径数据（地图重建后恢复）
  lastPlanPath = pathPoints
  lastAltProfile = altitudeProfile

  // 获取路径的精确首尾坐标
  const pathStart = pathPoints[0]
  const pathEnd = pathPoints[pathPoints.length - 1]

  // 更新起止点数据
  startPoint.value = { lng: pathStart.lng, lat: pathStart.lat }
  endPoint.value = { lng: pathEnd.lng, lat: pathEnd.lat }
  startInput.value = `${pathStart.lng.toFixed(6)}, ${pathStart.lat.toFixed(6)}`
  endInput.value = `${pathEnd.lng.toFixed(6)}, ${pathEnd.lat.toFixed(6)}`

  // 创建起点标记（使用路径首点的精确坐标）
  startMarker = new AMap.Marker({
    position: new AMap.LngLat(pathStart.lng, pathStart.lat),
    content: '<div style="width:14px;height:14px;background:#16a34a;border-radius:50%;border:2px solid #fff;box-shadow:0 0 4px rgba(0,0,0,0.3);transform:translate(-50%,-50%);"></div>',
    zIndex: 200,
  })
  mapInstance.add(startMarker)

  // 创建终点标记（使用路径尾点的精确坐标）
  endMarker = new AMap.Marker({
    position: new AMap.LngLat(pathEnd.lng, pathEnd.lat),
    content: '<div style="width:14px;height:14px;background:#dc2626;border-radius:50%;border:2px solid #fff;box-shadow:0 0 4px rgba(0,0,0,0.3);transform:translate(-50%,-50%);"></div>',
    zIndex: 200,
  })
  mapInstance.add(endMarker)

  // 绘制路径
  if (!altitudeProfile || altitudeProfile.length !== pathPoints.length) {
    // 无高度剖面数据时，使用单色渲染
    const line = new AMap.Polyline({
      path: pathPoints.map(p => [p.lng, p.lat]),
      strokeColor: '#3b82f6', strokeWeight: 5, strokeOpacity: 0.9,
      showDir: true, lineJoin: 'round', lineCap: 'round', zIndex: 100,
    })
    mapInstance.add(line)
    routeLines.push(line)
  } else {
    // 按飞行阶段分段渲染
    // 找出 phase 变化的分界点
    const boundaries = [0]
    for (let i = 1; i < pathPoints.length; i++) {
      if (altitudeProfile[i].phase !== altitudeProfile[i - 1].phase) {
        boundaries.push(i)
      }
    }

    // 构建分段
    // 每段从 boundaries[b] 到 boundaries[b+1]（包含 boundaries[b+1]，共享端点）
    // 最后一段从 boundaries[last] 到 pathPoints.length - 1
    const segments = []
    for (let b = 0; b < boundaries.length; b++) {
      const startIdx = boundaries[b]
      const endIdx = b < boundaries.length - 1 ? boundaries[b + 1] : pathPoints.length - 1
      const phase = altitudeProfile[startIdx].phase
      const color = PHASE_COLORS[phase] || '#3b82f6'
      segments.push({ start: startIdx, end: endIdx, color, isLast: b === boundaries.length - 1 })
    }

    // 渲染每段 Polyline
    // 如果某段只有一个点（start === end），跳过它（它会被包含在前一段中）
    // 前一段的 endIdx 已经包含了当前段的 startIdx
    for (let s = 0; s < segments.length; s++) {
      const seg = segments[s]
      const segPoints = pathPoints.slice(seg.start, seg.end + 1).map(p => [p.lng, p.lat])

      if (segPoints.length >= 2) {
        const line = new AMap.Polyline({
          path: segPoints,
          strokeColor: seg.color,
          strokeWeight: 5,
          strokeOpacity: 0.9,
          showDir: seg.isLast,
          lineJoin: 'round',
          lineCap: 'round',
          zIndex: 100,
        })
        mapInstance.add(line)
        routeLines.push(line)
      }
    }
  }

  mapInstance.setFitView([...routeLines, startMarker, endMarker].filter(Boolean))
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
.legend-group-title { font-size: 11px; font-weight: 600; color: #6b7280; margin-bottom: 4px; }
.legend-divider { height: 1px; background: #e5e7eb; margin: 6px 0; }
.lc { width: 14px; height: 14px; border-radius: 3px; border: 2px solid; }
.ll { width: 18px; height: 3px; border-radius: 2px; }
.ld { width: 10px; height: 10px; border-radius: 50%; margin: 0 4px; }
</style>
