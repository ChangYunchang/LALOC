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
import { wgs2gcj, gcj2wgs } from '@/utils/coordConvert'

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
let globalPanTick = 0  // 每 10 tick（≈500ms）才执行一次 panTo，避免地图跳动干扰操作

// ── 颜色常量 ──────────────────────────────────
const COLOR_NORMAL = '#10b981'
const COLOR_HIGHLIGHT = '#f59e0b'
const PHASE_COLORS = {
  ascent: '#22c55e',
  cruise: '#3b82f6',
  descent: '#f59e0b',
  height_limit: '#3b82f6',
  building: '#a855f7',
}
const PHASE_COLORS_HIGHLIGHT = {
  ascent: '#4ade80',
  cruise: '#60a5fa',
  descent: '#fbbf24',
  height_limit: '#60a5fa',
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

    // crs='wgs84' 的航线（规划页面保存）需转 GCJ-02；样例/API 航线默认已是 GCJ-02
    const toMapCoord = route.crs === 'wgs84'
      ? (c) => { const g = wgs2gcj(c[0], c[1]); return new AMap.LngLat(g.lng, g.lat) }
      : (c) => new AMap.LngLat(c[0], c[1])

    const path = route.route_line.coordinates.map(toMapCoord)
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
            strokeWeight: 5,
            strokeOpacity: 0.92,
            isOutline: true,
            outlineColor: 'rgba(255,255,255,0.55)',
            borderWeight: 2,
            showDir: true,
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
        strokeWeight: 5,
        strokeOpacity: 0.92,
        isOutline: true,
        outlineColor: 'rgba(255,255,255,0.55)',
        borderWeight: 2,
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
      content: '<div style="width:14px;height:14px;background:#10b981;border-radius:50%;border:2.5px solid #fff;box-shadow:0 1px 6px rgba(0,0,0,0.25);"></div>',
      offset: new AMap.Pixel(-7, -7),
      zIndex: 110,
    })
    map.add(startMarker)

    const endMarker = new AMap.Marker({
      position: path[path.length - 1],
      content: '<div style="width:14px;height:14px;background:#ef4444;border-radius:50%;border:2.5px solid #fff;box-shadow:0 1px 6px rgba(0,0,0,0.25);"></div>',
      offset: new AMap.Pixel(-7, -7),
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

    globalPanTick++
    if (selectedId !== null && droneLng !== null && globalPanTick % 10 === 0) {
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
    // 先创建地图，让用户立即看到界面；禁飞区/限高区数据异步加载，
    // 加载完成后由下方 watch 触发 renderZones() 自动绘制
    createMap()
    initMiddleButtonDrag(mapRef.value)
    zoneStore.fetchAll()
  } catch (e) {
    console.error('Amap 2D map load failed:', e)
  }
})

onUnmounted(() => {
  stopGlobalLoop()
  clearTimeout(_renderZonesTimer)
  if (mapStore.map) mapStore.map.destroy()
  mapStore.setMap(null)
})

let _renderZonesTimer = null
function _renderZonesDebounced() {
  clearTimeout(_renderZonesTimer)
  _renderZonesTimer = setTimeout(renderZones, 60)
}
watch(() => zoneStore.noFlyZones, _renderZonesDebounced)
watch(() => zoneStore.heightLimitZones, _renderZonesDebounced)
watch(() => mapStore.routeDataList, (routes) => {
  if (routes?.length && mapStore.map) {
    setTimeout(() => drawRoutes(routes), 300)
  }
}, { immediate: false })

// ── 规划路径绘制 ──────────────────────────────
let planPathLines = []

const PLAN_PHASE_COLORS = {
  ascent: '#22c55e', cruise: '#3b82f6', descent: '#f59e0b',
  height_limit: '#3b82f6', building: '#a855f7', no_fly: '#3b82f6',
}
const PLAN_PHASE_LABELS = {
  ascent: '起飞爬升', cruise: '巡航', descent: '降落下降',
  height_limit: '限高绕行', building: '建筑避让', no_fly: '禁飞区绕行',
}

