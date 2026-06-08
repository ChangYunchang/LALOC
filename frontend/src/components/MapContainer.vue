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
let sharedInfoWindow = null // 复用同一个 InfoWindow，避免内存泄漏

const amapKey = import.meta.env.VITE_AMAP_KEY
const amapSecurityCode = import.meta.env.VITE_AMAP_SECURITY_CODE

// ── 中键旋转状态 ──────────────────────────────────
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
    const dx = e.clientX - startX
    const dy = e.clientY - startY
    map.setRotation(startRotation + dx * 0.3)
    map.setPitch(Math.max(0, Math.min(75, startPitch - dy * 0.3)))
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
      plugins: [
        'AMap.Scale',
        'AMap.ToolBar',
        'AMap.Weather',
        'AMap.GeometryUtil',
        'AMap.MoveAnimation',
      ],
    })

    const map = new AMap.Map('map-container', {
      viewMode: '3D',
      pitch: 0,
      rotation: 0,
      zoom: 12,
      center: [113.2644, 23.1291],
      mapStyle: 'amap://styles/whitesmoke',
      features: ['bg', 'road', 'building', 'point'],
      buildingAnimation: false, // 关闭建筑动画，减少连续渲染
      rotateEnable: false,
      pitchEnable: false,
      jogEnable: true,
      animateEnable: true,
    })

    map.addControl(new AMap.Scale({ position: 'LB' }))
    map.addControl(new AMap.ToolBar({ position: 'RT', liteStyle: true }))

    // 白模建筑
    const buildings = new AMap.Buildings({
      zooms: [14, 20],
      heightFactor: 1.5,
      wallColor: 'rgba(255, 255, 255, 0.9)',
      roofColor: 'rgba(240, 240, 245, 0.95)',
      borderColor: 'rgba(200, 200, 210, 0.6)',
      borderWeight: 1,
    })
    map.add(buildings)

    // 共享 InfoWindow（复用，避免泄漏）
    sharedInfoWindow = new AMap.InfoWindow({
      offset: new AMap.Pixel(0, -10),
      autoMove: false,
    })

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
  // 清理动画
  Object.keys(routeAnimState).forEach((id) => stopDroneLoop(Number(id)))
  if (mapStore.map) mapStore.map.destroy()
})

// ── 区域渲染（优化：复用 InfoWindow）──────────────────

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
        sharedInfoWindow.setContent(
          `<div style="padding:8px 12px;">
            <b style="color:#dc2626;font-size:14px;">${name}</b><br/>
            <span style="color:#6b7280;font-size:12px;">禁飞原因: ${reason}</span>
          </div>`
        )
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
        sharedInfoWindow.setContent(
          `<div style="padding:8px 12px;">
            <b style="color:#ea580c;font-size:14px;">${name}</b><br/>
            <span style="color:#6b7280;font-size:12px;">限高: ${maxAlt} 米</span>
          </div>`
        )
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

// ── 航线渲染 ──────────────────────────────────────────

const routeAnimState = {}

function drawRoutes(routes) {
  const map = mapStore.map
  if (!map || !AMap) return

  // 清除旧航线
  Object.keys(routeAnimState).forEach((id) => stopDroneLoop(Number(id)))
  Object.values(routeAnimState).forEach((s) => {
    if (s.polyline) s.polyline.setMap(null)
    if (s.droneMarker) s.droneMarker.setMap(null)
    if (s.shadowLine) s.shadowLine.setMap(null)
    if (s.startMarker) s.startMarker.setMap(null)
    if (s.endMarker) s.endMarker.setMap(null)
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
      strokeColor: '#2563eb',
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

    // 无人机标记
    const droneMarker = new AMap.Marker({
      position: path[0],
      content: createDroneHTML(),
      offset: new AMap.Pixel(-16, -16),
      zIndex: 120,
    })
    map.add(droneMarker)

    // 已飞轨迹（只保留最近 N 个点，避免无限增长）
    const shadowLine = new AMap.Polyline({
      path: [path[0]],
      strokeColor: '#10b981',
      strokeWeight: 6,
      strokeOpacity: 0.5,
      lineJoin: 'round',
      lineCap: 'round',
      zIndex: 99,
    })
    map.add(shadowLine)

    routeAnimState[route.id] = {
      polyline,
      droneMarker,
      shadowLine,
      startMarker,
      endMarker,
      path,
      animating: false,
      progress: 0, // 0 ~ 1
      _rafId: null,
      route,
    }

    mapStore.droneMarkers.push(droneMarker)

    // 启动循环动画
    startDroneLoop(route.id)
  })
}

