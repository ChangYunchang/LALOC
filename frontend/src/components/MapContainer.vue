<template>
  <div class="map-wrapper">
    <div id="map-container" ref="mapRef"></div>

    <!-- 2D/3D 切换按钮 - 左上角（避免与右上角缩放按钮冲突） -->
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

    <!-- 图例 - 右下角（避免与左下角比例尺冲突） -->
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

const amapKey = import.meta.env.VITE_AMAP_KEY
const amapSecurityCode = import.meta.env.VITE_AMAP_SECURITY_CODE

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
      buildingAnimation: true,
      rotateEnable: true,
      pitchEnable: true,
      jogEnable: true,
      animateEnable: true,
    })

    // 比例尺放左下角
    map.addControl(new AMap.Scale({ position: 'LB' }))
    // 缩放工具放右上角
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

    mapStore.setMap(map)
    await zoneStore.fetchAll()
    renderZones()
  } catch (e) {
    console.error('地图加载失败:', e)
  }
})

onUnmounted(() => {
  if (mapStore.map) mapStore.map.destroy()
})

function renderZones() {
  const map = mapStore.map
  if (!map || !AMap) return

  mapStore.clearAllOverlays()

  // 禁飞区（红色）
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
      polygon.on('click', () => {
        new AMap.InfoWindow({
          content: `<div style="padding:8px 12px;">
            <b style="color:#dc2626;font-size:14px;">${name}</b><br/>
            <span style="color:#6b7280;font-size:12px;">禁飞原因: ${feature.properties?.reason || '无'}</span>
          </div>`,
          offset: new AMap.Pixel(0, -10),
        }).open(map, polygon.getBounds().getCenter())
      })

      map.add(polygon)
      mapStore.noFlyPolygons.push(polygon)
    })
  }

  // 限高区（橙色）
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
        new AMap.InfoWindow({
          content: `<div style="padding:8px 12px;">
            <b style="color:#ea580c;font-size:14px;">${name}</b><br/>
            <span style="color:#6b7280;font-size:12px;">限高: ${maxAlt} 米</span>
          </div>`,
          offset: new AMap.Pixel(0, -10),
        }).open(map, polygon.getBounds().getCenter())
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

watch(() => zoneStore.noFlyZones, renderZones, { deep: true })
watch(() => zoneStore.heightLimitZones, renderZones, { deep: true })
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

/* 2D/3D 按钮 - 左上角 */
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
