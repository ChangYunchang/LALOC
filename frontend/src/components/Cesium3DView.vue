<template>
  <div class="cesium-3d-wrapper">
    <div id="cesium-3d-container" ref="cesiumRef"></div>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, ref, watch, nextTick } from 'vue'
import { useMapStore } from '@/stores/map'
import { useZoneStore } from '@/stores/zones'

// 动态加载 Cesium — 仅在 3D 模式时加载，不阻塞页面
let Cesium = null
let cesiumStyleLoaded = false

async function loadCesium() {
  if (Cesium) return Cesium

  // 设置静态资源基础路径
  window.CESIUM_BASE_URL = '/cesium/'

  // 加载 CSS（仅一次）
  if (!cesiumStyleLoaded && !document.querySelector('link[data-cesium]')) {
    const link = document.createElement('link')
    link.rel = 'stylesheet'
    link.href = '/cesium/Widgets/widgets.css'
    link.setAttribute('data-cesium', '1')
    document.head.appendChild(link)
    cesiumStyleLoaded = true
  }

  // 加载 Cesium JS（仅一次）
  if (!window.Cesium) {
    await new Promise((resolve, reject) => {
      const script = document.createElement('script')
      script.src = '/cesium/Cesium.js'
      script.setAttribute('data-cesium', '1')
      script.onload = resolve
      script.onerror = () => reject(new Error('Failed to load Cesium.js'))
      document.head.appendChild(script)
    })
  }

  Cesium = window.Cesium
  return Cesium
}

const cesiumRef = ref(null)
const mapStore = useMapStore()
const zoneStore = useZoneStore()

const cesiumIonToken = import.meta.env.VITE_CESIUM_ION_TOKEN || ''

// ── Cesium 核心实例 ────────────────────────────
let viewer = null
let buildingsTileset = null
let zoneEntities = []    // 禁飞区/限高区 entity 引用
let routeEntities = {}   // { routeId: { polylines[], droneEntity, startEntity, endEntity } }
let routeAnimState = {}
let globalRafId = null
let globalLastTime = 0
let lastRoutesData = null

// ── 颜色（Cesium 加载后填充）────────────────────
let COL = { normal: null, highlight: null, phase: {}, phaseHighlight: {} }

function initColors() {
  const c = (hex) => Cesium.Color.fromCssColorString(hex)
  COL.normal = c('#10b981')
  COL.highlight = c('#f59e0b')
  COL.phase = {
    ascent: c('#22c55e'), cruise: c('#3b82f6'),
    descent: c('#f59e0b'), height_limit: c('#ef4444'),
  }
  COL.phaseHighlight = {
    ascent: c('#4ade80'), cruise: c('#60a5fa'),
    descent: c('#fbbf24'), height_limit: c('#f87171'),
  }
}

// ── SVG 无人机图标 (Data URI) ──────────────────
const DRONE_SVG = 'data:image/svg+xml,' + encodeURIComponent(
  '<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">' +
  '<circle cx="12" cy="12" r="4" fill="#10b981" stroke="#fff" stroke-width="2"/>' +
  '<line x1="4" y1="4" x2="10" y2="10" stroke="#10b981" stroke-width="2" stroke-linecap="round"/>' +
  '<line x1="20" y1="4" x2="14" y2="10" stroke="#10b981" stroke-width="2" stroke-linecap="round"/>' +
  '<line x1="4" y1="20" x2="10" y2="14" stroke="#10b981" stroke-width="2" stroke-linecap="round"/>' +
  '<line x1="20" y1="20" x2="14" y2="14" stroke="#10b981" stroke-width="2" stroke-linecap="round"/>' +
  '<circle cx="4" cy="4" r="2.5" fill="#10b981" opacity="0.8"/>' +
  '<circle cx="20" cy="4" r="2.5" fill="#10b981" opacity="0.8"/>' +
  '<circle cx="4" cy="20" r="2.5" fill="#10b981" opacity="0.8"/>' +
  '<circle cx="20" cy="20" r="2.5" fill="#10b981" opacity="0.8"/></svg>'
)

