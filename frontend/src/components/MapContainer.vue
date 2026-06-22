<template>
  <div class="map-wrapper">
    <!-- 2D 地图视图 (Amap) — 用 v-if 确保容器在挂载时有正确尺寸 -->
    <Amap2DView
      v-if="viewMode === '2D'"
      ref="amap2DRef"
    />

    <!-- 3D 实景视图 (Cesium) -->
    <Cesium3DView
      v-if="viewMode === '3D'"
      ref="cesium3DRef"
    />

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
import { ref, watch, nextTick } from 'vue'
import Amap2DView from './Amap2DView.vue'
import Cesium3DView from './Cesium3DView.vue'
import ZoneLegend from './ZoneLegend.vue'

const viewMode = ref('2D')
const amap2DRef = ref(null)
const cesium3DRef = ref(null)

// 缓存最后一次 drawRoutes 的参数，切换模式后重新绘制
let _lastRoutes = null
let _lastHighlightId = null

function getActive() {
  return viewMode.value === '2D' ? amap2DRef.value : cesium3DRef.value
}

function switchMode(mode) {
  if (viewMode.value === mode) return
  viewMode.value = mode
  // v-if 会销毁并重建组件，新实例挂载后重新绘制
  nextTick(() => {
    setTimeout(() => {
      const active = getActive()
      if (!active) return
      if (_lastRoutes) active.drawRoutes(_lastRoutes)
      if (_lastHighlightId != null) active.highlightRoute(_lastHighlightId)
    }, 800) // 等待地图初始化
  })
}

// 监听 amap2DRef 就绪（防止 ref 异步赋值）
watch(amap2DRef, (newRef) => {
  if (newRef && _lastRoutes) {
    setTimeout(() => {
      newRef.drawRoutes?.(_lastRoutes)
      if (_lastHighlightId != null) newRef.highlightRoute?.(_lastHighlightId)
    }, 1200)
  }
})

defineExpose({
  viewMode,
  drawRoutes: (...args) => {
    _lastRoutes = args[0]   // 缓存航线数据
    getActive()?.drawRoutes(...args)
  },
  highlightRoute: (...args) => {
    _lastHighlightId = args[0]
    getActive()?.highlightRoute(...args)
  },
  resetRouteHighlight: (...args) => {
    _lastHighlightId = null
    getActive()?.resetRouteHighlight(...args)
  },
  setDronePosition: (...args) => {
    const active = getActive()
    if (!active) console.warn('MapContainer.setDronePosition: no active child')
    else active.setDronePosition(...args)
  },
  pauseDrone: (...args) => { const a = getActive(); if (a) a.pauseDrone(...args) },
  resumeDrone: (...args) => { const a = getActive(); if (a) a.resumeDrone(...args) },
  getViewMode: () => viewMode.value,
  addClickHandler: (...args) => getActive()?.addClickHandler(...args),
  removeClickHandler: (...args) => getActive()?.removeClickHandler(...args),
  addMarker: (...args) => getActive()?.addMarker(...args),
  removeMarker: (...args) => getActive()?.removeMarker(...args),
  clearCustomMarkers: (...args) => getActive()?.clearCustomMarkers(...args),
  drawPlanPath: (...args) => getActive()?.drawPlanPath(...args),
  clearPlanPath: (...args) => getActive()?.clearPlanPath(...args),
  startDrawLine: (...args) => getActive()?.startDrawLine(...args),
  startDrawPolygon: (...args) => getActive()?.startDrawPolygon(...args),
  stopDrawing: (...args) => getActive()?.stopDrawing(...args),
  clearDrawing: (...args) => getActive()?.clearDrawing(...args),
  getViewer: () => getActive()?.getViewer?.() || null,
})
</script>

<style scoped>
.map-wrapper {
  position: relative;
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
