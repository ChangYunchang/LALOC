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
        </div>
        <div class="routes-list">
          <div
            v-for="route in routes"
            :key="route.id"
            class="route-item"
            @click="highlightRoute(route)"
          >
            <span class="route-name">{{ route.name }}</span>
            <span class="route-distance">{{ (route.total_distance / 1000).toFixed(1) }}km</span>
          </div>
          <div v-if="routes.length === 0" class="empty-text">
            暂无航线数据
          </div>
        </div>
      </div>
    </aside>

    <!-- 中间地图区 -->
    <div class="map-area">
      <MapContainer />

      <div class="timeline-wrapper">
        <TimelineSlider @time-change="onTimeChange" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useZoneStore } from '@/stores/zones'
import { useMapStore } from '@/stores/map'
import { getAllRoutes } from '@/api/routes'
import MapContainer from '@/components/MapContainer.vue'
import WeatherPanel from '@/components/WeatherPanel.vue'
import TimelineSlider from '@/components/TimelineSlider.vue'

const zoneStore = useZoneStore()
const mapStore = useMapStore()
const routes = ref([])

onMounted(async () => {
  try {
    routes.value = await getAllRoutes()
  } catch (e) {
    console.log('航线数据加载失败（可能是首次运行）')
  }
})

function highlightRoute(route) {
  console.log('选中航线:', route.name)
}

function onTimeChange(timePoint) {
  console.log('时间变化:', timePoint.label)
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
.routes-card {
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
  max-height: 200px;
  overflow-y: auto;
}

.route-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.15s;
}

.route-item:hover {
  background: #f3f4f6;
}

.route-name {
  font-size: 13px;
  color: #374151;
}

.route-distance {
  font-size: 12px;
  color: #2563eb;
  font-weight: 500;
}

.empty-text {
  text-align: center;
  color: #9ca3af;
  font-size: 13px;
  padding: 20px;
}
</style>
