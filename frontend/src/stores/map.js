/**
 * 地图状态管理
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useMapStore = defineStore('map', () => {
  // 地图实例
  const map = ref(null)

  // AMap 类引用（供其他组件使用）
  let AMap = null

  // 地图模式：2D 或 3D
  const viewMode = ref('2D')

  // 是否正在加载
  const loading = ref(false)

  // 当前时间（时间轴）
  const currentTime = ref(new Date())

  // 地图中心点（广州市）
  const center = ref([113.2644, 23.1291])

  // 地图缩放级别
  const zoom = ref(12)

  // 禁飞区多边形列表
  const noFlyPolygons = ref([])

  // 限高区多边形列表
  const heightLimitPolygons = ref([])

  // 航线相关
  const routeLines = ref([])      // 航线 Polyline
  const routeDataList = ref([])   // 航线数据
  const selectedRouteId = ref(null) // 当前选中的航线 ID
  const droneMarkers = ref([])    // 无人机标记

  function setMap(mapInstance) {
    map.value = mapInstance
  }

  function toggleViewMode() {
    viewMode.value = viewMode.value === '2D' ? '3D' : '2D'
  }

  function clearAllOverlays() {
    if (map.value) {
      noFlyPolygons.value.forEach((p) => p.setMap(null))
      noFlyPolygons.value = []

      heightLimitPolygons.value.forEach((p) => p.setMap(null))
      heightLimitPolygons.value = []

      routeLines.value.forEach((l) => l.setMap(null))
      routeLines.value = []

      droneMarkers.value.forEach((m) => m.setMap(null))
      droneMarkers.value = []
    }
  }

  // 只清除航线和无人机（保留禁飞区/限高区）
  function clearRouteOverlays() {
    if (map.value) {
      routeLines.value.forEach((l) => l.setMap(null))
      routeLines.value = []
      droneMarkers.value.forEach((m) => m.setMap(null))
      droneMarkers.value = []
    }
  }

  return {
    map,
    AMap,
    viewMode,
    loading,
    currentTime,
    center,
    zoom,
    noFlyPolygons,
    heightLimitPolygons,
    routeLines,
    routeDataList,
    selectedRouteId,
    droneMarkers,
    setMap,
    toggleViewMode,
    clearAllOverlays,
    clearRouteOverlays,
  }
})
