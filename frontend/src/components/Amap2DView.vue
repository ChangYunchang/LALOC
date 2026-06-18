<template>
  <div class="amap-2d-wrapper">
    <div id="amap-2d-container" ref="mapRef"></div>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, ref, watch } from 'vue'
import AMapLoader from '@amap/amap-jsapi-loader'
import { useMapStore } from '@/stores/map'
import { useZoneStore } from '@/stores/zones'

const mapRef = ref(null)
const mapStore = useMapStore()
const zoneStore = useZoneStore()

let AMap = null
let sharedInfoWindow = null
let lastRoutesData = null

const amapKey = import.meta.env.VITE_AMAP_KEY
const amapSecurityCode = import.meta.env.VITE_AMAP_SECURITY_CODE

// ── 动画状态 ──────────────────────────────────
const routeAnimState = {}
let globalRafId = null
let globalLastTime = 0

// ── 颜色常量 ──────────────────────────────────
const COLOR_NORMAL = '#10b981'
const COLOR_HIGHLIGHT = '#f59e0b'
const PHASE_COLORS = {
  ascent: '#22c55e',
  cruise: '#3b82f6',
  descent: '#f59e0b',
  height_limit: '#ef4444',
  building: '#a855f7',
}
const PHASE_COLORS_HIGHLIGHT = {
  ascent: '#4ade80',
  cruise: '#60a5fa',
  descent: '#fbbf24',
  height_limit: '#f87171',
  building: '#c084fc',
}

// ── 中键拖拽 ──────────────────────────────────
let isDragging = false
let dragStartX = 0
let dragStartY = 0

function initMiddleButtonDrag(container) {
  container.addEventListener('mousedown', (e) => {
    if (e.button === 1) {
      e.preventDefault()
      isDragging = true
      dragStartX = e.clientX
      dragStartY = e.clientY
    }
  })
  document.addEventListener('mousemove', (e) => {
    if (!isDragging) return
    const m = mapStore.map
    if (!m) return
    const dx = e.clientX - dragStartX
    const dy = e.clientY - dragStartY
    dragStartX = e.clientX
    dragStartY = e.clientY
    m.panBy(-dx, -dy)
  })
  document.addEventListener('mouseup', () => { isDragging = false })
  container.addEventListener('auxclick', (e) => {
    if (e.button === 1) e.preventDefault()
  })
}

// ── 创建 Amap 2D 地图 ────────────────────────
function createMap() {
  const map = new AMap.Map('amap-2d-container', {
    viewMode: '2D',
    zoom: 12,
    center: [113.2644, 23.1291],
    mapStyle: 'amap://styles/whitesmoke',
    features: ['bg', 'road', 'point'],
    jogEnable: true,
    animateEnable: true,
  })

  map.addControl(new AMap.Scale({ position: 'LB' }))
  sharedInfoWindow = new AMap.InfoWindow({ offset: new AMap.Pixel(0, -10), autoMove: false })

  mapStore.setMap(map)
  mapStore.AMap = AMap

  renderZones()

  if (lastRoutesData) {
    drawRoutes(lastRoutesData)
  }
}

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