function createDroneHTML() {
  return `
    <div class="drone-marker">
      <div class="drone-body">
        <div class="drone-rotor r1"></div>
        <div class="drone-rotor r2"></div>
        <div class="drone-rotor r3"></div>
        <div class="drone-rotor r4"></div>
        <div class="drone-center"></div>
      </div>
      <div class="drone-shadow"></div>
    </div>
  `
}

// ── 高性能动画循环（requestAnimationFrame + 降频更新）──

const SHADOW_UPDATE_INTERVAL = 6 // 每 6 帧更新一次轨迹（约 10fps）
const TRACK_UPDATE_INTERVAL = 30 // 每 30 帧更新一次地图视角（约 2fps）

function startDroneLoop(routeId) {
  const state = routeAnimState[routeId]
  if (!state) return

  state.animating = true
  let frameCount = 0
  let lastTime = 0

  const getSpeed = () => {
    if (mapStore.selectedRouteId === routeId) return 0.0015
    return 0.0004
  }

  function animate(timestamp) {
    if (!state.animating) return

    const isSel = mapStore.selectedRouteId === routeId
    const minInterval = isSel ? 33 : 66
    if (timestamp - lastTime < minInterval) {
      state._rafId = requestAnimationFrame(animate)
      return
    }
    lastTime = timestamp
    frameCount++

    state.progress += getSpeed()
    if (state.progress >= 1) {
      state.progress = 0
      state.shadowLine.setPath([state.path[0]])
      frameCount = 0
    }

    const { path, droneMarker, shadowLine } = state
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

    // 降频更新轨迹
    if (frameCount % SHADOW_UPDATE_INTERVAL === 0) {
      const start = Math.max(0, i - 100)
      const shadowPath = path.slice(start, i + 1)
      shadowPath.push(new AMap.LngLat(lng, lat))
      shadowLine.setPath(shadowPath)
    }

    // 选中航线时，地图跟踪无人机（降频，避免抖动）
    if (isSel && frameCount % TRACK_UPDATE_INTERVAL === 0) {
      const map = mapStore.map
      if (map) map.panTo(new AMap.LngLat(lng, lat), false)
    }

    state._rafId = requestAnimationFrame(animate)
  }

  state._rafId = requestAnimationFrame(animate)
}

function stopDroneLoop(routeId) {
  const state = routeAnimState[routeId]
  if (state) {
    state.animating = false
    if (state._rafId) {
      cancelAnimationFrame(state._rafId)
      state._rafId = null
    }
  }
}

// ── 航线高亮与跟踪 ──────────────────────────────────

function highlightRoute(routeId) {
  mapStore.selectedRouteId = routeId
  const map = mapStore.map

  Object.entries(routeAnimState).forEach(([id, state]) => {
    const isSelected = Number(id) === routeId
    state.polyline.setOptions({
      strokeWeight: isSelected ? 6 : 3,
      strokeOpacity: isSelected ? 1 : 0.25,
      strokeColor: isSelected ? '#1d4ed8' : '#93c5fd',
      zIndex: isSelected ? 150 : 100,
    })
    state.droneMarker.setOpacity(isSelected ? 1 : 0.2)
    state.shadowLine.setOptions({ strokeOpacity: isSelected ? 0.5 : 0.1 })
    if (state.startMarker) state.startMarker.setOpacity(isSelected ? 1 : 0.2)
    if (state.endMarker) state.endMarker.setOpacity(isSelected ? 1 : 0.2)

    // 未选中的航线停止动画，选中的恢复
    if (isSelected) {
      if (!state.animating) startDroneLoop(routeId)
    } else {
      stopDroneLoop(Number(id))
      // 未选中的隐藏无人机
      state.droneMarker.setOpacity(0)
      state.shadowLine.setOptions({ strokeOpacity: 0 })
    }
  })

  // 自动定位到选中航线 + 跟踪无人机
  const state = routeAnimState[routeId]
  if (state && map) {
    map.setFitView([state.polyline], false, [80, 80, 80, 80])
  }
}