function drawPlanPath(pathPoints, altitudeProfile, opts = {}) {
  clearPlanPath()
  const map = mapStore.map
  if (!map || !AMap || !pathPoints?.length) return

  // 路径点为 WGS-84，转 GCJ-02 供 AMap 渲染
  const toGcj = (p) => { const g = wgs2gcj(p.lng, p.lat); return { ...p, lng: g.lng, lat: g.lat } }
  const gcjPoints = pathPoints.map(toGcj)

  const hasProfile = altitudeProfile && altitudeProfile.length === pathPoints.length

  if (!hasProfile) {
    // fallback: 单色折线
    const line = new AMap.Polyline({
      path: gcjPoints.map(p => [p.lng, p.lat]),
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
      // 首尾段各自包含端点，确保段落首尾衔接（使用 GCJ-02 坐标）
      const segPoints = gcjPoints.slice(startIdx, endIdx + 1).map(p => [p.lng, p.lat])
      if (segPoints.length < 2) continue

      // 规避段（建筑/禁飞区）：宽光晕垫底 + 加粗虚线，醒目区别于巡航段
      const isAvoid = (phase === 'building' || phase === 'no_fly')
      if (isAvoid) {
        const halo = new AMap.Polyline({
          path: segPoints,
          strokeColor: color, strokeWeight: 18, strokeOpacity: 0.22,
          lineJoin: 'round', lineCap: 'round', zIndex: 99,
        })
        map.add(halo)
        planPathLines.push(halo)
      }
      const line = new AMap.Polyline({
        path: segPoints,
        strokeColor: color,
        strokeWeight: isAvoid ? 9 : 6,        // 整体加粗；规避段更粗
        strokeOpacity: 0.95,
        strokeStyle: isAvoid ? 'dashed' : 'solid',
        strokeDasharray: isAvoid ? [10, 6] : undefined,
        isOutline: !isAvoid,                  // 巡航段加白色描边，层次更清晰
        outlineColor: '#ffffff',
        borderWeight: isAvoid ? 0 : 1.5,
        showDir: b === boundaries.length - 2, // 最后一段显示方向箭头
        lineJoin: 'round', lineCap: 'round', zIndex: 100,
      })
      map.add(line)
      planPathLines.push(line)
    }

    // 在相位切换点添加高度标注
    const phaseChanges = boundaries.slice(1, -1)  // 去掉首尾
    for (const idx of phaseChanges) {
      const p = gcjPoints[idx]
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

  // 2D 不做路径精细化，直接上报最终路径供保存使用
  if (opts.onFinalPath) opts.onFinalPath(pathPoints, altitudeProfile)
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
    if (clickHandler) {
      // AMap 返回 GCJ-02，转换为 WGS-84 后透出，保持系统内部坐标一致
      const wgs = gcj2wgs(e.lnglat.getLng(), e.lnglat.getLat())
      clickHandler({ lng: wgs.lng, lat: wgs.lat })
    }
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
  // 接收 WGS-84，转 GCJ-02 后交给 AMap
  const gcj = wgs2gcj(lng, lat)
  const marker = new AMap.Marker({
    position: new AMap.LngLat(gcj.lng, gcj.lat),
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

// ── 绘图工具（纯 Canvas 绘制，零 DOM 标记，杜绝点击拦截）─────
//
// 核心设计：所有顶点标记使用 Polyline + lineCap:'round' + 极小偏移在
// AMap 内部 Canvas 上渲染成圆点，不创建任何 Marker DOM 节点。Polyline /
// Polygon 预览和结果全部设置 clickable:false。因此无论如何点击，地图
// click 事件都能正确触发，多边形顶点数量无上限。
//
let isDrawing = false
let drawMode = null              // 'line' | 'polygon'
let drawVertices = []            // [{lng, lat}]
let drawDotLines = []            // 顶点圆点 Polyline 列表
let drawPreview = null           // AMap.Polyline 预览线
let drawResultOverlay = null     // 完成后保留的覆盖物
let drawResultFill = null        // 多边形填充
let drawFinishCallback = null
let _drawKeyHandler = null
const DRAW_CLOSE_PX = 30         // 多边形闭合阈值（像素）
const DOT_COLOR_LINE = '#3b82f6'
const DOT_COLOR_POLY = '#8b5cf6'

function _drawClearAll() {
  // 清除顶点圆点（Polyline）
  drawDotLines.forEach(l => l.setMap(null))
  drawDotLines = []
  drawVertices = []
  // 清除预览线
  if (drawPreview) { drawPreview.setMap(null); drawPreview = null }
  // 移除事件
  const map = mapStore.map
  if (map) {
    map.off('click', _onDrawClick)
    map.off('mousemove', _onDrawMouseMove)
    map.off('rightclick', _onDrawRightClick)
  }
  if (_drawKeyHandler) {
    document.removeEventListener('keydown', _drawKeyHandler)
    _drawKeyHandler = null
  }
  isDrawing = false
  drawMode = null
  drawFinishCallback = null
}

// 用 Polyline + lineCap:'round' 在 Canvas 上绘制可见圆点（≈10px），
// 完全不使用 DOM Marker，因此绝不会拦截地图 click 事件。
function _drawVertexDots() {
  // 先清除旧圆点
  drawDotLines.forEach(l => l.setMap(null))
  drawDotLines = []

  const color = drawMode === 'line' ? DOT_COLOR_LINE : DOT_COLOR_POLY
  const map = mapStore.map
  if (!map) return

  // 每个顶点：一条极短线段（0.000002° ≈ 0.2m），
  // lineCap:'round' + strokeWeight:10 → 渲染为 10px 实心圆
  for (const v of drawVertices) {
    const dotLine = new AMap.Polyline({
      path: [
        [v.lng, v.lat],
        [v.lng + 0.000002, v.lat],   // 极小偏移，肉眼不可见
      ],
      strokeColor: color,
      strokeWeight: 10,
      strokeOpacity: 0.95,
      lineCap: 'round',
      lineJoin: 'round',
      clickable: false,
      zIndex: 130,
    })
    map.add(dotLine)
    drawDotLines.push(dotLine)
  }
}

function _drawConfirm() {
  if (drawMode === 'line' && drawVertices.length < 2) return
  if (drawMode === 'polygon' && drawVertices.length < 3) return

  const path = drawVertices.map(v => ({ lng: v.lng, lat: v.lat }))

  // 清除预览和圆点，保留结果
  if (drawPreview) { drawPreview.setMap(null); drawPreview = null }
  drawDotLines.forEach(l => l.setMap(null))
  drawDotLines = []
  if (drawResultOverlay) { drawResultOverlay.setMap(null); drawResultOverlay = null }
  if (drawResultFill) { drawResultFill.setMap(null); drawResultFill = null }

  // 绘制最终结果边框
  const points = drawVertices.map(v => new AMap.LngLat(v.lng, v.lat))
  const displayPositions = drawMode === 'polygon' ? [...points, points[0]] : points
  drawResultOverlay = new AMap.Polyline({
    path: displayPositions,
    strokeColor: drawMode === 'line' ? '#3b82f6' : '#8b5cf6',
    strokeWeight: 4,
    strokeOpacity: 0.9,
    strokeStyle: 'solid',
    clickable: false,
    zIndex: 100,
  })
  mapStore.map.add(drawResultOverlay)

  // 多边形半透明填充
  if (drawMode === 'polygon') {
    drawResultFill = new AMap.Polygon({
      path: points,
      strokeColor: '#8b5cf6',
      strokeWeight: 2,
      strokeOpacity: 0.6,
      fillColor: '#c4b5fd',
      fillOpacity: 0.25,
      clickable: false,
      zIndex: 99,
    })
    drawResultFill._isDrawResult = true
    mapStore.map.add(drawResultFill)
  }

  const cb = drawFinishCallback
  _drawClearAll()
  if (cb) cb(path)
}

function _onDrawClick(e) {
  const pos = { lng: e.lnglat.getLng(), lat: e.lnglat.getLat() }
  const map = mapStore.map

  // 多边形模式：检查是否点击在首点附近（闭合判断）
  if (drawMode === 'polygon' && drawVertices.length >= 3) {
    const first = drawVertices[0]
    const p1 = map.lngLatToContainer(new AMap.LngLat(first.lng, first.lat))
    const p2 = map.lngLatToContainer(new AMap.LngLat(pos.lng, pos.lat))
    const dist = Math.sqrt(Math.pow(p1.x - p2.x, 2) + Math.pow(p1.y - p2.y, 2))
    if (dist < DRAW_CLOSE_PX) {
      _drawConfirm()
      return
    }
  }

  // 添加顶点（仅存储坐标，用 Polyline 渲染圆点）
  drawVertices.push({ lng: pos.lng, lat: pos.lat })

  // 重绘预览线 + 顶点圆点（全部 Canvas 渲染，零 DOM）
  _drawRedrawPreview()
  _drawVertexDots()
}

function _drawRedrawPreview() {
  if (drawPreview) { drawPreview.setMap(null); drawPreview = null }
  if (drawVertices.length < 2) return

  const points = drawVertices.map(v => new AMap.LngLat(v.lng, v.lat))
  // 预览始终使用开放链（不闭合），避免闭合 Polyline 拦截后续点击事件
  // 闭合仅在用户确认（右键/Enter/点击首点）时由 _drawConfirm 处理
  const positions = points

  drawPreview = new AMap.Polyline({
    path: positions,
    strokeColor: drawMode === 'line' ? '#3b82f6' : '#8b5cf6',
    strokeWeight: 2,
    strokeOpacity: 0.6,
    strokeStyle: 'dashed',
    strokeDasharray: [8, 4],
    zIndex: 120,
    clickable: false,
  })
  mapStore.map.add(drawPreview)
}

function _onDrawMouseMove(e) {
  // 鼠标移动预览：仅做微小性能优化，不需要额外的动态线
  // （静态顶点连线已足够直观）
}

function _onDrawRightClick(e) {
  e.preventDefault?.()
  if (drawMode === 'line' && drawVertices.length >= 2) _drawConfirm()
  if (drawMode === 'polygon' && drawVertices.length >= 3) _drawConfirm()
}

function startDrawLine(onFinish) {
  const map = mapStore.map
  if (!map) return
  _drawClearAll()
  isDrawing = true
  drawMode = 'line'
  drawFinishCallback = onFinish

  map.on('click', _onDrawClick)
  map.on('rightclick', _onDrawRightClick)

  _drawKeyHandler = (e) => {
    if (e.key === 'Enter' && drawVertices.length >= 2) { e.preventDefault(); _drawConfirm() }
    if (e.key === 'Escape') { e.preventDefault(); _drawClearAll() }
  }
  document.addEventListener('keydown', _drawKeyHandler)
}

function startDrawPolygon(onFinish) {
  const map = mapStore.map
  if (!map) return
  _drawClearAll()
  isDrawing = true
  drawMode = 'polygon'
  drawFinishCallback = onFinish

  map.on('click', _onDrawClick)
  map.on('rightclick', _onDrawRightClick)

  _drawKeyHandler = (e) => {
    if (e.key === 'Enter' && drawVertices.length >= 3) { e.preventDefault(); _drawConfirm() }
    if (e.key === 'Escape') { e.preventDefault(); _drawClearAll() }
  }
  document.addEventListener('keydown', _drawKeyHandler)
}

function stopDrawing() {
  _drawClearAll()
}

function clearDrawing() {
  if (drawResultOverlay) { drawResultOverlay.setMap(null); drawResultOverlay = null }
  if (drawResultFill) { drawResultFill.setMap(null); drawResultFill = null }
  // 也清除绘制的填充多边形
  const map = mapStore.map
  if (map) {
    map.getAllOverlays?.().forEach(o => {
      if (o._isDrawResult) { o.setMap(null) }
    })
  }
}

// ── 静态背景航线（PathPlanning 用，无动画/无无人机标记） ──
let bgRouteLines = []

/**
 * Chaikin 曲线平滑：对坐标数组执行 2 次 Chaikin 迭代，消除折点尖角。
 * 输入/输出均为 AMap.LngLat 数组，首尾点保持不变（钉住端点）。
 */
function _chaikin(pts, iterations = 2) {
  let p = pts.map(q => [q.getLng(), q.getLat()])
  for (let iter = 0; iter < iterations; iter++) {
    const np = [p[0]]
    for (let i = 0; i < p.length - 1; i++) {
      np.push([p[i][0] * 0.75 + p[i + 1][0] * 0.25, p[i][1] * 0.75 + p[i + 1][1] * 0.25])
      np.push([p[i][0] * 0.25 + p[i + 1][0] * 0.75, p[i][1] * 0.25 + p[i + 1][1] * 0.75])
    }
    np.push(p[p.length - 1])
    p = np
  }
  return p.map(([lng, lat]) => new AMap.LngLat(lng, lat))
}

function drawBackgroundRoutes(routes) {
  bgRouteLines.forEach(l => l?.setMap(null))
  bgRouteLines = []
  const map = mapStore.map
  if (!map || !AMap || !routes?.length) return

  routes.forEach(route => {
    if (!route.route_line?.coordinates) return
    const rawCoords = route.route_line.coordinates
    const altProfile = route.altitude_profile
    const hasProfile = altProfile && altProfile.length === rawCoords.length

    if (hasProfile) {
      // 按相位分段，每段单独做 Chaikin 平滑后绘制
      const boundaries = [0]
      for (let i = 1; i < rawCoords.length; i++) {
        if (altProfile[i].phase !== altProfile[i - 1].phase) boundaries.push(i)
      }
      for (let b = 0; b < boundaries.length; b++) {
        const startIdx = boundaries[b]
        const endIdx = b < boundaries.length - 1 ? boundaries[b + 1] : rawCoords.length - 1
        const phase = altProfile[startIdx].phase
        const color = PHASE_COLORS[phase] || COLOR_NORMAL
        const rawSeg = rawCoords.slice(startIdx, endIdx + 1).map(c => new AMap.LngLat(c[0], c[1]))
        if (rawSeg.length < 2) continue
        const smoothSeg = rawSeg.length >= 4 ? _chaikin(rawSeg) : rawSeg
        const line = new AMap.Polyline({
          path: smoothSeg, strokeColor: color,
          strokeWeight: 3, strokeOpacity: 0.55,
          lineJoin: 'round', lineCap: 'round', zIndex: 90,
        })
        map.add(line)
        bgRouteLines.push(line)
      }
    } else {
      const rawPts = rawCoords.map(c => new AMap.LngLat(c[0], c[1]))
      const smoothPts = rawPts.length >= 4 ? _chaikin(rawPts) : rawPts
      const line = new AMap.Polyline({
        path: smoothPts, strokeColor: COLOR_NORMAL,
        strokeWeight: 3, strokeOpacity: 0.55,
        lineJoin: 'round', lineCap: 'round', zIndex: 90,
      })
      map.add(line)
      bgRouteLines.push(line)
    }
  })
}

defineExpose({
  drawRoutes,
  drawBackgroundRoutes,
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
  startDrawLine,
  startDrawPolygon,
  stopDrawing,
  clearDrawing,
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
