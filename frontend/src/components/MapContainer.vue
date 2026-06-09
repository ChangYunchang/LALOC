<template>
  <div class="map-wrapper">
    <div id="map-container" ref="mapRef"></div>

    <!-- 2D/3D 切换按钮 - 左上角 -->
    <div class="map-controls-topleft">
      <el-button-group>
        <el-button
          :type="viewMode === '2D' ? 'primary' : 'default'"
          @click="switchMode('2D')"
          size="small"
        >
          2D 平面
        </el-button>
        <el-button
          :type="viewMode === '3D' ? 'primary' : 'default'"
          @click="switchMode('3D')"
          size="small"
        >
          3D 实景
        </el-button>
      </el-button-group>
    </div>

    <!-- 图例 - 右下角 -->
    <ZoneLegend />
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, ref, watch } from 'vue'
import AMapLoader from '@amap/amap-jsapi-loader'
import { useMapStore } from '@/stores/map'
import { useZoneStore } from '@/stores/zones'
import ZoneLegend from './ZoneLegend.vue'

const mapRef = ref(null)
const mapStore = useMapStore()
const zoneStore = useZoneStore()
const viewMode = ref('2D')
let AMap = null
let sharedInfoWindow = null
let buildingsLayer = null

const amapKey = import.meta.env.VITE_AMAP_KEY
const amapSecurityCode = import.meta.env.VITE_AMAP_SECURITY_CODE

// 保存航线数据，用于地图重建后重绘
let lastRoutesData = null

// ── 中键旋转（使用 mapStore.map 获取当前地图实例）────
let isRotating = false
let startX = 0
let startY = 0
let startRotation = 0
let startPitch = 0

function initMiddleButtonRotation(container) {
  container.addEventListener('mousedown', (e) => {
    if (e.button === 1) {
      e.preventDefault()
      isRotating = true
      startX = e.clientX
      startY = e.clientY
      const m = mapStore.map
      if (m) {
        startRotation = m.getRotation()
        startPitch = m.getPitch()
      }
    }
  })
  document.addEventListener('mousemove', (e) => {
    if (!isRotating) return
    const m = mapStore.map
    if (!m) return
    m.setRotation(startRotation + (e.clientX - startX) * 0.3)
    m.setPitch(Math.max(0, Math.min(75, startPitch - (e.clientY - startY) * 0.3)))
  })
  document.addEventListener('mouseup', (e) => {
    if (e.button === 1) isRotating = false
  })
  container.addEventListener('auxclick', (e) => {
    if (e.button === 1) e.preventDefault()
  })
}