function resetRouteHighlight() {
  mapStore.selectedRouteId = null

  Object.entries(routeAnimState).forEach(([id, state]) => {
    state.polyline.setOptions({
      strokeWeight: 4,
      strokeOpacity: 0.8,
      strokeColor: '#2563eb',
      zIndex: 100,
    })
    state.droneMarker.setOpacity(1)
    state.shadowLine.setOptions({ strokeOpacity: 0.5 })
    if (state.startMarker) state.startMarker.setOpacity(1)
    if (state.endMarker) state.endMarker.setOpacity(1)

    // 恢复动画
    if (!state.animating) startDroneLoop(Number(id))
  })
}

function setDronePosition(routeId, progress) {
  const state = routeAnimState[routeId]
  if (!state) return

  state.progress = progress
  const { path, droneMarker, shadowLine } = state
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

  // 更新轨迹（限制长度）
  const start = Math.max(0, i - 100)
  const shadowPath = path.slice(start, i + 1)
  shadowPath.push(new AMap.LngLat(lng, lat))
  shadowLine.setPath(shadowPath)
}

function pauseDrone(routeId) {
  stopDroneLoop(routeId)
}

function resumeDrone(routeId) {
  const state = routeAnimState[routeId]
  if (state && !state.animating) startDroneLoop(routeId)
}

defineExpose({
  drawRoutes,
  highlightRoute,
  resetRouteHighlight,
  setDronePosition,
  pauseDrone,
  resumeDrone,
  startDroneLoop,
  stopDroneLoop,
})

// 区域数据变化时重新渲染（不用 deep，只比较引用）
let lastNoFlyRef = null
let lastHeightRef = null
watch(
  () => zoneStore.noFlyZones,
  (val) => {
    if (val !== lastNoFlyRef) {
      lastNoFlyRef = val
      renderZones()
    }
  }
)
watch(
  () => zoneStore.heightLimitZones,
  (val) => {
    if (val !== lastHeightRef) {
      lastHeightRef = val
      renderZones()
    }
  }
)
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

<style>
.drone-marker {
  position: relative;
  width: 32px;
  height: 32px;
}

.drone-body {
  position: relative;
  width: 32px;
  height: 32px;
}

.drone-center {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 10px;
  height: 10px;
  background: #1e40af;
  border-radius: 50%;
  border: 2px solid #fff;
  box-shadow: 0 0 8px rgba(30, 64, 175, 0.6);
  z-index: 2;
}

.drone-rotor {
  position: absolute;
  width: 10px;
  height: 10px;
  background: rgba(59, 130, 246, 0.7);
  border-radius: 50%;
  animation: rotorSpin 0.15s linear infinite;
  box-shadow: 0 0 4px rgba(59, 130, 246, 0.5);
}

.drone-rotor.r1 { top: 0; left: 0; }
.drone-rotor.r2 { top: 0; right: 0; }
.drone-rotor.r3 { bottom: 0; left: 0; }
.drone-rotor.r4 { bottom: 0; right: 0; }

.drone-shadow {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 24px;
  height: 8px;
  background: rgba(0, 0, 0, 0.15);
  border-radius: 50%;
  margin-top: 14px;
  filter: blur(2px);
}

@keyframes rotorSpin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
