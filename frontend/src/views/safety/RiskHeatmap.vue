<!--
  6.3 安全风险热力分析
  在地图上叠加风险热力图
-->
<template>
  <PageLayout title="安全风险热力分析" subtitle="综合异常事件密度生成低空安全风险空间分布热力图">
    <template #actions>
      <el-button @click="fetchHeatData" :loading="loading">刷新数据</el-button>
    </template>

    <el-row :gutter="16">
      <el-col :span="16">
        <el-card style="padding:0">
          <div ref="mapEl" style="height:520px; border-radius:8px"></div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card header="风险说明">
          <div class="legend">
            <div class="legend-item" v-for="l in LEGEND" :key="l.label">
              <span class="legend-dot" :style="{ background: l.color }"></span>
              <span>{{ l.label }}</span>
            </div>
          </div>
          <el-divider />
          <div v-if="stats" class="stat-block">
            <div class="stat-row"><span>事件总数</span><strong>{{ stats.event_count }}</strong></div>
            <div class="stat-row"><span>热力点</span><strong>{{ stats.heat_points?.length }}</strong></div>
          </div>
          <div class="tips">
            <el-icon><InfoFilled /></el-icon>
            热力图颜色越深，表示该区域近30天内异常事件密度越高，建议加强该区域飞行监管。
          </div>
        </el-card>
      </el-col>
    </el-row>
  </PageLayout>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { InfoFilled } from '@element-plus/icons-vue'
import axios from 'axios'
import AMapLoader from '@amap/amap-jsapi-loader'
import PageLayout from '@/components/PageLayout.vue'

const LEGEND = [
  { color: '#22c55e', label: '低风险' },
  { color: '#eab308', label: '中风险' },
  { color: '#f97316', label: '较高风险' },
  { color: '#ef4444', label: '高风险' },
]

const loading = ref(false)
const mapEl = ref()
const stats = ref(null)
let mapInstance = null
let heatmapLayer = null

const AMAP_KEY = import.meta.env.VITE_AMAP_KEY || ''
const AMAP_SECURITY = import.meta.env.VITE_AMAP_SECURITY_CODE || ''

async function initMap() {
  window._AMapSecurityConfig = { securityJsCode: AMAP_SECURITY }
  const AMap = await AMapLoader.load({
    key: AMAP_KEY,
    version: '2.0',
    plugins: ['AMap.HeatMap'],
  })
  mapInstance = new AMap.Map(mapEl.value, {
    center: [113.2644, 23.1291],
    zoom: 11,
    mapStyle: 'amap://styles/whitesmoke',
  })
  heatmapLayer = new AMap.HeatMap(mapInstance, {
    radius: 35, opacity: [0, 0.8],
    gradient: { 0.4: '#22c55e', 0.6: '#eab308', 0.8: '#f97316', 1.0: '#ef4444' },
  })
  await fetchHeatData()
}

async function fetchHeatData() {
  loading.value = true
  try {
    const { data } = await axios.get('/api/safety/risk-heatmap')
    stats.value = data
    if (heatmapLayer && data.heat_points) {
      const points = data.heat_points.map(p => ({ lng: p.lng, lat: p.lat, count: p.weight * 100 }))
      heatmapLayer.setDataSet({ data: points, max: 100 })
    }
  } catch { ElMessage.error('获取热力数据失败') }
  finally { loading.value = false }
}

onMounted(initMap)
onUnmounted(() => { mapInstance?.destroy() })
</script>

<style scoped>
.legend { display: flex; flex-direction: column; gap: 10px; }
.legend-item { display: flex; align-items: center; gap: 10px; font-size: 13px; }
.legend-dot { width: 14px; height: 14px; border-radius: 50%; flex-shrink: 0; }
.stat-block { display: flex; flex-direction: column; gap: 8px; }
.stat-row { display: flex; justify-content: space-between; font-size: 13px; }
.tips { margin-top: 16px; font-size: 12px; color: #6b7280; display: flex; gap: 6px; line-height: 1.5; }
</style>