// ── 创建地图实例 ──────────────────────────────────
function createMap(mode) {
  const map = new AMap.Map('map-container', {
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

  map.addControl(new AMap.Scale({ position: 'LB' }))

  // 3D 建筑图层（仅 3D 模式下创建）
  if (mode === '3D') {
    buildingsLayer = new AMap.Buildings({
      zooms: [14, 20],
      heightFactor: 1.5,
      wallColor: 'rgba(255, 255, 255, 0.9)',
      roofColor: 'rgba(240, 240, 245, 0.95)',
      borderColor: 'rgba(200, 200, 210, 0.6)',
      borderWeight: 1,
    })
    map.add(buildingsLayer)
  } else {
    buildingsLayer = null
  }

  sharedInfoWindow = new AMap.InfoWindow({ offset: new AMap.Pixel(0, -10), autoMove: false })

  mapStore.setMap(map)
  mapStore.AMap = AMap

  // 重新渲染区域
  renderZones()

  // 重新绘制航线
  if (lastRoutesData) {
    drawRoutes(lastRoutesData)
  }
}

onMounted(async () => {
  window._AMapSecurityConfig = { securityJsCode: amapSecurityCode }
  try {
    AMap = await AMapLoader.load({
      key: amapKey,
      version: '2.0',
      plugins: ['AMap.Scale', 'AMap.Weather', 'AMap.GeometryUtil'],
    })

    await zoneStore.fetchAll()
    createMap('2D')
    initMiddleButtonRotation(mapRef.value)
  } catch (e) {
    console.error('地图加载失败:', e)
  }
})

onUnmounted(() => {
  stopGlobalLoop()
  if (mapStore.map) mapStore.map.destroy()
})

// ── 区域渲染 ──────────────────────────────────

function renderZones() {
  const map = mapStore.map
  if (!map || !AMap) return
  mapStore.clearAllOverlays()

  if (zoneStore.noFlyZones?.features) {
    zoneStore.noFlyZones.features.forEach((feature) => {
      if (!feature.geometry) return
      const coords = feature.geometry.coordinates[0].map((c) => new AMap.LngLat(c[0], c[1]))
      const polygon = new AMap.Polygon({
        path: coords,
        strokeColor: '#dc2626',
        strokeWeight: 2,
        strokeOpacity: 0.8,
        fillColor: '#fca5a5',
        fillOpacity: 0.3,
        strokeStyle: 'dashed',
        strokeDasharray: [8, 4],
        cursor: 'pointer',
        zIndex: 50,
      })
      polygon.on('mouseover', () => polygon.setOptions({ fillOpacity: 0.5 }))
      polygon.on('mouseout', () => polygon.setOptions({ fillOpacity: 0.3 }))
      const name = feature.properties?.name || '禁飞区'
      const reason = feature.properties?.reason || '无'
      polygon.on('click', () => {
        sharedInfoWindow.setContent(`<div style="padding:8px 12px;"><b style="color:#dc2626;font-size:14px;">${name}</b><br/><span style="color:#6b7280;font-size:12px;">禁飞原因: ${reason}</span></div>`)
        sharedInfoWindow.open(map, polygon.getBounds().getCenter())
      })
      map.add(polygon)
      mapStore.noFlyPolygons.push(polygon)
    })
  }

  if (zoneStore.heightLimitZones?.features) {
    zoneStore.heightLimitZones.features.forEach((feature) => {
      if (!feature.geometry) return
      const coords = feature.geometry.coordinates[0].map((c) => new AMap.LngLat(c[0], c[1]))
      const polygon = new AMap.Polygon({
        path: coords,
        strokeColor: '#ea580c',
        strokeWeight: 2,
        strokeOpacity: 0.8,
        fillColor: '#fdba74',
        fillOpacity: 0.25,
        cursor: 'pointer',
        zIndex: 40,
      })
      polygon.on('mouseover', () => polygon.setOptions({ fillOpacity: 0.45 }))
      polygon.on('mouseout', () => polygon.setOptions({ fillOpacity: 0.25 }))
      const name = feature.properties?.name || '限高区'
      const maxAlt = feature.properties?.max_altitude || 120
      polygon.on('click', () => {
        sharedInfoWindow.setContent(`<div style="padding:8px 12px;"><b style="color:#ea580c;font-size:14px;">${name}</b><br/><span style="color:#6b7280;font-size:12px;">限高: ${maxAlt} 米</span></div>`)
        sharedInfoWindow.open(map, polygon.getBounds().getCenter())
      })
      map.add(polygon)
      mapStore.heightLimitPolygons.push(polygon)
    })
  }
}

function switchMode(mode) {
  if (viewMode.value === mode) return
  viewMode.value = mode

  // 停止动画
  stopGlobalLoop()

  // 清除旧的覆盖物引用
  Object.keys(routeAnimState).forEach((k) => delete routeAnimState[k])
  mapStore.routeLines = []
  mapStore.droneMarkers = []

  // 销毁旧地图
  if (mapStore.map) {
    mapStore.map.destroy()
  }

  // 创建新地图
  createMap(mode)
}

// ── 航线渲染（轻量版：全局单循环）──────────────────

const routeAnimState = {}

// 颜色常量
const COLOR_NORMAL = '#10b981'    // 绿色 - 普通航线（无高度剖面时的默认色）
const COLOR_HIGHLIGHT = '#f59e0b' // 琥珀色 - 选中航线
const COLOR_DIM = '#d1d5db'       // 灰色 - 未选中

// 飞行阶段颜色映射
const PHASE_COLORS = {
  ascent: '#22c55e',        // 绿色 - 爬升
  cruise: '#3b82f6',        // 蓝色 - 巡航
  descent: '#f59e0b',       // 琥珀色 - 下降
  height_limit: '#ef4444',  // 红色 - 限高区飞行
}

// 高亮时的阶段颜色（更亮）
const PHASE_COLORS_HIGHLIGHT = {
  ascent: '#4ade80',
  cruise: '#60a5fa',
  descent: '#fbbf24',
  height_limit: '#f87171',
}

function drawRoutes(routes) {
  const map = mapStore.map
  if (!map || !AMap) return

  // 保存航线数据，用于地图重建后重绘
  lastRoutesData = routes

  // 清除旧数据
  stopGlobalLoop()
  Object.values(routeAnimState).forEach((s) => {
    // 清除所有分段 Polyline
    if (s.polylines) {
      s.polylines.forEach(p => p?.setMap(null))
    } else {
      s.polyline?.setMap(null)
    }
    s.droneMarker?.setMap(null)
    s.startMarker?.setMap(null)
    s.endMarker?.setMap(null)
  })
  Object.keys(routeAnimState).forEach((k) => delete routeAnimState[k])
  mapStore.routeLines = []
  mapStore.droneMarkers = []

  routes.forEach((route) => {
    if (!route.route_line?.coordinates) return

    const path = route.route_line.coordinates.map((c) => new AMap.LngLat(c[0], c[1]))
    const altProfile = route.altitude_profile

    // 航线 Polyline（分段渲染）
    const polylines = []

    if (altProfile && altProfile.length === path.length) {
      // 按飞行阶段分段渲染
      // 找出 phase 变化的分界点
      const boundaries = [0]
      for (let i = 1; i < path.length; i++) {
        if (altProfile[i].phase !== altProfile[i - 1].phase) {
          boundaries.push(i)
        }
      }

      // 构建分段
      // 每段从 boundaries[b] 到 boundaries[b+1]（包含 boundaries[b+1]，共享端点）
      // 最后一段从 boundaries[last] 到 path.length - 1
      const segments = []
      for (let b = 0; b < boundaries.length; b++) {
        const startIdx = boundaries[b]
        const endIdx = b < boundaries.length - 1 ? boundaries[b + 1] : path.length - 1
        const phase = altProfile[startIdx].phase
        const color = PHASE_COLORS[phase] || COLOR_NORMAL
        segments.push({ start: startIdx, end: endIdx, color, isLast: b === boundaries.length - 1 })
      }

      // 渲染每段 Polyline
      // 如果某段只有一个点（start === end），跳过它（它会被包含在前一段中）
      // 前一段的 endIdx 已经包含了当前段的 startIdx
      for (let s = 0; s < segments.length; s++) {
        const seg = segments[s]
        const segPoints = path.slice(seg.start, seg.end + 1)

        if (segPoints.length >= 2) {
          const polyline = new AMap.Polyline({
            path: segPoints,
            strokeColor: seg.color,
            strokeWeight: 4,
            strokeOpacity: 0.8,
            showDir: seg.isLast, // 只在最后一段显示方向箭头
            lineJoin: 'round',
            lineCap: 'round',
            zIndex: 100,
          })
          map.add(polyline)
          polylines.push(polyline)
        }
      }
    } else {
      // 无高度剖面数据时，使用单色渲染
      const polyline = new AMap.Polyline({
        path,
        strokeColor: COLOR_NORMAL,
        strokeWeight: 4,
        strokeOpacity: 0.8,
        showDir: true,
        lineJoin: 'round',
        lineCap: 'round',
        zIndex: 100,
      })
      map.add(polyline)
      polylines.push(polyline)
    }

    mapStore.routeLines.push(...polylines)

    // 起点（圆点标记）
    const startMarker = new AMap.Marker({
      position: path[0],
      content: '<div style="width:12px;height:12px;background:#10b981;border-radius:50%;border:2px solid #fff;box-shadow:0 1px 4px rgba(0,0,0,0.15);"></div>',
      offset: new AMap.Pixel(-6, -6),
      zIndex: 110,
    })
    map.add(startMarker)

    // 终点（圆点标记）
    const endMarker = new AMap.Marker({
      position: path[path.length - 1],
      content: '<div style="width:12px;height:12px;background:#ef4444;border-radius:50%;border:2px solid #fff;box-shadow:0 1px 4px rgba(0,0,0,0.15);"></div>',
      offset: new AMap.Pixel(-6, -6),
      zIndex: 110,
    })
    map.add(endMarker)

    // 无人机标记（轻量 SVG 图标）
    const droneMarker = new AMap.Marker({
      position: path[0],
      content: '<div style="width:24px;height:24px;"><svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><circle cx="12" cy="12" r="4" fill="#10b981" stroke="#fff" stroke-width="2"/><line x1="4" y1="4" x2="10" y2="10" stroke="#10b981" stroke-width="2" stroke-linecap="round"/><line x1="20" y1="4" x2="14" y2="10" stroke="#10b981" stroke-width="2" stroke-linecap="round"/><line x1="4" y1="20" x2="10" y2="14" stroke="#10b981" stroke-width="2" stroke-linecap="round"/><line x1="20" y1="20" x2="14" y2="14" stroke="#10b981" stroke-width="2" stroke-linecap="round"/><circle cx="4" cy="4" r="2.5" fill="#10b981" opacity="0.8"/><circle cx="20" cy="4" r="2.5" fill="#10b981" opacity="0.8"/><circle cx="4" cy="20" r="2.5" fill="#10b981" opacity="0.8"/><circle cx="20" cy="20" r="2.5" fill="#10b981" opacity="0.8"/></svg></div>',
      offset: new AMap.Pixel(-12, -12),
      zIndex: 120,
    })
    map.add(droneMarker)

    routeAnimState[route.id] = {
      polylines,     // 多段 Polyline 数组
      polyline: polylines[0], // 兼容旧代码（取第一段）
      droneMarker,
      startMarker,
      endMarker,
      path,
      progress: 0,
      route,
    }

    mapStore.droneMarkers.push(droneMarker)
  })

  startGlobalLoop()
}

// ── 全局单一动画循环（所有航线共享一个 rAF）──────────

let globalRafId = null
let globalLastTime = 0

function startGlobalLoop() {
  if (globalRafId) return

  function tick(timestamp) {
    // 节流：约 20fps
    if (timestamp - globalLastTime < 50) {
      globalRafId = requestAnimationFrame(tick)
      return
    }
    globalLastTime = timestamp

    const selectedId = mapStore.selectedRouteId
    let droneLng = null
    let droneLat = null

    Object.entries(routeAnimState).forEach(([id, state]) => {
      const rid = Number(id)
      const isSelected = rid === selectedId

      // 未选中航线 或 被时间轴暂停的航线：跳过
      if ((!isSelected && selectedId !== null) || state._paused) return

      const speed = isSelected ? 0.0012 : 0.0003
      state.progress += speed
      if (state.progress >= 1) state.progress = 0

      const { path, droneMarker } = state
      const exactIdx = state.progress * (path.length - 1)
      const i = Math.floor(exactIdx)
      const frac = exactIdx - i
      const p1 = path[i]
      const p2 = path[Math.min(i + 1, path.length - 1)]

      const lng = p1.getLng() + (p2.getLng() - p1.getLng()) * frac
      const lat = p1.getLat() + (p2.getLat() - p1.getLat()) * frac

      droneMarker.setPosition(new AMap.LngLat(lng, lat))
      const angle = Math.atan2(p2.getLng() - p1.getLng(), p2.getLat() - p1.getLat()) * (180 / Math.PI)
      droneMarker.setAngle(angle)

      if (isSelected) {
        droneLng = lng
        droneLat = lat
      }
    })

    // 选中航线时，地图跟踪无人机
    if (selectedId !== null && droneLng !== null) {
      const map = mapStore.map
      if (map) map.panTo(new AMap.LngLat(droneLng, droneLat), false)
    }

    globalRafId = requestAnimationFrame(tick)
  }

  globalRafId = requestAnimationFrame(tick)
}

function stopGlobalLoop() {
  if (globalRafId) {
    cancelAnimationFrame(globalRafId)
    globalRafId = null
  }
}

// ── 航线高亮 ──────────────────────────────────

function setMarkerOpacity(marker, opacity) {
  if (!marker) return
  try {
    marker.setOpacity(opacity)
  } catch {
    const el = marker.getContentDom?.() || marker.getDom?.()
    if (el) el.style.opacity = opacity
  }
}

function highlightRoute(routeId) {
  mapStore.selectedRouteId = routeId
  const map = mapStore.map
  if (!map || !AMap) return

  for (const key in routeAnimState) {
    const state = routeAnimState[key]
    const isSelected = Number(key) === routeId

    // 清除旧的高亮线
    if (state._highlightLines) {
      state._highlightLines.forEach(l => l?.setMap(null))
      state._highlightLines = null
    }

    const allPolys = state.polylines || [state.polyline].filter(Boolean)

    // 隐藏原始分段线
    allPolys.forEach(p => p.hide())

    if (isSelected) {
      // 选中：创建高亮版分段线（保持阶段颜色，增加线宽和亮度）
      const hlLines = []
      const altProfile = state.route?.altitude_profile

      if (altProfile && altProfile.length === state.path.length) {
        // 按阶段分段高亮
        // 找出 phase 变化的分界点
        const boundaries = [0]
        for (let i = 1; i < state.path.length; i++) {
          if (altProfile[i].phase !== altProfile[i - 1].phase) {
            boundaries.push(i)
          }
        }

        // 构建分段
        // 每段从 boundaries[b] 到 boundaries[b+1]（包含 boundaries[b+1]，共享端点）
        // 最后一段从 boundaries[last] 到 state.path.length - 1
        const segments = []
        for (let b = 0; b < boundaries.length; b++) {
          const startIdx = boundaries[b]
          const endIdx = b < boundaries.length - 1 ? boundaries[b + 1] : state.path.length - 1
          const phase = altProfile[startIdx].phase
          const color = PHASE_COLORS_HIGHLIGHT[phase] || COLOR_HIGHLIGHT
          segments.push({ start: startIdx, end: endIdx, color, isLast: b === boundaries.length - 1 })
        }

        // 渲染每段高亮线
        // 如果某段只有一个点（start === end），跳过它（它会被包含在前一段中）
        // 前一段的 endIdx 已经包含了当前段的 startIdx
        for (let s = 0; s < segments.length; s++) {
          const seg = segments[s]
          const segPoints = state.path.slice(seg.start, seg.end + 1)

          if (segPoints.length >= 2) {
            const hlLine = new AMap.Polyline({
              path: segPoints,
              strokeColor: seg.color,
              strokeWeight: 6,
              strokeOpacity: 1,
              showDir: seg.isLast, // 只在最后一段显示方向箭头
              lineJoin: 'round',
              lineCap: 'round',
              zIndex: 150,
            })
            map.add(hlLine)
            hlLines.push(hlLine)
          }
        }
      } else {
        // 无高度剖面，使用单色高亮
        const hlLine = new AMap.Polyline({
          path: state.path,
          strokeColor: COLOR_HIGHLIGHT,
          strokeWeight: 6,
          strokeOpacity: 1,
          showDir: true,
          lineJoin: 'round',
          lineCap: 'round',
          zIndex: 150,
        })
        map.add(hlLine)
        hlLines.push(hlLine)
      }

      state._highlightLines = hlLines

      setMarkerOpacity(state.droneMarker, 1)
      setMarkerOpacity(state.startMarker, 1)
      setMarkerOpacity(state.endMarker, 1)
    } else {
      // 未选中：降低透明度
      allPolys.forEach(p => {
        p.show()
        p.setOptions({
          strokeWeight: 3,
          strokeOpacity: 0.6,
          zIndex: 100,
        })
      })
      setMarkerOpacity(state.droneMarker, 0.3)
      setMarkerOpacity(state.startMarker, 0.4)
      setMarkerOpacity(state.endMarker, 0.4)
    }
  }

  const selectedState = routeAnimState[routeId]
  if (selectedState && map) {
    const targets = selectedState._highlightLines || [selectedState.polyline].filter(Boolean)
    map.setFitView(targets, false, [80, 80, 80, 80])
  }
}

function resetRouteHighlight() {
  mapStore.selectedRouteId = null

  for (const key in routeAnimState) {
    const state = routeAnimState[key]

    // 清除高亮线
    if (state._highlightLines) {
      state._highlightLines.forEach(l => l?.setMap(null))
      state._highlightLines = null
    }

    // 恢复原始分段线样式
    const allPolys = state.polylines || [state.polyline].filter(Boolean)
    allPolys.forEach(p => {
      p.show()
      p.setOptions({
        strokeWeight: 4,
        strokeOpacity: 0.8,
        zIndex: 100,
      })
    })
    setMarkerOpacity(state.droneMarker, 1)
    setMarkerOpacity(state.startMarker, 1)
    setMarkerOpacity(state.endMarker, 1)
  }
}

// 时间轴回放：设置无人机位置 + 跟踪地图
function setDronePosition(routeId, progress) {
  const state = routeAnimState[routeId]
  if (!state) return

  state.progress = progress
  const { path, droneMarker } = state
  const exactIdx = progress * (path.length - 1)
  const i = Math.floor(exactIdx)
  const frac = exactIdx - i
  const p1 = path[i]
  const p2 = path[Math.min(i + 1, path.length - 1)]

  const lng = p1.getLng() + (p2.getLng() - p1.getLng()) * frac
  const lat = p1.getLat() + (p2.getLat() - p1.getLat()) * frac

  droneMarker.setPosition(new AMap.LngLat(lng, lat))
  const angle = Math.atan2(p2.getLng() - p1.getLng(), p2.getLat() - p1.getLat()) * (180 / Math.PI)
  droneMarker.setAngle(angle)

  // 跟踪地图
  const map = mapStore.map
  if (map && mapStore.selectedRouteId === routeId) {
    map.panTo(new AMap.LngLat(lng, lat), false)
  }
}

function pauseDrone(routeId) {
  const state = routeAnimState[routeId]
  if (state) state._paused = true
}

function resumeDrone(routeId) {
  const state = routeAnimState[routeId]
  if (state) state._paused = false
}

defineExpose({
  drawRoutes,
  highlightRoute,
  resetRouteHighlight,
  setDronePosition,
  pauseDrone,
  resumeDrone,
})

// 区域数据监听
let lastNoFlyRef = null
let lastHeightRef = null
watch(() => zoneStore.noFlyZones, (val) => { if (val !== lastNoFlyRef) { lastNoFlyRef = val; renderZones() } })
watch(() => zoneStore.heightLimitZones, (val) => { if (val !== lastHeightRef) { lastHeightRef = val; renderZones() } })
</script>

<style scoped>
.map-wrapper {
  position: relative;
  width: 100%;
  height: 100%;
}

#map-container {
  width: 100%;
  height: 100%;
}

.map-controls-topleft {
  position: absolute;
  top: 15px;
  left: 15px;
  z-index: 100;
}

.map-controls-topleft .el-button {
  background: #ffffff !important;
  border-color: #d1d5db !important;
  color: #374151 !important;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1) !important;
  font-size: 13px;
}

.map-controls-topleft .el-button--primary {
  background: #2563eb !important;
  border-color: #2563eb !important;
  color: #ffffff !important;
}
</style>
