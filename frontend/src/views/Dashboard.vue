<template>
  <div class="dashboard">
    <!-- 左侧面板 -->
    <aside class="left-panel">
      <WeatherPanel />

      <!-- 区域统计 -->
      <div class="stats-card">
        <div class="card-header">
          <span class="card-icon">📊</span>
          <span class="card-title">区域统计</span>
        </div>
        <div class="stats-grid">
          <div class="stat-item">
            <span class="stat-number nofly">{{ zoneStore.stats.no_fly_zones_count }}</span>
            <span class="stat-label">禁飞区</span>
          </div>
          <div class="stat-item">
            <span class="stat-number heightlimit">{{ zoneStore.stats.height_limit_zones_count }}</span>
            <span class="stat-label">限高区</span>
          </div>
        </div>
      </div>

      <!-- 航线列表 -->
      <div class="routes-card">
        <div class="card-header">
          <span class="card-icon">✈️</span>
          <span class="card-title">航线列表</span>
          <span v-if="routes.length > 0" class="route-count">{{ routes.length }}</span>
        </div>
        <div class="routes-list">
          <div
            v-for="route in routes"
            :key="route.id"
            class="route-item"
            :class="{ active: mapStore.selectedRouteId === route.id }"
            @click="onSelectRoute(route)"
          >
            <div class="route-info">
              <span class="route-name">{{ route.name }}</span>
              <span class="route-meta">
                {{ (route.total_distance / 1000).toFixed(1) }}km
                · {{ Math.ceil(route.estimated_time / 60) }}分钟
              </span>
            </div>
            <div class="route-status" :class="route.status">
              {{ statusMap[route.status] || route.status }}
            </div>
          </div>
          <div v-if="routes.length === 0" class="empty-text">
            暂无航线数据
          </div>
        </div>
      </div>

      <!-- 选中航线信息 -->
      <div v-if="selectedRoute" class="selected-route-card">
        <div class="card-header">
          <span class="card-icon">🎯</span>
          <span class="card-title">当前航线</span>
          <el-button size="small" text type="primary" @click="deselectRoute">取消选中</el-button>
        </div>
        <div class="selected-route-info">
          <div class="info-row">
            <span class="info-label">名称</span>
            <span class="info-value">{{ selectedRoute.name }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">距离</span>
            <span class="info-value">{{ (selectedRoute.total_distance / 1000).toFixed(1) }} km</span>
          </div>
          <div class="info-row">
            <span class="info-label">预计时间</span>
            <span class="info-value">{{ Math.ceil(selectedRoute.estimated_time / 60) }} 分钟</span>
          </div>
          <div class="info-row">
            <span class="info-label">途经点</span>
            <span class="info-value">{{ selectedRoute.waypoints?.length || 0 }} 个</span>
          </div>
        </div>
      </div>
    </aside>

    <!-- 中间地图区 -->
    <div class="map-area">
      <MapContainer ref="mapContainerRef" />

      <div v-if="selectedRoute" class="timeline-wrapper">
        <TimelineSlider
          :selected-route="selectedRoute"
          :map-ref="mapContainerRef"
          @time-change="onTimeChange"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, nextTick } from 'vue'
import { useZoneStore } from '@/stores/zones'
import { useMapStore } from '@/stores/map'
import { getAllRoutes } from '@/api/routes'
import MapContainer from '@/components/MapContainer.vue'
import WeatherPanel from '@/components/WeatherPanel.vue'
import TimelineSlider from '@/components/TimelineSlider.vue'

const zoneStore = useZoneStore()
const mapStore = useMapStore()
const apiRoutes = ref([])
const routes = computed(() => [...apiRoutes.value, ...mapStore.savedRoutes])
const selectedRoute = ref(null)
const mapContainerRef = ref(null)

const statusMap = {
  planned: '待执行',
  active: '执行中',
  completed: '已完成',
}

onMounted(async () => {
  try {
    apiRoutes.value = await getAllRoutes()
    mapStore.routeDataList = routes.value

    await nextTick()
    setTimeout(() => {
      if (mapContainerRef.value && routes.value.length > 0) {
        mapContainerRef.value.drawRoutes(routes.value)
      }
    }, 1500)
  } catch (e) {
    console.log('航线数据加载失败（可能是首次运行）')
  }
})

// 新保存的航线实时同步到地图
watch(() => mapStore.savedRoutes.length, async () => {
  mapStore.routeDataList = routes.value
  await nextTick()
  if (mapContainerRef.value && routes.value.length > 0) {
    mapContainerRef.value.drawRoutes(routes.value)
  }
})

function onSelectRoute(route) {
  if (selectedRoute.value?.id === route.id) {
    deselectRoute()
    return
  }
  selectedRoute.value = route
  mapStore.selectedRouteId = route.id

  if (mapContainerRef.value) {
    mapContainerRef.value.highlightRoute(route.id)
  }
}

function deselectRoute() {
  selectedRoute.value = null
  mapStore.selectedRouteId = null

  if (mapContainerRef.value) {
    mapContainerRef.value.resetRouteHighlight()
  }
}

function onTimeChange(timePoint) {
  // 由 TimelineSlider 内部处理
}
</script>

<style scoped>
.dashboard {
  display: flex;
  width: 100%;
  height: 100%;
}

.left-panel {
  width: 300px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow-y: auto;
  background: #f8f9fa;
  border-right: 1px solid #e5e7eb;
}

.map-area {
  flex: 1;
  position: relative;
}

.timeline-wrapper {
  position: absolute;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  width: 70%;
  z-index: 100;
}

.stats-card,
.routes-card,
.selected-route-card {
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.card-icon {
  font-size: 16px;
}

.card-title {
  font-size: 14px;
  font-weight: 600;
  color: #1f2937;
}

.route-count {
  background: #2563eb;
  color: #fff;
  font-size: 11px;
  padding: 1px 7px;
  border-radius: 10px;
  font-weight: 600;
  margin-left: auto;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
}

.stat-item {
  text-align: center;
  padding: 12px;
  background: #f9fafb;
  border-radius: 8px;
}

.stat-number {
  display: block;
  font-size: 28px;
  font-weight: 700;
  margin-bottom: 4px;
}

.stat-number.nofly {
  color: #dc2626;
}

.stat-number.heightlimit {
  color: #ea580c;
}

.stat-label {
  font-size: 12px;
  color: #9ca3af;
}

.routes-list {
  max-height: 240px;
  overflow-y: auto;
}

.route-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.15s;
  border: 1px solid transparent;
}

.route-item:hover {
  background: #f3f4f6;
}

.route-item.active {
  background: #eff6ff;
  border-color: #2563eb;
}

.route-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.route-name {
  font-size: 13px;
  color: #374151;
  font-weight: 500;
}

.route-meta {
  font-size: 11px;
  color: #9ca3af;
}

.route-status {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  font-weight: 500;
}

.route-status.active {
  background: #dcfce7;
  color: #16a34a;
}

.route-status.planned {
  background: #fef9c3;
  color: #ca8a04;
}

.route-status.completed {
  background: #e0e7ff;
  color: #4f46e5;
}

.empty-text {
  text-align: center;
  color: #9ca3af;
  font-size: 13px;
  padding: 20px;
}

/* 选中航线信息卡片 */
.selected-route-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.info-label {
  font-size: 12px;
  color: #9ca3af;
}

.info-value {
  font-size: 13px;
  color: #374151;
  font-weight: 500;
}
</style>