// ── 创建 Cesium Viewer ─────────────────────────
async function createViewer() {
  await loadCesium()
  initColors()
  Cesium.Ion.defaultAccessToken = cesiumIonToken
  console.log('Cesium loaded, creating viewer...')

  // 地形：尝试 ion，失败则用平面
  let terrainProvider
  if (cesiumIonToken && cesiumIonToken.length > 10) {
    try {
      terrainProvider = await Cesium.createWorldTerrainAsync()
      console.log('World Terrain loaded')
    } catch (e) {
      console.warn('World Terrain failed:', e.message)
      terrainProvider = new Cesium.EllipsoidTerrainProvider()
    }
  } else {
    terrainProvider = new Cesium.EllipsoidTerrainProvider()
  }

  viewer = new Cesium.Viewer('cesium-3d-container', {
    terrainProvider,
    // 不设 imageryProvider — 先用 Cesium 默认底图，再叠加 OSM
    // 初始视图：广州
    camera: {
      destination: Cesium.Cartesian3.fromDegrees(113.35, 23.10, 8000),
      orientation: {
        heading: Cesium.Math.toRadians(30),
        pitch: Cesium.Math.toRadians(-45),
        roll: 0,
      },
    },
    // UI 配置
    animation: false,
    timeline: false,
    baseLayerPicker: false,
    fullscreenButton: false,
    vrButton: false,
    geocoder: false,
    homeButton: false,
    sceneModePicker: false,
    navigationHelpButton: false,
    infoBox: false,
    selectionIndicator: false,
    // 渲染：先持续渲染确保加载完成，5 秒后切换为按需渲染
    requestRenderMode: false,
  })

  // 移除 Cesium logo 下方的 attribution
  viewer.cesiumWidget.creditContainer.style.display = 'none'

  // 叠加 OpenStreetMap 影像层（全球可用，无需 token）
  try {
    const osmLayer = viewer.imageryLayers.addImageryProvider(
      Cesium.createOpenStreetMapImageryProvider({ url: 'https://tile.openstreetmap.org/' })
    )
    console.log('OpenStreetMap layer added')
  } catch (e) {
    console.warn('OSM layer failed:', e.message)
  }

  // 加载完成后切换为按需渲染以节省资源
  setTimeout(() => {
    if (viewer && !viewer.isDestroyed()) {
      viewer.scene.requestRenderMode = true
      viewer.scene.maximumRenderTimeChange = Infinity
      console.log('Switched to on-demand rendering')
    }
  }, 5000)

  console.log('Viewer created, loading OSM Buildings...')

  // 加载 OSM Buildings (白模)
  try {
    buildingsTileset = await Cesium.createOsmBuildingsAsync()
    viewer.scene.primitives.add(buildingsTileset)
    buildingsTileset.style = new Cesium.Cesium3DTileStyle({
      color: "color('white', 0.9)",
      show: true,
    })
    console.log('Cesium OSM Buildings loaded')
  } catch (e) {
    console.warn('Cesium OSM Buildings load failed (may need valid ion token):', e.message)
  }

  // 存储到 store
  mapStore.setCesiumViewer(viewer)

  // 渲染区域
  renderZones()

  // 重绘航线
  if (lastRoutesData) {
    drawRoutes(lastRoutesData)
  }

  console.log('Cesium viewer ready')
}

// ── 区域渲染（禁飞区 + 限高区）─────────────────
function clearZoneEntities() {
  zoneEntities.forEach(e => viewer?.entities.remove(e))
  zoneEntities = []
}

function renderZones() {
  if (!viewer) return
  clearZoneEntities()

  // 禁飞区
  if (zoneStore.noFlyZones?.features) {
    zoneStore.noFlyZones.features.forEach((feature) => {
      if (!feature.geometry) return
      const coords = feature.geometry.coordinates[0]
      const hierarchy = Cesium.Cartesian3.fromDegreesArray(
        coords.flatMap((c) => [c[0], c[1]])
      )

      const entity = viewer.entities.add({
        polygon: {
          hierarchy,
          material: Cesium.Color.RED.withAlpha(0.3),
          outline: true,
          outlineColor: Cesium.Color.RED.withAlpha(0.8),
          outlineWidth: 2,
        },
        properties: {
          name: feature.properties?.name || '禁飞区',
          reason: feature.properties?.reason || '无',
          type: 'no-fly-zone',
        },
      })
      zoneEntities.push(entity)
    })
  }

  // 限高区
  if (zoneStore.heightLimitZones?.features) {
    zoneStore.heightLimitZones.features.forEach((feature) => {
      if (!feature.geometry) return
      const coords = feature.geometry.coordinates[0]
      const hierarchy = Cesium.Cartesian3.fromDegreesArray(
        coords.flatMap((c) => [c[0], c[1]])
      )

      const entity = viewer.entities.add({
        polygon: {
          hierarchy,
          material: Cesium.Color.ORANGE.withAlpha(0.25),
          outline: true,
          outlineColor: Cesium.Color.ORANGE.withAlpha(0.8),
          outlineWidth: 2,
        },
        properties: {
          name: feature.properties?.name || '限高区',
          maxAltitude: feature.properties?.max_altitude || 120,
          type: 'height-limit-zone',
        },
      })
      zoneEntities.push(entity)
    })
  }
}

