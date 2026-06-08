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

const amapKey = import.meta.env.VITE_AMAP_KEY
const amapSecurityCode = import.meta.env.VITE_AMAP_SECURITY_CODE

// ── 中键旋转 ──────────────────────────────────
let isRotating = false
let startX = 0
let startY = 0
let startRotation = 0
let startPitch = 0

function initMiddleButtonRotation(map, container) {
  container.addEventListener('mousedown', (e) => {
    if (e.button === 1) {
      e.preventDefault()
      isRotating = true
      startX = e.clientX
      startY = e.clientY
      startRotation = map.getRotation()
      startPitch = map.getPitch()
    }
  })
  document.addEventListener('mousemove', (e) => {
    if (!isRotating) return
    map.setRotation(startRotation + (e.clientX - startX) * 0.3)
    map.setPitch(Math.max(0, Math.min(75, startPitch - (e.clientY - startY) * 0.3)))
  })
  document.addEventListener('mouseup', (e) => {
    if (e.button === 1) isRotating = false
  })
  container.addEventListener('auxclick', (e) => {
    if (e.button === 1) e.preventDefault()
  })
}

onMounted(async () => {
  window._AMapSecurityConfig = { securityJsCode: amapSecurityCode }
  try {
    AMap = await AMapLoader.load({
      key: amapKey,
      version: '2.0',
      plugins: ['AMap.Scale', 'AMap.ToolBar', 'AMap.Weather', 'AMap.GeometryUtil'],
    })

    const map = new AMap.Map('map-container', {
      viewMode: '3D',
      pitch: 0,
      rotation: 0,
      zoom: 12,
      center: [113.2644, 23.1291],
      mapStyle: 'amap://styles/whitesmoke',
      features: ['bg', 'road', 'building', 'point'],
      buildingAnimation: false,
      rotateEnable: false,
      pitchEnable: false,
      jogEnable: true,
      animateEnable: true,
    })

    map.addControl(new AMap.Scale({ position: 'LB' }))
    map.addControl(new AMap.ToolBar({ position: 'RT', liteStyle: true }))

    const buildings = new AMap.Buildings({
      zooms: [14, 20],
      heightFactor: 1.5,
      wallColor: 'rgba(255, 255, 255, 0.9)',
      roofColor: 'rgba(240, 240, 245, 0.95)',
      borderColor: 'rgba(200, 200, 210, 0.6)',
      borderWeight: 1,
    })
    map.add(buildings)

    sharedInfoWindow = new AMap.InfoWindow({ offset: new AMap.Pixel(0, -10), autoMove: false })

    mapStore.setMap(map)
    mapStore.AMap = AMap
    initMiddleButtonRotation(map, mapRef.value)

    await zoneStore.fetchAll()
    renderZones()
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
  viewMode.value = mode
  const map = mapStore.map
  if (!map) return
  if (mode === '3D') {
    map.setPitch(55)
    map.setRotation(-30)
    map.setZoomAndCenter(14.5, [113.2644, 23.1291])
  } else {
    map.setPitch(0)
    map.setRotation(0)
    map.setZoomAndCenter(12, [113.2644, 23.1291])
  }
}

// ── 航线渲染（轻量版：全局单循环）──────────────────

const routeAnimState = {}

// 颜色常量
const COLOR_NORMAL = '#10b981'    // 绿色 - 普通航线
const COLOR_HIGHLIGHT = '#f59e0b' // 琥珀色 - 选中航线
const COLOR_DIM = '#d1d5db'       // 灰色 - 未选中

function drawRoutes(routes) {
  const map = mapStore.map
  if (!map || !AMap) return

  // 清除旧数据
  stopGlobalLoop()
  Object.values(routeAnimState).forEach((s) => {
    s.polyline?.setMap(null)
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

    // 航线 Polyline
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
    mapStore.routeLines.push(polyline)

    // 起点
    const startMarker = new AMap.Marker({
      position: path[0],
      content: '<div style="background:#10b981;color:#fff;padding:2px 8px;border-radius:4px;font-size:12px;font-weight:600;white-space:nowrap;">起</div>',
      offset: new AMap.Pixel(-10, -10),
      zIndex: 110,
    })
    map.add(startMarker)

    // 终点
    const endMarker = new AMap.Marker({
      position: path[path.length - 1],
      content: '<div style="background:#ef4444;color:#fff;padding:2px 8px;border-radius:4px;font-size:12px;font-weight:600;white-space:nowrap;">终</div>',
      offset: new AMap.Pixel(-10, -10),
      zIndex: 110,
    })
    map.add(endMarker)

    // 无人机标记（轻量 SVG 图标，无 CSS 动画）
    const droneMarker = new AMap.Marker({
      position: path[0],
      content: '<div style="width:24px;height:24px;"><svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><circle cx="12" cy="12" r="4" fill="#10b981" stroke="#fff" stroke-width="2"/><line x1="4" y1="4" x2="10" y2="10" stroke="#10b981" stroke-width="2" stroke-linecap="round"/><line x1="20" y1="4" x2="14" y2="10" stroke="#10b981" stroke-width="2" stroke-linecap="round"/><line x1="4" y1="20" x2="10" y2="14" stroke="#10b981" stroke-width="2" stroke-linecap="round"/><line x1="20" y1="20" x2="14" y2="14" stroke="#10b981" stroke-width="2" stroke-linecap="round"/><circle cx="4" cy="4" r="2.5" fill="#10b981" opacity="0.8"/><circle cx="20" cy="4" r="2.5" fill="#10b981" opacity="0.8"/><circle cx="4" cy="20" r="2.5" fill="#10b981" opacity="0.8"/><circle cx="20" cy="20" r="2.5" fill="#10b981" opacity="0.8"/></svg></div>',
      offset: new AMap.Pixel(-12, -12),
      zIndex: 120,
    })
    map.add(droneMarker)

    routeAnimState[route.id] = {
      polyline,
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

// 设置 Marker 透明度（兼容 content 自定义 HTML 的 Marker）
function setMarkerOpacity(marker, opacity) {
  if (!marker) return
  try {
    marker.setOpacity(opacity)
  } catch {
    // content 模式下 setOpacity 不可用，改为操作 DOM
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

    // 清理旧高亮线
    if (state._highlightLine) {
      state._highlightLine.setMap(null)
      state._highlightLine = null
    }

    // 隐藏原始线
    state.polyline.hide()

    if (isSelected) {
      // 选中：创建琥珀色高亮线
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
      state._highlightLine = hlLine

      setMarkerOpacity(state.droneMarker, 1)
      setMarkerOpacity(state.startMarker, 1)
      setMarkerOpacity(state.endMarker, 1)
    } else {
      state.polyline.show()
      state.polyline.setOptions({
        strokeWeight: 3,
        strokeOpacity: 0.6,
        strokeColor: COLOR_NORMAL,
        zIndex: 100,
      })
      setMarkerOpacity(state.droneMarker, 0.3)
      setMarkerOpacity(state.startMarker, 0.4)
      setMarkerOpacity(state.endMarker, 0.4)
    }
  }

  // 定位
  const selectedState = routeAnimState[routeId]
  if (selectedState && map) {
    const target = selectedState._highlightLine || selectedState.polyline
    map.setFitView([target], false, [80, 80, 80, 80])
  }
}

function resetRouteHighlight() {
  mapStore.selectedRouteId = null

  for (const key in routeAnimState) {
    const state = routeAnimState[key]

    if (state._highlightLine) {
      state._highlightLine.setMap(null)
      state._highlightLine = null
    }

    state.polyline.show()
    state.polyline.setOptions({
      strokeWeight: 4,
      strokeOpacity: 0.8,
      strokeColor: COLOR_NORMAL,
      zIndex: 100,
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
