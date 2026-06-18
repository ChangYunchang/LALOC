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

  window.CESIUM_BASE_URL = '/cesium/'

  if (!cesiumStyleLoaded && !document.querySelector('link[data-cesium]')) {
    const link = document.createElement('link')
    link.rel = 'stylesheet'
    link.href = '/cesium/Widgets/widgets.css'
    link.setAttribute('data-cesium', '1')
    document.head.appendChild(link)
    cesiumStyleLoaded = true
  }

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
let zoneEntities = []
let routeEntities = {}
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
    building: c('#a855f7'),
  }
  COL.phaseHighlight = {
    ascent: c('#4ade80'), cruise: c('#60a5fa'),
    descent: c('#fbbf24'), height_limit: c('#f87171'),
    building: c('#c084fc'),
  }
}

// ── 创建 Cesium Viewer ─────────────────────────
async function createViewer() {
  await loadCesium()
  initColors()
  Cesium.Ion.defaultAccessToken = cesiumIonToken
  console.log('Cesium loaded, creating viewer...')

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
    camera: {
      destination: Cesium.Cartesian3.fromDegrees(113.35, 23.10, 8000),
      orientation: {
        heading: Cesium.Math.toRadians(30),
        pitch: Cesium.Math.toRadians(-45),
        roll: 0,
      },
    },
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
    requestRenderMode: false,
  })

  viewer.cesiumWidget.creditContainer.style.display = 'none'

  try {
    viewer.imageryLayers.addImageryProvider(
      Cesium.createOpenStreetMapImageryProvider({ url: 'https://tile.openstreetmap.org/' })
    )
    console.log('OpenStreetMap layer added')
  } catch (e) {
    console.warn('OSM layer failed:', e.message)
  }

  setTimeout(() => {
    if (viewer && !viewer.isDestroyed()) {
      viewer.scene.requestRenderMode = true
      viewer.scene.maximumRenderTimeChange = Infinity
      console.log('Switched to on-demand rendering')
    }
  }, 5000)

  console.log('Viewer created, loading OSM Buildings...')

  try {
    buildingsTileset = await Cesium.createOsmBuildingsAsync()
    viewer.scene.primitives.add(buildingsTileset)
    buildingsTileset.style = new Cesium.Cesium3DTileStyle({
      color: "color('white', 0.9)",
      show: true,
    })
    console.log('Cesium OSM Buildings loaded')

    const buildingClickHandler = new Cesium.ScreenSpaceEventHandler(viewer.scene.canvas)
    buildingClickHandler.setInputAction((movement) => {
      const picked = viewer.scene.pick(movement.position)
      if (Cesium.defined(picked) && picked instanceof Cesium.Cesium3DTileFeature) {
        const props = {}
        try {
          const names = picked.getPropertyNames()
          names.forEach(n => { try { props[n] = picked.getProperty(n) } catch {} })
        } catch {}
        const osmId = props.osm_id || props['@id'] || '-'
        const buildingHeight = props.height || null
        const levels = props['building:levels'] || props.levels || null
        const name = props.name || `建筑 #${osmId}`
        let heightStr = '未知'
        if (buildingHeight) heightStr = `${buildingHeight}m`
        else if (levels) heightStr = `~${levels * 3}m (${levels}层)`
        const cartesian = viewer.scene.pickPosition(movement.position)
        if (cartesian) {
          viewer.entities.add({
            position: cartesian,
            label: {
              text: `🏢 ${name}`,
              font: '13px sans-serif',
              fillColor: Cesium.Color.WHITE,
              outlineColor: Cesium.Color.fromCssColorString('#1f2937'),
              outlineWidth: 3,
              style: Cesium.LabelStyle.FILL_AND_OUTLINE,
              verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
              pixelOffset: new Cesium.Cartesian2(0, -20),
              disableDepthTestDistance: Number.POSITIVE_INFINITY,
            },
          })
        }
      }
    }, Cesium.ScreenSpaceEventType.LEFT_CLICK)
  } catch (e) {
    console.warn('Cesium OSM Buildings load failed:', e.message)
  }

  mapStore.setCesiumViewer(viewer)
  renderZones()

  const storedRoutes = mapStore.routeDataList
  if (storedRoutes?.length) {
    drawRoutes(storedRoutes)
  } else if (lastRoutesData) {
    drawRoutes(lastRoutesData)
  }

  setTimeout(() => {
    if (viewer && !viewer.isDestroyed() && !viewer._userInteracted) {
      viewer.camera.flyTo({
        destination: Cesium.Cartesian3.fromDegrees(113.35, 23.10, 8000),
        orientation: { heading: Cesium.Math.toRadians(30), pitch: Cesium.Math.toRadians(-45) },
        duration: 1.5,
      })
      viewer._userInteracted = true
    }
  }, 2000)

  viewer.camera.changed.addEventListener(() => {
    if (viewer) viewer._userInteracted = true
  })

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

  if (zoneStore.noFlyZones?.features) {
    zoneStore.noFlyZones.features.forEach((feature) => {
      if (!feature.geometry) return
      const coords = feature.geometry.coordinates[0]
      const hierarchy = Cesium.Cartesian3.fromDegreesArray(coords.flatMap((c) => [c[0], c[1]]))
      const entity = viewer.entities.add({
        polygon: {
          hierarchy,
          material: Cesium.Color.RED.withAlpha(0.3),
          outline: true, outlineColor: Cesium.Color.RED.withAlpha(0.8), outlineWidth: 2,
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

  if (zoneStore.heightLimitZones?.features) {
    zoneStore.heightLimitZones.features.forEach((feature) => {
      if (!feature.geometry) return
      const coords = feature.geometry.coordinates[0]
      const hierarchy = Cesium.Cartesian3.fromDegreesArray(coords.flatMap((c) => [c[0], c[1]]))
      const entity = viewer.entities.add({
        polygon: {
          hierarchy,
          material: Cesium.Color.ORANGE.withAlpha(0.25),
          outline: true, outlineColor: Cesium.Color.ORANGE.withAlpha(0.8), outlineWidth: 2,
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

// Catmull-Rom 样条平滑航线
// - 将折线段变为弧线，消除 45° 折角视觉
// - 自动生成符合无人机物理的起降弧（sin 缓入缓出）
// - 每段插值 SAMPLES 个点，密集采样为后续建筑高度检测提供基础
function generateSmoothCurvePositions(coords, altProfile) {
  const SAMPLES = 12       // 每段采样点数
  const CRUISE_ALT = 180   // 无 altProfile 时的巡航高度(m)
  const n = coords.length
  if (n < 2) return coords.map((c, i) =>
    Cesium.Cartesian3.fromDegrees(c[0], c[1], altProfile?.[i]?.alt ?? CRUISE_ALT))

  // 构建控制点：有 altProfile 直接用，无则生成正弦起降弧
  const ctrlPts = coords.map((c, i) => {
    let alt
    if (altProfile && altProfile[i]?.alt != null) {
      alt = altProfile[i].alt
    } else {
      const t = i / (n - 1)
      if (t < 0.18) {
        // 起飞段：sin 缓入，15m → 巡航高度
        alt = 15 + (CRUISE_ALT - 15) * Math.sin((t / 0.18) * (Math.PI / 2))
      } else if (t > 0.82) {
        // 降落段：sin 缓出，巡航高度 → 15m
        alt = 15 + (CRUISE_ALT - 15) * Math.sin(((1 - t) / 0.18) * (Math.PI / 2))
      } else {
        alt = CRUISE_ALT
      }
    }
    return Cesium.Cartesian3.fromDegrees(c[0], c[1], Math.max(alt, 15))
  })

  // Cesium 内置 Catmull-Rom 样条（经过所有控制点，切线自动计算）
  const times = coords.map((_, i) => i)
  const spline = new Cesium.CatmullRomSpline({ times, points: ctrlPts })

  const result = []
  for (let i = 0; i < n - 1; i++) {
    for (let k = 0; k < SAMPLES; k++) {
      result.push(spline.evaluate(i + k / SAMPLES))
    }
  }
  result.push(ctrlPts[n - 1])
  return result
}

// 将一组 Cartesian3 路径点（平滑曲线上的密集采样）整体抬升至建筑物和地形上方
// 在密集采样点上采样，从根本上消除路段中间穿模
async function liftCurvedPositions(positions, clearance = 80) {
  const MIN_AGL = 160  // 城市上空保底离地高度（m），可覆盖广州大多数建筑

  const cartos = positions.map(pos => Cesium.Cartographic.fromCartesian(pos))

  // 1. 地形高度采样
  let terrainH = cartos.map(() => 0)
  try {
    const tp = viewer.terrainProvider
    if (tp && !(tp instanceof Cesium.EllipsoidTerrainProvider)) {
      const copy = cartos.map(c => new Cesium.Cartographic(c.longitude, c.latitude))
      const sampled = await Cesium.sampleTerrainMostDetailed(tp, copy)
      terrainH = sampled.map(c => c.height || 0)
    }
  } catch {}

  // 2. 建筑白模高度采样（已加载视口内建筑块才有结果）
  let buildH = cartos.map(() => 0)
  try {
    const copy = cartos.map(c => new Cesium.Cartographic(c.longitude, c.latitude))
    const result = await viewer.scene.sampleHeightMostDetailed(copy)
    buildH = result.map(c => (c.height > 0 ? c.height : 0))
  } catch {}

  // 3. 逐点抬升：max(样条原高, 建筑顶+净空, 地形+MIN_AGL)
  return positions.map((pos, i) => {
    const c = cartos[i]
    const origAlt = c.height
    const finalAlt = Math.max(origAlt, buildH[i] + clearance, terrainH[i] + MIN_AGL)
    return Cesium.Cartesian3.fromDegrees(
      Cesium.Math.toDegrees(c.longitude),
      Cesium.Math.toDegrees(c.latitude),
      finalAlt,
    )
  })
}

// Canvas 绘制无人机图标（十字机臂 + 四旋翼），中心锚点精确对齐实体位置
function makeDroneCanvas(color = '#f59e0b') {
  const s = 40
  const cv = document.createElement('canvas')
  cv.width = s; cv.height = s
  const ctx = cv.getContext('2d')
  const cx = s / 2, cy = s / 2
  ctx.strokeStyle = color; ctx.lineWidth = 2.5; ctx.lineCap = 'round'
  for (const a of [45, 135, 225, 315]) {
    const r = a * Math.PI / 180
    ctx.beginPath(); ctx.moveTo(cx, cy)
    ctx.lineTo(cx + 13 * Math.cos(r), cy + 13 * Math.sin(r))
    ctx.stroke()
  }
  ctx.fillStyle = color
  for (const a of [45, 135, 225, 315]) {
    const r = a * Math.PI / 180
    ctx.beginPath()
    ctx.arc(cx + 13 * Math.cos(r), cy + 13 * Math.sin(r), 4, 0, Math.PI * 2)
    ctx.fill()
  }
  ctx.fillStyle = '#ffffff'
  ctx.beginPath(); ctx.arc(cx, cy, 5, 0, Math.PI * 2); ctx.fill()
  ctx.strokeStyle = color; ctx.lineWidth = 1.5
  ctx.beginPath(); ctx.arc(cx, cy, 5, 0, Math.PI * 2); ctx.stroke()
  return cv
}

function drawRoutes(routes) {
  if (!viewer) return
  lastRoutesData = routes
  stopGlobalLoop()
  clearRouteEntities()
  Object.keys(routeAnimState).forEach((k) => delete routeAnimState[k])

  const droneNormalCanvas = makeDroneCanvas('#f59e0b')
  const droneHighlightCanvas = makeDroneCanvas('#10b981')

  routes.forEach((route) => {
    if (!route.route_line?.coordinates) return

    const coords = route.route_line.coordinates
    const altProfile = route.altitude_profile

    // 1. Catmull-Rom 平滑曲线（含起降弧），密集采样点
    let curvedPositions = generateSmoothCurvePositions(coords, altProfile)

    const makeDepthFail = (color) =>
      new Cesium.PolylineDashMaterialProperty({ color: color.withAlpha(0.4), dashLength: 10 })

    // 2. 平滑折线实体
    const polylineEntity = viewer.entities.add({
      polyline: {
        positions: curvedPositions,
        width: 4,
        material: COL.normal,
        depthFailMaterial: makeDepthFail(COL.normal),
        clampToGround: false,
      },
    })

    // 3. 起终点标记（与曲线端点精确重合）
    const startEntity = viewer.entities.add({
      position: curvedPositions[0],
      point: {
        pixelSize: 10, color: Cesium.Color.fromCssColorString('#10b981'),
        outlineColor: Cesium.Color.WHITE, outlineWidth: 1,
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
      },
    })
    const endEntity = viewer.entities.add({
      position: curvedPositions[curvedPositions.length - 1],
      point: {
        pixelSize: 10, color: Cesium.Color.fromCssColorString('#ef4444'),
        outlineColor: Cesium.Color.WHITE, outlineWidth: 1,
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
      },
    })

    // 4. 无人机 Billboard：图像中心 = 实体坐标点，无像素偏移
    //    → 任意相机角度下图标中心都精确落在航线曲线上
    const droneEntity = viewer.entities.add({
      position: curvedPositions[0],
      billboard: {
        image: droneNormalCanvas,
        width: 36, height: 36,
        verticalOrigin: Cesium.VerticalOrigin.CENTER,
        horizontalOrigin: Cesium.HorizontalOrigin.CENTER,
        eyeOffset: Cesium.Cartesian3.ZERO,
        pixelOffset: Cesium.Cartesian2.ZERO,
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
        scale: 1.0,
      },
    })
    droneEntity._normalImage = droneNormalCanvas
    droneEntity._highlightImage = droneHighlightCanvas

    routeEntities[route.id] = { polylines: [polylineEntity], droneEntity, startEntity, endEntity }
    routeAnimState[route.id] = { curvedPositions, droneEntity, progress: 0, route }

    // 5. 异步抬升：在密集采样点上采样建筑高度，确保路段中间不穿模
    //    关键：动画状态与折线使用同一组 positions，无人机与航线永远重合
    liftCurvedPositions(curvedPositions).then(liftedPositions => {
      if (!viewer || viewer.isDestroyed() || !routeEntities[route.id]) return
      curvedPositions = liftedPositions
      polylineEntity.polyline.positions = new Cesium.ConstantProperty(liftedPositions)
      startEntity.position = new Cesium.ConstantPositionProperty(liftedPositions[0])
      endEntity.position = new Cesium.ConstantPositionProperty(liftedPositions[liftedPositions.length - 1])
      if (routeAnimState[route.id]) {
        routeAnimState[route.id].curvedPositions = liftedPositions
        droneEntity.position = new Cesium.ConstantPositionProperty(liftedPositions[0])
      }
      viewer.scene.requestRender()
    }).catch(() => {})
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

      const { curvedPositions, droneEntity } = state
      if (!curvedPositions?.length) return

      const n = curvedPositions.length
      const exactIdx = state.progress * (n - 1)
      const i = Math.floor(exactIdx)
      const frac = exactIdx - i
      const j = Math.min(i + 1, n - 1)

      // 从平滑曲线（与折线相同 positions）上插值 → 无人机与折线完全重合
      const pos = new Cesium.Cartesian3()
      Cesium.Cartesian3.lerp(curvedPositions[i], curvedPositions[j], frac, pos)
      droneEntity.position = pos
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
      p.polyline.width = isSelected ? 6 : 2
      p.polyline.material = isSelected ? COL.highlight : COL.normal.withAlpha(0.2)
      p.show = true
    })

    if (group.droneEntity) {
      group.droneEntity.show = true
      if (group.droneEntity.billboard) {
        group.droneEntity.billboard.scale = isSelected ? 1.4 : 0.8
        group.droneEntity.billboard.image = isSelected
          ? group.droneEntity._highlightImage
          : group.droneEntity._normalImage
      }
    }
    if (group.startEntity?.point) group.startEntity.point.pixelSize = isSelected ? 14 : 8
    if (group.endEntity?.point) group.endEntity.point.pixelSize = isSelected ? 14 : 8
  })

  const entityGroup = routeEntities[routeId]
  if (entityGroup?.polylines?.length) {
    viewer.flyTo(entityGroup.polylines[0], {
      offset: new Cesium.HeadingPitchRange(0, Cesium.Math.toRadians(-45), 5000),
    })
  }
}

function resetRouteHighlight() {
  if (!viewer) return
  mapStore.selectedRouteId = null

  Object.entries(routeEntities).forEach(([, group]) => {
    group.polylines?.forEach((p) => {
      p.polyline.width = 4
      p.polyline.material = COL.normal
      p.show = true
    })
    if (group.droneEntity?.billboard) {
      group.droneEntity.billboard.scale = 1.0
      group.droneEntity.billboard.image = group.droneEntity._normalImage
    }
    if (group.startEntity?.point) group.startEntity.point.pixelSize = 10
    if (group.endEntity?.point) group.endEntity.point.pixelSize = 10
  })
}

function setDronePosition(routeId, progress) {
  const state = routeAnimState[routeId]
  if (!state?.curvedPositions?.length) return
  state.progress = progress

  const { curvedPositions, droneEntity } = state
  const n = curvedPositions.length
  const exactIdx = progress * (n - 1)
  const i = Math.floor(exactIdx)
  const frac = exactIdx - i
  const j = Math.min(i + 1, n - 1)

  const pos = new Cesium.Cartesian3()
  Cesium.Cartesian3.lerp(curvedPositions[i], curvedPositions[j], frac, pos)
  droneEntity.position = pos

  if (viewer && !viewer.isDestroyed()) {
    viewer.scene.requestRenderMode = false
    const carto = Cesium.Cartographic.fromCartesian(pos)
    viewer.scene.camera.lookAt(
      Cesium.Cartesian3.fromDegrees(
        Cesium.Math.toDegrees(carto.longitude),
        Cesium.Math.toDegrees(carto.latitude),
        carto.height,
      ),
      new Cesium.HeadingPitchRange(0, Cesium.Math.toRadians(-45), 2000),
    )
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
  await nextTick()
  if (!cesiumIonToken) {
    console.warn('Cesium ion token not set. Set VITE_CESIUM_ION_TOKEN in .env.')
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

// ── 规划路径绘制（3D，带高度剖面 + 相位颜色 + 实际建筑高度校正） ──

let planPathEntities = []

// ── 数组平滑工具 ─────────────────────────────────────────
function _smooth(arr, w) {
  const r = arr.slice()
  for (let i = 0; i < arr.length; i++) {
    let s = 0, c = 0
    for (let k = -w; k <= w; k++) {
      const j = i + k
      if (j >= 0 && j < arr.length) { s += arr[j]; c++ }
    }
    r[i] = s / c
  }
  return r
}
// 形态学膨胀（取窗口最大值）——把孤立高点扩展成平台，消除"针尖"
function _dilateMax(arr, w) {
  const r = arr.slice()
  for (let i = 0; i < arr.length; i++) {
    let m = arr[i]
    for (let k = -w; k <= w; k++) {
      const j = i + k
      if (j >= 0 && j < arr.length) m = Math.max(m, arr[j])
    }
    r[i] = m
  }
  return r
}

// 数组均值平滑（带符号，用于横向偏移缓入缓出），保留首尾
function _smoothSeq(arr, w) {
  const r = arr.slice()
  for (let i = 1; i < arr.length - 1; i++) {
    let s = 0, c = 0
    for (let k = -w; k <= w; k++) { const j = i + k; if (j >= 0 && j < arr.length) { s += arr[j]; c++ } }
    r[i] = s / c
  }
  return r
}

// ── 穿模检测与航线校正：用真实 OSM 建筑高度逐点采样 ──────────────
// 核心问题：服务端按高斯模型水平绕行，但真实 OSM 建筑轮廓不一致，航线仍可能穿模。
// 解决：① 采样真实建筑高度，找出穿模点（建筑高于航线高度）；
//      ② 高于限高的建筑 → 横向偏移绕开（在垂直航向方向逐级试探，批量采样验证）；
//      ③ 低于限高/横向无解的残余穿模 → 垂直抬升兜底（绝不留穿模），缓入缓出成平滑弧。
async function correctForBuildings(points, profile, ceiling = Infinity) {
  if (!viewer?.scene?.sampleHeightMostDetailed || points.length < 2) return null
  const n = points.length
  const MARGIN = 15            // 垂直安全余量（米）
  const OFFSETS = [40, 80, 130, 190, 260, 340]  // 横向试探距离（米）
  const MPD = 111320

  const sampleH = async (pts) => {
    try {
      const carto = pts.map(p => Cesium.Cartographic.fromDegrees(p.lng, p.lat))
      const s = await viewer.scene.sampleHeightMostDetailed(carto)
      return s.map(c => (c && c.height > 0 ? c.height : 0))
    } catch { return null }
  }

  const baseAlt = profile.map(p => p.alt)
  const buildH = await sampleH(points)
  if (!buildH || !buildH.some(h => h > 0)) return null  // 建筑瓦片未就绪 → 保留服务端航迹

  // 可校正的相位（巡航/建筑/禁飞绕行段；起降段保持原样）
  const adjustable = (i) => profile[i].phase !== 'ascent' && profile[i].phase !== 'descent'
  // 单位垂直航向向量（经纬度增量），用于横向偏移
  const perp = (i) => {
    const a = points[Math.max(0, i - 1)], b = points[Math.min(n - 1, i + 1)]
    const ml = MPD * Math.cos(points[i].lat * Math.PI / 180)
    let dx = (b.lng - a.lng) * ml, dy = (b.lat - a.lat) * MPD
    const L = Math.hypot(dx, dy) || 1; dx /= L; dy /= L
    return { lng: -dy / ml, lat: dx / MPD }  // 旋转 90° 后换回经纬度
  }

  // ① 穿模点：真实建筑高于航线高度 + 余量
  const pen = buildH.map((h, i) => h > 0 && adjustable(i) && h + MARGIN > baseAlt[i])

  // ② 对"高于限高"的穿模点做横向绕行候选，批量采样验证
  const cand = []   // { i, signed, lng, lat }
  for (let i = 0; i < n; i++) {
    if (!pen[i] || buildH[i] <= ceiling) continue   // 低于限高的留给垂直抬升
    const pp = perp(i)
    for (const side of [1, -1]) for (const d of OFFSETS) {
      cand.push({ i, signed: side * d, lng: points[i].lng + pp.lng * side * d, lat: points[i].lat + pp.lat * side * d })
    }
  }
  const latOff = new Array(n).fill(0)      // 每点横向偏移（米，带符号）
  if (cand.length) {
    const candH = await sampleH(cand) || cand.map(() => 9999)
    const pick = new Map()                  // i → 最小 |偏移| 的可行候选
    cand.forEach((c, k) => {
      if (candH[k] + MARGIN < baseAlt[c.i]) {  // 该偏移点航线高度可净空
        const cur = pick.get(c.i)
        if (!cur || Math.abs(c.signed) < Math.abs(cur.signed)) pick.set(c.i, c)
      }
    })
    for (const [i, c] of pick) latOff[i] = c.signed
  }
  // 横向偏移缓入缓出平滑（避免突兀折角，形成圆润绕行弧）
  let latS = _smoothSeq(latOff, 3); latS = _smoothSeq(latS, 3)

  const newPts = points.map((p, i) => {
    if (Math.abs(latS[i]) < 1) return { ...p }
    const pp = perp(i)
    return { lng: p.lng + pp.lng * latS[i], lat: p.lat + pp.lat * latS[i], alt: p.alt }
  })

  // ③ 重新采样校正后航线，对残余穿模（低矮建筑或横向无解）垂直抬升兜底
  const buildH2 = await sampleH(newPts) || buildH
  const need = baseAlt.map((a, i) => (adjustable(i) && buildH2[i] > 0) ? Math.max(a, buildH2[i] + MARGIN) : a)
  let alt = _dilateMax(need, 2)    // 抬升段扩成平台
  alt = _smooth(alt, 2)            // 平滑成缓坡
  for (let i = 0; i < n; i++) if (!adjustable(i)) alt[i] = baseAlt[i]  // 起降段保留斜坡

  return newPts.map((p, i) => {
    const moved = Math.abs(latS[i]) > 2 || alt[i] > baseAlt[i] + 5
    return {
      lng: p.lng, lat: p.lat, alt: Math.round(alt[i]), index: i,
      phase: (moved && adjustable(i)) ? 'building' : profile[i].phase,
    }
  })
}

// 从服务端剖面推断巡航高度
function _deriveCruise(profile) {
  if (!profile?.length) return 0
  const cruise = profile.filter(p => p.phase === 'cruise').map(p => p.alt)
  const pool = cruise.length ? cruise : profile.map(p => p.alt)
  pool.sort((a, b) => a - b)
  return pool[Math.floor(pool.length / 2)]
}

// 核心绘制逻辑（同步），接受任意高度剖面（初始或校正后均可）
function _drawPlanPathCore(pathPoints, altitudeProfile) {
  if (!viewer || !pathPoints?.length) return

  const C = (hex) => Cesium.Color.fromCssColorString(hex)
  const phaseColors = {
    ascent: C('#22c55e'), cruise: C('#3b82f6'),
    descent: C('#f59e0b'), height_limit: C('#ef4444'),
    building: C('#a855f7'), no_fly: C('#ef4444'),
  }
  const hasProfile = altitudeProfile && altitudeProfile.length === pathPoints.length

  if (!hasProfile) {
    const positions = pathPoints.map(p => Cesium.Cartesian3.fromDegrees(p.lng, p.lat, 120))
    planPathEntities.push(viewer.entities.add({
      polyline: { positions, width: 5, material: C('#3b82f6'), clampToGround: false }
    }))
    return
  }

  // 按飞行相位切分并分段绘制
  const boundaries = [0]
  for (let i = 1; i < pathPoints.length; i++) {
    if (altitudeProfile[i].phase !== altitudeProfile[i - 1].phase) boundaries.push(i)
  }
  boundaries.push(pathPoints.length - 1)

  for (let b = 0; b < boundaries.length - 1; b++) {
    const startIdx = boundaries[b]
    const endIdx   = boundaries[b + 1]
    const phase    = altitudeProfile[startIdx].phase
    const color    = phaseColors[phase] || C('#3b82f6')
    const segPts   = pathPoints.slice(startIdx, endIdx + 1)
    if (segPts.length < 2) continue

    const positions = segPts.map((p, k) => {
      const alt = altitudeProfile[startIdx + k]?.alt ?? 120
      return Cesium.Cartesian3.fromDegrees(p.lng, p.lat, alt)
    })

    if (phase === 'building' || phase === 'no_fly') {
      const haloColor = phase === 'no_fly' ? '#ef4444' : '#a855f7'
      planPathEntities.push(viewer.entities.add({
        polyline: { positions, width: 11, material: C(haloColor).withAlpha(0.25), clampToGround: false }
      }))
    }
    planPathEntities.push(viewer.entities.add({
      polyline: {
        positions,
        width: (phase === 'building' || phase === 'no_fly') ? 5 : 4,
        material: new Cesium.PolylineGlowMaterialProperty({ glowPower: 0.25, color: color.withAlpha(0.95) }),
        clampToGround: false,
      }
    }))
  }

  // 相位切换处打高度标注
  for (let bi = 1; bi < boundaries.length - 1; bi++) {
    const idx = boundaries[bi]
    const p   = pathPoints[idx]
    const alt = altitudeProfile[idx]?.alt ?? 0
    if (!alt) continue
    planPathEntities.push(viewer.entities.add({
      position: Cesium.Cartesian3.fromDegrees(p.lng, p.lat, alt + 30),
      label: {
        text: `${alt}m`,
        font: '11px monospace',
        fillColor: Cesium.Color.WHITE,
        showBackground: true,
        backgroundColor: Cesium.Color.fromCssColorString('#1e293b').withAlpha(0.85),
        backgroundPadding: new Cesium.Cartesian2(4, 2),
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
        pixelOffset: new Cesium.Cartesian2(0, -10),
      },
    }))
  }
}

// 外部接口：先用服务端剖面立即绘制，再异步用真实 OSM 建筑做细密横向避让重绘
async function drawPlanPath(pathPoints, altitudeProfile, opts = {}) {
  clearPlanPath()
  if (!viewer || !pathPoints?.length) return

  // 第一步：立即展示服务端路径（快速反馈）
  _drawPlanPathCore(pathPoints, altitudeProfile)
  viewer.scene.requestRender()

  // 第二步：异步细密横向避让（仅在开启避障且有剖面时）
  const hasProfile = altitudeProfile && altitudeProfile.length === pathPoints.length
  if (!hasProfile || opts.avoidBuildings === false) return

  try {
    // 返回的是校正后的航迹点（含横向偏移 + 抬升 + 相位），位置与高度均可能改变
    const corrected = await correctForBuildings(pathPoints, altitudeProfile, opts.cruiseAlt ?? Infinity)
    if (!viewer || viewer.isDestroyed() || !corrected) return
    clearPlanPath()
    _drawPlanPathCore(corrected, corrected)
    viewer.scene.requestRender()
  } catch { /* 采样失败，保留初始绘制 */ }
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