// ── 航线渲染 ──────────────────────────────────
function clearRouteEntities() {
  Object.values(routeEntities).forEach((group) => {
    group.polylines?.forEach(p => viewer?.entities.remove(p))
    if (group.droneEntity) viewer?.entities.remove(group.droneEntity)
    if (group.startEntity) viewer?.entities.remove(group.startEntity)
    if (group.endEntity) viewer?.entities.remove(group.endEntity)
  })
  routeEntities = {}
}

function drawRoutes(routes) {
  if (!viewer) return
  lastRoutesData = routes
  stopGlobalLoop()
  clearRouteEntities()
  Object.keys(routeAnimState).forEach((k) => delete routeAnimState[k])

  routes.forEach((route) => {
    if (!route.route_line?.coordinates) return

    const coords = route.route_line.coordinates
    const altProfile = route.altitude_profile
    const polylines = []

    // 使用实际高度值
    const positions = coords.map((c, i) => {
      const alt = altProfile && altProfile[i] ? altProfile[i].alt : 100
      return Cesium.Cartesian3.fromDegrees(c[0], c[1], alt)
    })

    if (altProfile && altProfile.length === coords.length) {
      const boundaries = [0]
      for (let i = 1; i < coords.length; i++) {
        if (altProfile[i].phase !== altProfile[i - 1].phase) boundaries.push(i)
      }
      for (let b = 0; b < boundaries.length; b++) {
        const startIdx = boundaries[b]
        const endIdx = b < boundaries.length - 1 ? boundaries[b + 1] : coords.length - 1
        const phase = altProfile[startIdx].phase
        const color = COL.phase[phase] || COL.normal

        if (endIdx - startIdx >= 1) {
          const segPositions = positions.slice(startIdx, endIdx + 1)
          const isLast = b === boundaries.length - 1
          const polyline = viewer.entities.add({
            polyline: {
              positions: segPositions,
              width: 4,
              material: new Cesium.PolylineDashMaterialProperty({
                color: isLast ? color : color.withAlpha(0.8),
                dashLength: isLast ? 0 : 16, // 只有最后一段不显示虚线（表示方向）
              }),
              clampToGround: false,
            },
          })
          polylines.push(polyline)
        }
      }
    } else {
      const polyline = viewer.entities.add({
        polyline: {
          positions,
          width: 4,
          material: COL.normal,
          clampToGround: false,
        },
      })
      polylines.push(polyline)
    }

    // 起终点标记
    const startPos = Cesium.Cartesian3.fromDegrees(coords[0][0], coords[0][1], 0)
    const endPos = Cesium.Cartesian3.fromDegrees(
      coords[coords.length - 1][0],
      coords[coords.length - 1][1],
      0
    )

    const startEntity = viewer.entities.add({
      position: startPos,
      point: {
        pixelSize: 10,
        color: Cesium.Color.fromCssColorString('#10b981'),
        outlineColor: Cesium.Color.WHITE,
        outlineWidth: 1,
        heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,
      },
    })

    const endEntity = viewer.entities.add({
      position: endPos,
      point: {
        pixelSize: 10,
        color: Cesium.Color.fromCssColorString('#ef4444'),
        outlineColor: Cesium.Color.WHITE,
        outlineWidth: 1,
        heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,
      },
    })

    // 无人机
    const droneEntity = viewer.entities.add({
      position: Cesium.Cartesian3.fromDegrees(coords[0][0], coords[0][1], 100),
      billboard: {
        image: DRONE_SVG,
        width: 32,
        height: 32,
        heightReference: Cesium.HeightReference.NONE,
      },
    })

    routeEntities[route.id] = {
      polylines,
      droneEntity,
      startEntity,
      endEntity,
    }

    routeAnimState[route.id] = {
      coords,
      altProfile,
      droneEntity,
      positions,
      progress: 0,
      route,
    }
  })

  startGlobalLoop()
}

