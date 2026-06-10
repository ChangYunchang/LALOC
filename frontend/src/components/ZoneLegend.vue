<template>
  <div class="zone-legend">
    <div class="legend-title">图例</div>
    <div class="legend-item">
      <span class="legend-color" style="background: rgba(252, 165, 165, 0.5); border-color: #dc2626;"></span>
      <span>禁飞区</span>
      <span class="legend-count">{{ zoneStore.stats.no_fly_zones_count }}</span>
    </div>
    <div class="legend-item">
      <span class="legend-color" style="background: rgba(253, 186, 116, 0.4); border-color: #ea580c;"></span>
      <span>限高区</span>
      <span class="legend-count">{{ zoneStore.stats.height_limit_zones_count }}</span>
    </div>
    <div class="legend-divider"></div>
    <div class="legend-group-title">飞行阶段</div>
    <div class="legend-item">
      <span class="legend-line" style="background: #22c55e;"></span>
      <span>爬升段</span>
    </div>
    <div class="legend-item">
      <span class="legend-line" style="background: #3b82f6;"></span>
      <span>巡航段</span>
    </div>
    <div class="legend-item">
      <span class="legend-line" style="background: #f59e0b;"></span>
      <span>下降段</span>
    </div>
    <div class="legend-item">
      <span class="legend-line" style="background: #ef4444;"></span>
      <span>限高区飞行</span>
    </div>
    <div class="legend-item">
      <span class="legend-line" style="background: #a855f7;"></span>
      <span>建筑避让</span>
    </div>
    <div class="legend-divider"></div>
    <div class="legend-item">
      <span class="legend-dot" style="background: #16a34a;"></span>
      <span>无人机</span>
    </div>
  </div>
</template>

<script setup>
import { useZoneStore } from '@/stores/zones'
const zoneStore = useZoneStore()
</script>

<style scoped>
.zone-legend {
  position: absolute;
  bottom: 35px;
  right: 15px;
  background: rgba(255, 255, 255, 0.95);
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 12px 16px;
  z-index: 100;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.legend-title {
  font-size: 12px;
  color: #9ca3af;
  margin-bottom: 8px;
  font-weight: 600;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
  font-size: 13px;
  color: #374151;
}

.legend-item:last-child {
  margin-bottom: 0;
}

.legend-group-title {
  font-size: 11px;
  font-weight: 600;
  color: #6b7280;
  margin-bottom: 4px;
}

.legend-divider {
  height: 1px;
  background: #e5e7eb;
  margin: 6px 0;
}

.legend-color {
  width: 16px;
  height: 16px;
  border-radius: 4px;
  border: 2px solid;
}

.legend-line {
  width: 20px;
  height: 3px;
  border-radius: 2px;
}

.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  margin: 0 5px;
}

.legend-count {
  margin-left: auto;
  font-size: 12px;
  color: #2563eb;
  font-weight: 600;
}
</style>