// ── 航线渲染 ──────────────────────────────────
function drawRoutes(routes) {
  const map = mapStore.map
  if (!map || !AMap) return

  lastRoutesData = routes
  stopGlobalLoop()
  Object.values(routeAnimState).forEach((s) => {
    if (s.polylines) s.polylines.forEach(p => p?.setMap(null))
    else s.polyline?.setMap(null)
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
    const polylines = []

    if (altProfile && altProfile.length === path.length) {
      const boundaries = [0]
      for (let i = 1; i < path.length; i++) {
        if (altProfile[i].phase !== altProfile[i - 1].phase) boundaries.push(i)
      }
      const segments = []
      for (let b = 0; b < boundaries.length; b++) {
        const startIdx = boundaries[b]
        const endIdx = b < boundaries.length - 1 ? boundaries[b + 1] : path.length - 1
        const phase = altProfile[startIdx].phase
        const color = PHASE_COLORS[phase] || COLOR_NORMAL
        segments.push({ start: startIdx, end: endIdx, color, isLast: b === boundaries.length - 1 })
      }
      for (let s = 0; s < segments.length; s++) {
        const seg = segments[s]
        const segPoints = path.slice(seg.start, seg.end + 1)
        if (segPoints.length >= 2) {
          const polyline = new AMap.Polyline({
            path: segPoints,
            strokeColor: seg.color,
            strokeWeight: 4,
            strokeOpacity: 0.8,
            showDir: seg.isLast,
            lineJoin: 'round',
            lineCap: 'round',
            zIndex: 100,
          })
          map.add(polyline)
          polylines.push(polyline)
        }
      }
    } else {
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

    const startMarker = new AMap.Marker({
      position: path[0],
      content: '<div style="width:12px;height:12px;background:#10b981;border-radius:50%;border:2px solid #fff;box-shadow:0 1px 4px rgba(0,0,0,0.15);"></div>',
      offset: new AMap.Pixel(-6, -6),
      zIndex: 110,
    })
    map.add(startMarker)

    const endMarker = new AMap.Marker({
      position: path[path.length - 1],
      content: '<div style="width:12px;height:12px;background:#ef4444;border-radius:50%;border:2px solid #fff;box-shadow:0 1px 4px rgba(0,0,0,0.15);"></div>',
      offset: new AMap.Pixel(-6, -6),
      zIndex: 110,
    })
    map.add(endMarker)

    const droneMarker = new AMap.Marker({
      position: path[0],
      content: '<div style="width:24px;height:24px;"><svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><circle cx="12" cy="12" r="4" fill="#10b981" stroke="#fff" stroke-width="2"/><line x1="4" y1="4" x2="10" y2="10" stroke="#10b981" stroke-width="2" stroke-linecap="round"/><line x1="20" y1="4" x2="14" y2="10" stroke="#10b981" stroke-width="2" stroke-linecap="round"/><line x1="4" y1="20" x2="10" y2="14" stroke="#10b981" stroke-width="2" stroke-linecap="round"/><line x1="20" y1="20" x2="14" y2="14" stroke="#10b981" stroke-width="2" stroke-linecap="round"/><circle cx="4" cy="4" r="2.5" fill="#10b981" opacity="0.8"/><circle cx="20" cy="4" r="2.5" fill="#10b981" opacity="0.8"/><circle cx="4" cy="20" r="2.5" fill="#10b981" opacity="0.8"/><circle cx="20" cy="20" r="2.5" fill="#10b981" opacity="0.8"/></svg></div>',
      offset: new AMap.Pixel(-12, -12),
      zIndex: 120,
    })
    map.add(droneMarker)

    routeAnimState[route.id] = {
      polylines,
      polyline: polylines[0],
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

// ── 全局动画循环 ──────────────────────────────
function startGlobalLoop() {
  if (globalRafId) return
  function tick(timestamp) {
    if (timestamp - globalLastTime < 50) {
      globalRafId = requestAnimationFrame(tick)
      return
    }
    globalLastTime = timestamp
    const selectedId = mapStore.selectedRouteId
    let droneLng = null, droneLat = null

    Object.entries(routeAnimState).forEach(([id, state]) => {
      const rid = Number(id)
      const isSelected = rid === selectedId
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

      if (isSelected) { droneLng = lng; droneLat = lat }
    })

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
  try { marker.setOpacity(opacity) } catch {
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

    if (state._highlightLines) {
      state._highlightLines.forEach(l => l?.setMap(null))
      state._highlightLines = null
    }

    const allPolys = state.polylines || [state.polyline].filter(Boolean)
    allPolys.forEach(p => p.hide())

    if (isSelected) {
      const hlLines = []
      const altProfile = state.route?.altitude_profile

      if (altProfile && altProfile.length === state.path.length) {
        const boundaries = [0]
        for (let i = 1; i < state.path.length; i++) {
          if (altProfile[i].phase !== altProfile[i - 1].phase) boundaries.push(i)
        }
        const segments = []
        for (let b = 0; b < boundaries.length; b++) {
          const startIdx = boundaries[b]
          const endIdx = b < boundaries.length - 1 ? boundaries[b + 1] : state.path.length - 1
          const phase = altProfile[startIdx].phase
          const color = PHASE_COLORS_HIGHLIGHT[phase] || COLOR_HIGHLIGHT
          segments.push({ start: startIdx, end: endIdx, color, isLast: b === boundaries.length - 1 })
        }
        for (let s = 0; s < segments.length; s++) {
          const seg = segments[s]
          const segPoints = state.path.slice(seg.start, seg.end + 1)
          if (segPoints.length >= 2) {
            const hlLine = new AMap.Polyline({
              path: segPoints,
              strokeColor: seg.color,
              strokeWeight: 6,
              strokeOpacity: 1,
              showDir: seg.isLast,
              lineJoin: 'round',
              lineCap: 'round',
              zIndex: 150,
            })
            map.add(hlLine)
            hlLines.push(hlLine)
          }
        }
      } else {
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
      allPolys.forEach(p => {
        p.show()
        p.setOptions({ strokeWeight: 3, strokeOpacity: 0.6, zIndex: 100 })
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
    if (state._highlightLines) {
      state._highlightLines.forEach(l => l?.setMap(null))
      state._highlightLines = null
    }
    const allPolys = state.polylines || [state.polyline].filter(Boolean)
    allPolys.forEach(p => {
      p.show()
      p.setOptions({ strokeWeight: 4, strokeOpacity: 0.8, zIndex: 100 })
    })
    setMarkerOpacity(state.droneMarker, 1)
    setMarkerOpacity(state.startMarker, 1)
    setMarkerOpacity(state.endMarker, 1)
  }
}

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

// ── 生命周期 ──────────────────────────────────
onMounted(async () => {
  window._AMapSecurityConfig = { securityJsCode: amapSecurityCode }
  try {
    AMap = await AMapLoader.load({
      key: amapKey,
      version: '2.0',
      plugins: ['AMap.Scale', 'AMap.Weather', 'AMap.GeometryUtil'],
    })
    await zoneStore.fetchAll()
    createMap()
    initMiddleButtonDrag(mapRef.value)
  } catch (e) {
    console.error('Amap 2D map load failed:', e)
  }
})

onUnmounted(() => {
  stopGlobalLoop()
  if (mapStore.map) mapStore.map.destroy()
  mapStore.setMap(null)
})

watch(() => zoneStore.noFlyZones, () => { renderZones() })
watch(() => zoneStore.heightLimitZones, () => { renderZones() })
watch(() => mapStore.routeDataList, (routes) => {
  if (routes?.length && mapStore.map) {
    setTimeout(() => drawRoutes(routes), 300)
  }
}, { immediate: false })

// ── 规划路径绘制 ──────────────────────────────
let planPathLines = []

const PLAN_PHASE_COLORS = {
  ascent: '#22c55e', cruise: '#3b82f6', descent: '#f59e0b',
  height_limit: '#ef4444', building: '#a855f7', no_fly: '#ef4444',
}
const PLAN_PHASE_LABELS = {
  ascent: '起飞爬升', cruise: '巡航', descent: '降落下降',
  height_limit: '限高绕行', building: '建筑避让', no_fly: '禁飞区绕行',
}

function drawPlanPath(pathPoints, altitudeProfile) {
  clearPlanPath()
  const map = mapStore.map
  if (!map || !AMap || !pathPoints?.length) return

  const hasProfile = altitudeProfile && altitudeProfile.length === pathPoints.length

  if (!hasProfile) {
    // fallback: 单色折线
    const line = new AMap.Polyline({
      path: pathPoints.map(p => [p.lng, p.lat]),
      strokeColor: '#3b82f6', strokeWeight: 5, strokeOpacity: 0.9,
      showDir: true, lineJoin: 'round', lineCap: 'round', zIndex: 100,
    })
    map.add(line)
    planPathLines.push(line)
  } else {
    // 按相位分段绘制，每段对应不同颜色
    const boundaries = [0]
    for (let i = 1; i < pathPoints.length; i++) {
      if (altitudeProfile[i].phase !== altitudeProfile[i - 1].phase) boundaries.push(i)
    }
    boundaries.push(pathPoints.length - 1)  // 确保末尾段始终被绘制

    for (let b = 0; b < boundaries.length - 1; b++) {
      const startIdx = boundaries[b]
      const endIdx   = boundaries[b + 1]
      const phase    = altitudeProfile[startIdx].phase
      const color    = PLAN_PHASE_COLORS[phase] || '#3b82f6'
      // 首尾段各自包含端点，确保段落首尾衔接
      const segPoints = pathPoints.slice(startIdx, endIdx + 1).map(p => [p.lng, p.lat])
      if (segPoints.length < 2) continue

      // 避让段（建筑/禁飞区）加虚线描边，更加醒目
      const isBuilding = (phase === 'building' || phase === 'no_fly')
      const line = new AMap.Polyline({
        path: segPoints,
        strokeColor: color,
        strokeWeight: isBuilding ? 7 : 5,
        strokeOpacity: 0.92,
        strokeStyle: isBuilding ? 'dashed' : 'solid',
        strokeDasharray: isBuilding ? [8, 4] : undefined,
        showDir: b === boundaries.length - 2,  // 最后一段显示方向箭头
        lineJoin: 'round', lineCap: 'round', zIndex: 100,
      })
      map.add(line)
      planPathLines.push(line)
    }

    // 在相位切换点添加高度标注
    const phaseChanges = boundaries.slice(1, -1)  // 去掉首尾
    for (const idx of phaseChanges) {
      const p = pathPoints[idx]
      const alt = altitudeProfile[idx]?.alt
      if (!alt) continue
      const label = new AMap.Text({
        text: `${alt}m`,
        position: new AMap.LngLat(p.lng, p.lat),
        offset: new AMap.Pixel(0, -18),
        style: {
          'background-color': 'rgba(255,255,255,0.9)',
          'border': '1px solid #d1d5db',
          'border-radius': '4px',
          'padding': '1px 5px',
          'font-size': '11px',
          'color': '#374151',
          'white-space': 'nowrap',
        },
        zIndex: 110,
      })
      map.add(label)
      planPathLines.push(label)
    }
  }

  if (planPathLines.length > 0) {
    map.setFitView(planPathLines.filter(l => l instanceof AMap.Polyline), false, [80, 80, 80, 80])
  }
}

function clearPlanPath() {
  planPathLines.forEach(l => l?.setMap(null))
  planPathLines = []
}

// ── 地图点击处理 ──────────────────────────────
let clickHandler = null

function addClickHandler(callback) {
  removeClickHandler()
  const map = mapStore.map
  if (!map) return
  clickHandler = callback
  map.on('click', (e) => {
    if (clickHandler) clickHandler({ lng: e.lnglat.getLng(), lat: e.lnglat.getLat() })
  })
}

function removeClickHandler() {
  const map = mapStore.map
  if (map && clickHandler) {
    map.off('click')
  }
  clickHandler = null
}

function addMarker(lng, lat, color) {
  const map = mapStore.map
  if (!map || !AMap) return null
  const marker = new AMap.Marker({
    position: new AMap.LngLat(lng, lat),
    content: `<div style="width:12px;height:12px;background:${color};border-radius:50%;border:2px solid #fff;box-shadow:0 1px 4px rgba(0,0,0,0.2);"></div>`,
    offset: new AMap.Pixel(-6, -6),
    zIndex: 130,
  })
  map.add(marker)
  return marker
}

function removeMarker(marker) {
  if (marker) marker.setMap(null)
}

function clearCustomMarkers(markerList) {
  markerList.forEach(m => m?.setMap(null))
}

defineExpose({
  drawRoutes,
  highlightRoute,
  resetRouteHighlight,
  setDronePosition,
  pauseDrone,
  resumeDrone,
  getMap: () => mapStore.map,
  addClickHandler,
  removeClickHandler,
  addMarker,
  removeMarker,
  clearCustomMarkers,
  drawPlanPath,
  clearPlanPath,
})
</script>

<style scoped>
.amap-2d-wrapper {
  width: 100%;
  height: 100%;
}
#amap-2d-container {
  width: 100%;
  height: 100%;
}
</style>