// ── 全局动画循环 ──────────────────────────────
function startGlobalLoop() {
  if (globalRafId) return
  function tick(timestamp) {
    if (!viewer || viewer.isDestroyed()) return
    if (timestamp - globalLastTime < 50) {
      globalRafId = requestAnimationFrame(tick)
      return
    }
    globalLastTime = timestamp
    const selectedId = mapStore.selectedRouteId

    Object.entries(routeAnimState).forEach(([id, state]) => {
      const rid = Number(id)
      const isSelected = rid === selectedId
      if ((!isSelected && selectedId !== null) || state._paused) return

      const speed = isSelected ? 0.0012 : 0.0003
      state.progress += speed
      if (state.progress >= 1) state.progress = 0

      const { coords, altProfile, droneEntity } = state
      const n = coords.length
      const exactIdx = state.progress * (n - 1)
      const i = Math.floor(exactIdx)
      const frac = exactIdx - i
      const j = Math.min(i + 1, n - 1)

      const lng = coords[i][0] + (coords[j][0] - coords[i][0]) * frac
      const lat = coords[i][1] + (coords[j][1] - coords[i][1]) * frac
      const alt1 = altProfile && altProfile[i] ? altProfile[i].alt : 100
      const alt2 = altProfile && altProfile[j] ? altProfile[j].alt : 100
      const alt = alt1 + (alt2 - alt1) * frac

      droneEntity.position = Cesium.Cartesian3.fromDegrees(lng, lat, alt)

      if (isSelected && viewer) {
        viewer.camera.flyTo({
          destination: Cesium.Cartesian3.fromDegrees(lng, lat, alt + 2000),
          orientation: {
            heading: viewer.camera.heading,
            pitch: Cesium.Math.toRadians(-45),
          },
          duration: 0,
        })
      }
    })

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
function highlightRoute(routeId) {
  if (!viewer) return
  mapStore.selectedRouteId = routeId

  Object.entries(routeEntities).forEach(([id, group]) => {
    const isSelected = Number(id) === routeId

    group.polylines?.forEach((p) => {
      if (isSelected) {
        p.polyline.material = new Cesium.PolylineDashMaterialProperty({
          color: COL.highlight,
          dashLength: 0,
        })
        p.polyline.width = 6
      } else {
        p.polyline.material = new Cesium.PolylineDashMaterialProperty({
          color: Cesium.Color.GRAY.withAlpha(0.4),
          dashLength: 16,
        })
        p.polyline.width = 2
      }
    })

    if (group.droneEntity?.billboard) {
      group.droneEntity.billboard.color = isSelected
        ? Cesium.Color.WHITE
        : Cesium.Color.WHITE.withAlpha(0.3)
    }
  })

  // 飞行到选中航线
  const entityGroup = routeEntities[routeId]
  if (entityGroup && entityGroup.polylines?.length) {
    viewer.flyTo(entityGroup.polylines[0], { offset: new Cesium.HeadingPitchRange(0, Cesium.Math.toRadians(-45), 5000) })
  }
}

function resetRouteHighlight() {
  if (!viewer) return
  mapStore.selectedRouteId = null

  Object.entries(routeEntities).forEach(([, group]) => {
    group.polylines?.forEach((p) => {
      p.polyline.width = 4
    })
    if (group.droneEntity?.billboard) {
      group.droneEntity.billboard.color = Cesium.Color.WHITE
    }
  })
}

function setDronePosition(routeId, progress) {
  const state = routeAnimState[routeId]
  if (!state) return
  state.progress = progress

  const { coords, altProfile, droneEntity } = state
  const n = coords.length
  const exactIdx = progress * (n - 1)
  const i = Math.floor(exactIdx)
  const frac = exactIdx - i
  const j = Math.min(i + 1, n - 1)

  const lng = coords[i][0] + (coords[j][0] - coords[i][0]) * frac
  const lat = coords[i][1] + (coords[j][1] - coords[i][1]) * frac
  const alt1 = altProfile && altProfile[i] ? altProfile[i].alt : 100
  const alt2 = altProfile && altProfile[j] ? altProfile[j].alt : 100
  const alt = alt1 + (alt2 - alt1) * frac

  droneEntity.position = Cesium.Cartesian3.fromDegrees(lng, lat, alt)
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
  await nextTick()
  if (!cesiumIonToken) {
    console.warn('Cesium ion token not set. Set VITE_CESIUM_ION_TOKEN in .env. Using default (may have limited access).')
  }
  try {
    await zoneStore.fetchAll()
    await createViewer()
  } catch (e) {
    console.error('Cesium 3D viewer init failed:', e)
  }
})

onUnmounted(() => {
  stopGlobalLoop()
  clearZoneEntities()
  clearRouteEntities()
  if (buildingsTileset) {
    viewer?.scene?.primitives?.remove(buildingsTileset)
    buildingsTileset = null
  }
  if (viewer && !viewer.isDestroyed()) {
    viewer.destroy()
    viewer = null
  }
})

watch(() => zoneStore.noFlyZones, () => { renderZones() })
watch(() => zoneStore.heightLimitZones, () => { renderZones() })

// ── 规划路径绘制 ──────────────────────────────
let planPathEntities = []

function drawPlanPath(pathPoints, altitudeProfile) {
  clearPlanPath()
  if (!viewer || !pathPoints?.length) return

  const phaseColors = {
    ascent: Cesium.Color.fromCssColorString('#22c55e'),
    cruise: Cesium.Color.fromCssColorString('#3b82f6'),
    descent: Cesium.Color.fromCssColorString('#f59e0b'),
    height_limit: Cesium.Color.fromCssColorString('#ef4444'),
    building: Cesium.Color.fromCssColorString('#a855f7'),
  }

  if (!altitudeProfile || altitudeProfile.length !== pathPoints.length) {
    const positions = pathPoints.map(p => Cesium.Cartesian3.fromDegrees(p.lng, p.lat, 100))
    const entity = viewer.entities.add({
      polyline: { positions, width: 5, material: Cesium.Color.fromCssColorString('#3b82f6'), clampToGround: false }
    })
    planPathEntities.push(entity)
  } else {
    const boundaries = [0]
    for (let i = 1; i < pathPoints.length; i++) {
      if (altitudeProfile[i].phase !== altitudeProfile[i - 1].phase) boundaries.push(i)
    }
    for (let b = 0; b < boundaries.length; b++) {
      const startIdx = boundaries[b]
      const endIdx = b < boundaries.length - 1 ? boundaries[b + 1] : pathPoints.length - 1
      const phase = altitudeProfile[startIdx].phase
      const color = phaseColors[phase] || Cesium.Color.fromCssColorString('#3b82f6')
      const segPoints = pathPoints.slice(startIdx, endIdx + 1)
      const positions = segPoints.map(p => {
        const alt = altitudeProfile[startIdx]?.alt || 100
        return Cesium.Cartesian3.fromDegrees(p.lng, p.lat, alt)
      })
      if (positions.length >= 2) {
        const entity = viewer.entities.add({
          polyline: { positions, width: 5, material: color, clampToGround: false }
        })
        planPathEntities.push(entity)
      }
    }
  }
  viewer.flyTo(planPathEntities[0], { offset: new Cesium.HeadingPitchRange(0, Cesium.Math.toRadians(-45), 3000) })
}

function clearPlanPath() {
  planPathEntities.forEach(e => viewer?.entities.remove(e))
  planPathEntities = []
}

// ── 地图点击处理 ──────────────────────────────
let clickHandler = null
let screenSpaceHandler = null

function addClickHandler(callback) {
  removeClickHandler()
  if (!viewer) return
  clickHandler = callback
  screenSpaceHandler = new Cesium.ScreenSpaceEventHandler(viewer.scene.canvas)
  screenSpaceHandler.setInputAction((movement) => {
    const cartesian = viewer.camera.pickEllipsoid(movement.position, viewer.scene.globe.ellipsoid)
    if (cartesian && clickHandler) {
      const cartographic = Cesium.Cartographic.fromCartesian(cartesian)
      const lng = Cesium.Math.toDegrees(cartographic.longitude)
      const lat = Cesium.Math.toDegrees(cartographic.latitude)
      clickHandler({ lng, lat })
    }
  }, Cesium.ScreenSpaceEventType.LEFT_CLICK)
}

function removeClickHandler() {
  if (screenSpaceHandler) {
    screenSpaceHandler.destroy()
    screenSpaceHandler = null
  }
  clickHandler = null
}

function addMarker(lng, lat, color) {
  if (!viewer) return null
  const entity = viewer.entities.add({
    position: Cesium.Cartesian3.fromDegrees(lng, lat),
    point: {
      pixelSize: 10,
      color: Cesium.Color.fromCssColorString(color),
      outlineColor: Cesium.Color.WHITE,
      outlineWidth: 1,
      heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,
    },
  })
  return entity
}

function removeMarker(entity) {
  if (entity) viewer?.entities.remove(entity)
}

function clearCustomMarkers(entities) {
  entities.forEach(e => viewer?.entities.remove(e))
}

defineExpose({
  drawRoutes,
  highlightRoute,
  resetRouteHighlight,
  setDronePosition,
  pauseDrone,
  resumeDrone,
  getViewer: () => viewer,
  getBuildingsTileset: () => buildingsTileset,
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
.cesium-3d-wrapper {
  width: 100%;
  height: 100%;
}
#cesium-3d-container {
  width: 100%;
  height: 100%;
}
</style>
