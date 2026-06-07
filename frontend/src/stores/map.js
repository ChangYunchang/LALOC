/**
 * 地图状态管理
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useMapStore = defineStore('map', () => {
  // 地图实例（使用 shallowRef 避免 Vue 深度代理）
  const map = ref(null)

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

  // 航线列表
  const routeLines = ref([])

  // 无人机模拟标记
  const droneMarkers = ref([])

  function setMap(mapInstance) {
    map.value = mapInstance
  }

  function toggleViewMode() {
    viewMode.value = viewMode.value === '2D' ? '3D' : '2D'
  }

  function clearAllOverlays() {
    if (map.value) {
      // 清除禁飞区
      noFlyPolygons.value.forEach((p) => p.setMap(null))
      noFlyPolygons.value = []

      // 清除限高区
      heightLimitPolygons.value.forEach((p) => p.setMap(null))
      heightLimitPolygons.value = []

      // 清除航线
      routeLines.value.forEach((l) => l.setMap(null))
      routeLines.value = []

      // 清除无人机标记
      droneMarkers.value.forEach((m) => m.setMap(null))
      droneMarkers.value = []
    }
  }

  return {
    map,
    viewMode,
    loading,
    currentTime,
    center,
    zoom,
    noFlyPolygons,
    heightLimitPolygons,
    routeLines,
    droneMarkers,
    setMap,
    toggleViewMode,
    clearAllOverlays,
  }
})
