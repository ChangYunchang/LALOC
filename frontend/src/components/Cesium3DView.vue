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
let _planToken = 0   // 每次 planAroundBuildings 调用时递增，旧调用检测到失效后自动退出
let _drawToken = 0   // 每次 drawPlanPath 调用时递增，过期的异步绘制不再更新画面

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

// ── 穿模垂直校正：用真实 OSM 建筑高度逐点采样，防穿模 ──────────────
// 水平绕行已在服务端基于"可越顶高度"完成（高于 35m 的建筑均水平绕开），此处不再改横向，
// 仅做垂直兜底：真实 OSM 建筑若仍高于航线（模型与真实轮廓有差异），平滑抬升越过，绝不留穿模。
// 不做横向偏移，从根本上消除横向左右震荡。
async function correctForBuildings(points, profile) {
  if (!viewer?.scene?.sampleHeightMostDetailed || points.length < 2) return null
  const n = points.length
  const MARGIN = 15            // 垂直安全余量（米）

  const carto = points.map(p => Cesium.Cartographic.fromDegrees(p.lng, p.lat))
  let sampled
  try { sampled = await viewer.scene.sampleHeightMostDetailed(carto) } catch { return null }
  const buildH = sampled.map(c => (c && c.height > 0 ? c.height : 0))
  if (!buildH.some(h => h > 0)) return null  // 建筑瓦片未就绪 → 保留服务端航迹

  const adjustable = (i) => profile[i].phase !== 'ascent' && profile[i].phase !== 'descent'
  const baseAlt = profile.map(p => p.alt)
  // 真实建筑高于航线 → 抬升越过；膨胀成平台 + 均值平滑（缓坡，无针尖）
  const need = baseAlt.map((a, i) => (adjustable(i) && buildH[i] > 0) ? Math.max(a, buildH[i] + MARGIN) : a)
  let alt = _dilateMax(need, 2)
  alt = _smooth(alt, 2)
  for (let i = 0; i < n; i++) if (!adjustable(i)) alt[i] = baseAlt[i]  // 起降段保留斜坡

  return points.map((p, i) => ({
    lng: p.lng, lat: p.lat, alt: Math.round(alt[i]), index: i,
    phase: (alt[i] > baseAlt[i] + 5 && adjustable(i) && profile[i].phase === 'cruise') ? 'building' : profile[i].phase,
  }))
}

// 从服务端剖面推断巡航高度
function _deriveCruise(profile) {
  if (!profile?.length) return 0
  const cruise = profile.filter(p => p.phase === 'cruise').map(p => p.alt)
  const pool = cruise.length ? cruise : profile.map(p => p.alt)
  pool.sort((a, b) => a - b)
  return pool[Math.floor(pool.length / 2)]
}

// ════════════════════════════════════════════════════════════════════
// 客户端"贴地规划再平移高空"路径规划：用真实 OSM 建筑高度做精细栅格避障
//
// 思路（按用户构想）：先在贴近地面的视角下，把高于"可越顶高度"的真实建筑都视为障碍，
// 用精细栅格（~10m）A* 绕行 → 天然实现对建筑物的水平绕行；再把整条航线平移到巡航高度。
// 矮建筑（< 可越顶高度）不绕行，巡航高度直接越过。采样耗时，故回调上报进度。
// ════════════════════════════════════════════════════════════════════
const _MPD = 111320
const _mLng = (lat) => 111320 * Math.cos(lat * Math.PI / 180)
function _hav(a, b) {
  const R = 6371000, dLat = (b.lat - a.lat) * Math.PI / 180, dLng = (b.lng - a.lng) * Math.PI / 180
  const s = Math.sin(dLat / 2) ** 2 + Math.cos(a.lat * Math.PI / 180) * Math.cos(b.lat * Math.PI / 180) * Math.sin(dLng / 2) ** 2
  return R * 2 * Math.atan2(Math.sqrt(s), Math.sqrt(1 - s))
}
function _pointInPoly(lng, lat, poly) {
  const p = poly.pts; let inside = false
  for (let i = 0, j = p.length - 1; i < p.length; j = i++) {
    const xi = p[i].lng, yi = p[i].lat, xj = p[j].lng, yj = p[j].lat
    if (((yi > lat) !== (yj > lat)) && (lng < (xj - xi) * (lat - yi) / (yj - yi) + xi)) inside = !inside
  }
  return inside
}
function _buildNoFlyPolys() {
  const polys = []
  const fc = zoneStore.noFlyZones
  if (!fc?.features) return polys
  for (const f of fc.features) {
    const g = f.geometry; if (!g) continue
    const rings = g.type === 'Polygon' ? [g.coordinates[0]]
      : g.type === 'MultiPolygon' ? g.coordinates.map(c => c[0]) : []
    for (const ring of rings) {
      const pts = ring.map(c => ({ lng: c[0], lat: c[1] }))
      if (pts.length < 3) continue
      let mnL = Infinity, mxL = -Infinity, mnA = Infinity, mxA = -Infinity
      for (const p of pts) { mnL = Math.min(mnL, p.lng); mxL = Math.max(mxL, p.lng); mnA = Math.min(mnA, p.lat); mxA = Math.max(mxA, p.lat) }
      polys.push({ pts, minLng: mnL, maxLng: mxL, minLat: mnA, maxLat: mxA })
    }
  }
  return polys
}

class _MinHeap {
  constructor() { this.a = [] }
  get size() { return this.a.length }
  push(n) { const a = this.a; a.push(n); let i = a.length - 1; while (i > 0) { const p = (i - 1) >> 1; if (a[p].f <= a[i].f) break;[a[p], a[i]] = [a[i], a[p]]; i = p } }
  pop() { const a = this.a, t = a[0], l = a.pop(); if (a.length) { a[0] = l; let i = 0; const n = a.length; while (true) { let s = i, L = 2 * i + 1, r = L + 1; if (L < n && a[L].f < a[s].f) s = L; if (r < n && a[r].f < a[s].f) s = r; if (s === i) break;[a[s], a[i]] = [a[i], a[s]]; i = s } } return t } }

// 建筑离地高度缓存：键为「分辨率:全局列_全局行」，跨多次规划复用（同区域瞬时完成）
const _bhCache = new Map()
const _REF_LAT = 23.13          // 广州参考纬度（固定 → 全局栅格对齐，缓存可跨规划命中）
const _mLngRef = _mLng(_REF_LAT)

async function planAroundBuildings(controlPts, opts = {}, onProgress = null) {
  if (!viewer?.scene?.sampleHeightMostDetailed || !controlPts || controlPts.length < 2) return null
  // 取消令牌：若新规划在本次完成前启动，live() 返回 false，直接退出
  const token = ++_planToken
  const live = () => token === _planToken && viewer && !viewer.isDestroyed()
  const yld = () => new Promise(r => setTimeout(r, 0))   // 让出主线程（≈0ms，允许浏览器渲染/响应）
  const cruiseAlt = Math.max(30, Math.min(300, opts.cruiseAlt || 120))
  const OVERFLY = opts.overflyMax ?? 20
  const noFlyPolys = opts.avoidNoFly === false ? [] : _buildNoFlyPolys()

  // ── 1. 全局对齐栅格 + 走廊裁剪（只在航线两侧一定宽度内计算）─────────
  let minLng = Infinity, maxLng = -Infinity, minLat = Infinity, maxLat = -Infinity
  for (const p of controlPts) {
    minLng = Math.min(minLng, p.lng); maxLng = Math.max(maxLng, p.lng)
    minLat = Math.min(minLat, p.lat); maxLat = Math.max(maxLat, p.lat)
  }
  const CORRIDOR = 360  // 走廊半宽（米）：绕行可用空间，超出走廊视作开阔（不采样）
  minLng -= CORRIDOR / _mLngRef; maxLng += CORRIDOR / _mLngRef
  minLat -= CORRIDOR / _MPD; maxLat += CORRIDOR / _MPD

  // 固定 10m 栅格并对齐到全局整数格（缓存键依赖全局格号）；过大则按 2 的幂放粗
  let CELL = 10, cellLat, cellLng, C0, R0, cols, rows, total
  const MAX_CELLS = 60000
  while (true) {
    cellLat = CELL / _MPD; cellLng = CELL / _mLngRef
    C0 = Math.floor(minLng / cellLng); R0 = Math.floor(minLat / cellLat)
    cols = Math.ceil(maxLng / cellLng) - C0 + 1
    rows = Math.ceil(maxLat / cellLat) - R0 + 1
    total = rows * cols
    if (total <= MAX_CELLS || CELL >= 80) break
    CELL *= 2
  }
  const cellM = CELL   // 下游 A*/串拉/重采样按米计算用
  const cellCenter = (r, c) => ({ lng: (C0 + c + 0.5) * cellLng, lat: (R0 + r + 0.5) * cellLat })
  const toCell = (p) => ({
    r: Math.max(0, Math.min(rows - 1, Math.floor(p.lat / cellLat) - R0)),
    c: Math.max(0, Math.min(cols - 1, Math.floor(p.lng / cellLng) - C0)),
  })
  const ckey = (r, c) => `${CELL}:${C0 + c}_${R0 + r}`

  // 走廊掩码：到任一控制段的距离 ≤ CORRIDOR 才纳入计算
  const segs = []
  for (let s = 0; s < controlPts.length - 1; s++) segs.push([controlPts[s], controlPts[s + 1]])
  const distToSegsM = (lng, lat) => {
    let best = Infinity
    for (const [a, b] of segs) {
      const ax = (lng - a.lng) * _mLngRef, ay = (lat - a.lat) * _MPD
      const bx = (b.lng - a.lng) * _mLngRef, by = (b.lat - a.lat) * _MPD
      const L2 = bx * bx + by * by || 1
      const t = Math.max(0, Math.min(1, (ax * bx + ay * by) / L2))
      best = Math.min(best, Math.hypot(ax - bx * t, ay - by * t))
    }
    return best
  }

  // ── 2. 采样真实建筑高度：仅采样「走廊内 ∧ 未缓存」的格 ──────────────
  const buildH = new Float32Array(total)         // 建筑离地高度（走廊外＝0，视作开阔）
  const inCorridor = new Uint8Array(total)
  const needCells = []                            // 需新采样的格 {r,c,i}
  for (let r = 0; r < rows; r++) for (let c = 0; c < cols; c++) {
    const i = r * cols + c
    const cc = cellCenter(r, c)
    if (distToSegsM(cc.lng, cc.lat) > CORRIDOR) continue
    inCorridor[i] = 1
    const cached = _bhCache.get(ckey(r, c))
    if (cached !== undefined) { buildH[i] = cached; continue }
    needCells.push({ r, c, i, lng: cc.lng, lat: cc.lat })
  }

  if (onProgress) onProgress(0.03, needCells.length ? `采样真实建筑（${needCells.length} 点）` : '复用缓存')
  if (needCells.length) {
    const terrainProv = viewer.terrainProvider
    // 地形：仅对需采样点做一次性采样（平缓，足够）；与场景采样并行
    const terrCarto = needCells.map(c => Cesium.Cartographic.fromDegrees(c.lng, c.lat))
    const sceneCarto = needCells.map(c => Cesium.Cartographic.fromDegrees(c.lng, c.lat))
    const terrainPromise = terrainProv
      ? Cesium.sampleTerrainMostDetailed(terrainProv, terrCarto).catch(() => null) : Promise.resolve(null)
    const scenePromise = viewer.scene.sampleHeightMostDetailed(sceneCarto).catch(() => null)
    const [terr, scene] = await Promise.all([terrainPromise, scenePromise])
    if (!live()) return null
    if (scene === null) return null   // 采样失败/瓦片未就绪 → 交回退（不写入错误缓存）
    for (let k = 0; k < needCells.length; k++) {
      const { i } = needCells[k]
      const sh = (scene[k] && Number.isFinite(scene[k].height)) ? scene[k].height : 0
      const th = (terr && terr[k] && Number.isFinite(terr[k].height)) ? terr[k].height : 0
      const h = Math.max(0, sh - th)
      buildH[i] = h
      _bhCache.set(ckey(needCells[k].r, needCells[k].c), h)   // 写入缓存
    }
    if (_bhCache.size > 400000) _bhCache.clear()   // 防无限增长
  }

  // 关键：无论是否采样（缓存全部命中时没有任何 await），都必须在此处让出主线程。
  // 第二次规划时全部缓存命中，若不 yield，后续 A* 会完全同步运行导致页面卡死。
  await yld()
  if (!live()) return null

  // ── 3. 障碍栅格：高于可越顶的真实建筑 + 禁飞区 ───────────────
  if (onProgress) onProgress(0.44, '规划绕行航线')
  const blocked = new Uint8Array(total)  // 0 通行 / 1 建筑 / 2 禁飞
  for (let r = 0; r < rows; r++) for (let c = 0; c < cols; c++) {
    const i = r * cols + c
    if (inCorridor[i] && buildH[i] > OVERFLY) { blocked[i] = 1; continue }
    if (noFlyPolys.length) {
      const cc = cellCenter(r, c)
      for (const poly of noFlyPolys) {
        if (cc.lng < poly.minLng || cc.lng > poly.maxLng || cc.lat < poly.minLat || cc.lat > poly.maxLat) continue
        if (_pointInPoly(cc.lng, cc.lat, poly)) { blocked[i] = 2; break }
      }
    }
  }
  const isBlk = (r, c) => blocked[r * cols + c]
  // 起终/途经点若落在障碍内，就近找可通行格
  const nearestFree = (cell) => {
    if (!isBlk(cell.r, cell.c)) return cell
    for (let rad = 1; rad <= 25; rad++) {
      for (let dr = -rad; dr <= rad; dr++) for (let dc = -rad; dc <= rad; dc++) {
        if (Math.max(Math.abs(dr), Math.abs(dc)) !== rad) continue
        const nr = cell.r + dr, nc = cell.c + dc
        if (nr >= 0 && nc >= 0 && nr < rows && nc < cols && !isBlk(nr, nc)) return { r: nr, c: nc }
      }
    }
    return cell
  }

  // ── 4. 8 方向 A*（保留途经点：逐段规划）──────────────────────
  // A* 改为 async：每 2000 次迭代 yield 一次，防止长路径/多途经点时主线程阻塞卡死
  const astarSeg = async (sCell, gCell) => {
    const gKey = gCell.r * cols + gCell.c
    const oct = (r, c) => { const dr = Math.abs(r - gCell.r), dc = Math.abs(c - gCell.c); return cellM * (Math.max(dr, dc) + (Math.SQRT2 - 1) * Math.min(dr, dc)) }
    const open = new _MinHeap(), gS = new Map(), par = new Map()
    const sKey = sCell.r * cols + sCell.c
    gS.set(sKey, 0); open.push({ r: sCell.r, c: sCell.c, f: oct(sCell.r, sCell.c) })
    const closed = new Set(); let guard = 0
    while (open.size && guard++ < total) {
      if (guard % 500 === 0) { await yld(); if (!live()) return null }
      const cur = open.pop(); const cK = cur.r * cols + cur.c
      if (cK === gKey) { const cells = []; let k = cK; while (k !== undefined) { cells.push({ r: Math.floor(k / cols), c: k % cols }); k = par.get(k) } cells.reverse(); return cells }
      if (closed.has(cK)) continue
      closed.add(cK)
      const gc = gS.get(cK)
      for (let dr = -1; dr <= 1; dr++) for (let dc = -1; dc <= 1; dc++) {
        if (!dr && !dc) continue
        const nr = cur.r + dr, nc = cur.c + dc
        if (nr < 0 || nc < 0 || nr >= rows || nc >= cols) continue
        const nK = nr * cols + nc
        if (closed.has(nK)) continue
        if (nK !== gKey && isBlk(nr, nc)) continue
        if (dr && dc && (isBlk(cur.r, nc) || isBlk(nr, cur.c))) continue
        const step = (dr && dc) ? cellM * Math.SQRT2 : cellM
        const ng = gc + step
        if (ng < (gS.get(nK) ?? Infinity)) { gS.set(nK, ng); par.set(nK, cK); open.push({ r: nr, c: nc, f: ng + oct(nr, nc) }) }
      }
    }
    return null
  }

  const lineClear = (a, b) => {
    const d = _hav(a, b), steps = Math.max(1, Math.ceil(d / (cellM * 0.5)))
    for (let s = 1; s < steps; s++) {
      const t = s / steps
      const c = toCell({ lng: a.lng + (b.lng - a.lng) * t, lat: a.lat + (b.lat - a.lat) * t })
      if (isBlk(c.r, c.c)) return false
    }
    return true
  }
  const stringPull = (pts) => {
    if (pts.length <= 2) return pts
    const out = [pts[0]]; let i = 0
    while (i < pts.length - 1) { let j = pts.length - 1; while (j > i + 1 && !lineClear(pts[i], pts[j])) j--; out.push(pts[j]); i = j }
    return out
  }

  let feasible = true
  let poly = []
  const _segTotal = controlPts.length - 1
  for (let s = 0; s < _segTotal; s++) {
    const seg = await astarSeg(nearestFree(toCell(controlPts[s])), nearestFree(toCell(controlPts[s + 1])))
    if (!live()) return null
    if (onProgress) onProgress(0.44 + 0.44 * (s + 1) / _segTotal, `绕行规划 ${s + 1}/${_segTotal} 段`)
    let segPts
    if (!seg) { feasible = false; segPts = [controlPts[s], controlPts[s + 1]] }
    else {
      segPts = seg.map(({ r, c }) => cellCenter(r, c))
      segPts[0] = { lng: controlPts[s].lng, lat: controlPts[s].lat }
      segPts[segPts.length - 1] = { lng: controlPts[s + 1].lng, lat: controlPts[s + 1].lat }
      segPts = stringPull(segPts)
    }
    if (poly.length) segPts = segPts.slice(1)
    poly = poly.concat(segPts)
  }

  if (onProgress) onProgress(0.91, '平滑航线')
  // ── 5. Chaikin 柔滑 + 均匀重采样 ───────────────────────────
  const chaikin = (pts, it) => {
    let p = pts
    for (let k = 0; k < it; k++) {
      if (p.length < 3) break
      const o = [p[0]]
      for (let i = 0; i < p.length - 1; i++) { const a = p[i], b = p[i + 1]; o.push({ lng: a.lng * 0.75 + b.lng * 0.25, lat: a.lat * 0.75 + b.lat * 0.25 }); o.push({ lng: a.lng * 0.25 + b.lng * 0.75, lat: a.lat * 0.25 + b.lat * 0.75 }) }
      o.push(p[p.length - 1]); p = o
    }
    return p
  }
  const SAMPLE_M = Math.max(20, cellM)
  const resampleM = (pts, S) => {
    const o = [pts[0]]; let d = S
    for (let i = 1; i < pts.length; i++) { const a = pts[i - 1], b = pts[i], L = _hav(a, b); if (L < 1e-9) continue; while (d <= L) { const t = d / L; o.push({ lng: a.lng + (b.lng - a.lng) * t, lat: a.lat + (b.lat - a.lat) * t }); d += S } d -= L }
    o.push(pts[pts.length - 1]); return o
  }
  let dense = resampleM(chaikin(poly, 3), SAMPLE_M)
  dense[0] = controlPts[0]; dense[dense.length - 1] = controlPts[controlPts.length - 1]
  const n = dense.length

  if (onProgress) onProgress(0.96, '生成高度剖面')
  // ── 6. 高度剖面（平移到巡航高度）+ 绕行段配色 ───────────────
  const ASCENT_R = 0.1, DESCENT_R = 0.1
  const nearBlk = (p, kind) => {
    const cell = toCell(p)
    for (let dr = -2; dr <= 2; dr++) for (let dc = -2; dc <= 2; dc++) {
      const nr = cell.r + dr, nc = cell.c + dc
      if (nr >= 0 && nc >= 0 && nr < rows && nc < cols && blocked[nr * cols + nc] === kind) return true
    }
    return false
  }
  const altitude_profile = [], path = []
  for (let i = 0; i < n; i++) {
    const t = i / Math.max(n - 1, 1)
    let alt, phase
    if (t < ASCENT_R) { alt = 20 + (cruiseAlt - 20) * (t / ASCENT_R); phase = 'ascent' }
    else if (t > 1 - DESCENT_R) { alt = 20 + (cruiseAlt - 20) * ((1 - t) / DESCENT_R); phase = 'descent' }
    else {
      alt = cruiseAlt; phase = 'cruise'
      if (nearBlk(dense[i], 2)) phase = 'no_fly'
      else if (nearBlk(dense[i], 1)) phase = 'building'
    }
    altitude_profile.push({ index: i, alt: Math.round(alt), phase })
    path.push({ lng: dense[i].lng, lat: dense[i].lat, alt: Math.round(alt), index: i })
  }

  if (onProgress) onProgress(1, '完成')
  return { path, altitude_profile, is_feasible: feasible }
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

    const isAvoid = phase === 'building' || phase === 'no_fly'
    if (isAvoid) {
      // 规避段：更宽的外发光光晕，醒目区别于巡航段
      const haloColor = phase === 'no_fly' ? '#ef4444' : '#a855f7'
      planPathEntities.push(viewer.entities.add({
        polyline: { positions, width: 22, material: C(haloColor).withAlpha(0.22), clampToGround: false }
      }))
      planPathEntities.push(viewer.entities.add({
        polyline: { positions, width: 14, material: C(haloColor).withAlpha(0.32), clampToGround: false }
      }))
    }
    planPathEntities.push(viewer.entities.add({
      polyline: {
        positions,
        width: isAvoid ? 9 : 7,   // 整体加粗；规避段更粗
        material: new Cesium.PolylineGlowMaterialProperty({
          glowPower: isAvoid ? 0.35 : 0.2,
          color: color.withAlpha(isAvoid ? 1.0 : 0.95),
        }),
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
  // 绘制令牌：若本次 drawPlanPath 尚未完成时又发起新的，则旧调用在每个 await 后检查并退出
  const drawToken = ++_drawToken
  const drawAlive = () => drawToken === _drawToken && viewer && !viewer.isDestroyed()

  clearPlanPath()
  if (!viewer || !pathPoints?.length) return

  // 第一步：立即展示服务端路径（快速反馈）
  _drawPlanPathCore(pathPoints, altitudeProfile)
  viewer.scene.requestRender()

  // 第二步：异步避障重绘（仅在开启避障且有剖面时）
  const hasProfile = altitudeProfile && altitudeProfile.length === pathPoints.length
  if (!hasProfile || opts.avoidBuildings === false) return

  // 首选：客户端"贴地规划再平移高空"——用真实 OSM 建筑做精细栅格水平绕行
  if (opts.controlPts && opts.controlPts.length >= 2) {
    if (opts.onProgress) opts.onProgress(0.01, '准备真实建筑数据')
    try {
      const planned = await planAroundBuildings(opts.controlPts, {
        cruiseAlt: opts.cruiseAlt, overflyMax: opts.overflyMax, avoidNoFly: opts.avoidNoFly,
      }, opts.onProgress)
      if (!drawAlive()) return   // 新规划已触发，丢弃旧结果
      if (planned && planned.path.length) {
        clearPlanPath()
        _drawPlanPathCore(planned.path, planned.altitude_profile)
        viewer.scene.requestRender()
        return
      }
    } catch { /* 规划失败 → 回退垂直防穿模 */ }
    if (!drawAlive()) return
    if (opts.onProgress) opts.onProgress(1, '完成')
  }

  if (!drawAlive()) return
  // 回退：保留服务端水平航线，仅做垂直防穿模
  try {
    const corrected = await correctForBuildings(pathPoints, altitudeProfile)
    if (!drawAlive()) return
    if (!corrected) return
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
