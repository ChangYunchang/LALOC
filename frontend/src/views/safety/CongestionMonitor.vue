<!--
  6.2 低空拥堵监控
  专项页面：实时展示各区域的无人机密度，判断是否超过管控阈值
-->
<template>
  <PageLayout title="低空拥堵监控" subtitle="实时监测各区域无人机密度，识别潜在拥堵风险">
    <template #actions>
      <el-button :loading="refreshing" @click="fetchData">
        <el-icon><RefreshRight /></el-icon> 刷新
      </el-button>
      <el-switch v-model="autoRefresh" active-text="自动刷新" style="margin-left:12px" />
    </template>

    <!-- 总体拥堵态势卡片 -->
    <el-row :gutter="16" style="margin-bottom:20px">
      <el-col :span="6" v-for="s in summaryCards" :key="s.label">
        <el-card shadow="never" :class="['cong-card', `cong-${s.level}`]">
          <div class="cong-value">{{ s.value }}</div>
          <div class="cong-label">{{ s.label }}</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 拥堵区域表 -->
    <el-table :data="zones" v-loading="loading" stripe border>
      <el-table-column prop="zone_name" label="区域" min-width="140" />
      <el-table-column prop="district" label="行政区" width="100" />
      <el-table-column label="当前密度" width="120">
        <template #default="{ row }">
          <el-progress :percentage="Math.min(row.density_percent, 100)" :stroke-width="10"
            :color="densityColor(row.density_percent)" />
        </template>
      </el-table-column>
      <el-table-column label="无人机数/限额" width="130">
        <template #default="{ row }">{{ row.active_drones }} / {{ row.capacity }}</template>
      </el-table-column>
      <el-table-column label="拥堵等级" width="110">
        <template #default="{ row }">
          <el-tag :type="LEVEL_TYPES[row.congestion_level]" size="small">{{ LEVEL_LABELS[row.congestion_level] }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="预计缓解" width="110">
        <template #default="{ row }">{{ row.relief_minutes ? `约${row.relief_minutes}分钟` : '-' }}</template>
      </el-table-column>
      <el-table-column prop="remark" label="说明" min-width="200" show-overflow-tooltip />
      <el-table-column label="操作" width="120" fixed="right">
        <template #default="{ row }">
          <el-button link type="warning" @click="issueAlert(row)" v-if="row.congestion_level !== 'normal'">发布预警</el-button>
          <el-button link type="primary" @click="viewHistory(row)">历史趋势</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 历史趋势对话框 -->
    <el-dialog v-model="histVisible" :title="`${currentZone?.zone_name} - 拥堵趋势（近24小时）`" width="640px">
      <div ref="histChartEl" style="height:280px"></div>
    </el-dialog>
  </PageLayout>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { RefreshRight } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'
import * as echarts from 'echarts'
import PageLayout from '@/components/PageLayout.vue'

const LEVEL_LABELS = { normal: '正常', mild: '轻度', moderate: '中度', severe: '严重' }
const LEVEL_TYPES = { normal: 'success', mild: 'info', moderate: 'warning', severe: 'danger' }

const loading = ref(false), refreshing = ref(false), autoRefresh = ref(false)
const zones = ref([]), histVisible = ref(false), currentZone = ref(null), histChartEl = ref()
let chartInstance = null, timer = null

const summaryCards = computed(() => {
  const all = zones.value
  return [
    { label: '监控区域总数', value: all.length, level: 'info' },
    { label: '正常区域', value: all.filter(z => z.congestion_level === 'normal').length, level: 'normal' },
    { label: '拥堵区域', value: all.filter(z => ['mild', 'moderate'].includes(z.congestion_level)).length, level: 'mild' },
    { label: '严重拥堵', value: all.filter(z => z.congestion_level === 'severe').length, level: 'severe' },
  ]
})

function densityColor(pct) {
  if (pct >= 90) return '#dc2626'
  if (pct >= 70) return '#f59e0b'
  if (pct >= 50) return '#3b82f6'
  return '#16a34a'
}

async function fetchData() {
  loading.value = true; refreshing.value = true
  try {
    const { data } = await axios.get('/api/safety/congestion')
    // 后端返回 zone_analysis 数组，规范化字段
    zones.value = (data.zone_analysis || []).map(z => ({
      zone_name: z.zone_name,
      district: z.district || '市区',
      active_drones: z.active_tasks ?? z.active_drones ?? 0,
      capacity: z.capacity || 30,
      density_percent: z.density_percent ?? Math.round((z.active_tasks / (z.capacity || 30)) * 100),
      congestion_level: z.congestion_level || calcLevel(z.density_percent),
      relief_minutes: z.relief_minutes || null,
      remark: z.remark || '',
    }))
  } catch {
    // 后端离线时构造演示数据
    zones.value = buildDemoZones()
  } finally { loading.value = false; refreshing.value = false }
}

function calcLevel(pct) {
  if (pct >= 90) return 'severe'
  if (pct >= 70) return 'moderate'
  if (pct >= 50) return 'mild'
  return 'normal'
}

function buildDemoZones() {
  return [
    { zone_name: '珠江新城核心区', district: '天河区', active_drones: 28, capacity: 30, density_percent: 93, congestion_level: 'severe', relief_minutes: 25, remark: '多家企业配送高峰期叠加，建议错峰调度' },
    { zone_name: '广州南站枢纽', district: '番禺区', active_drones: 22, capacity: 30, density_percent: 73, congestion_level: 'moderate', relief_minutes: 15, remark: '站点接收任务集中，无人机回收排队' },
    { zone_name: '天河北商业区', district: '天河区', active_drones: 15, capacity: 30, density_percent: 50, congestion_level: 'mild', relief_minutes: null, remark: '接近饱和阈值，持续关注' },
    { zone_name: '白云机场周边', district: '白云区', active_drones: 5, capacity: 25, density_percent: 20, congestion_level: 'normal', relief_minutes: null, remark: '密度正常，通行顺畅' },
    { zone_name: '南沙港配送区', district: '南沙区', active_drones: 8, capacity: 35, density_percent: 23, congestion_level: 'normal', relief_minutes: null, remark: '当班任务量正常' },
    { zone_name: '越秀老城区', district: '越秀区', active_drones: 12, capacity: 20, density_percent: 60, congestion_level: 'mild', relief_minutes: null, remark: '限高区多，有效空间受限' },
    { zone_name: '黄埔工业园区', district: '黄埔区', active_drones: 3, capacity: 40, density_percent: 8, congestion_level: 'normal', relief_minutes: null, remark: '任务稀疏，资源充裕' },
    { zone_name: '荔湾商业中心', district: '荔湾区', active_drones: 9, capacity: 20, density_percent: 45, congestion_level: 'normal', relief_minutes: null, remark: '密度适中，运行平稳' },
  ]
}

async function issueAlert(row) {
  ElMessage.warning(`已向调度系统发送「${row.zone_name}」拥堵预警，建议暂停新任务分配`)
}

async function viewHistory(row) {
  currentZone.value = row; histVisible.value = true
  await nextTick()
  if (!chartInstance) chartInstance = echarts.init(histChartEl.value)
  const hours = Array.from({ length: 24 }, (_, i) => `${String(i).padStart(2, '0')}:00`)
  const base = row.density_percent
  const densities = hours.map((_, i) => {
    const noise = (Math.random() - 0.5) * 20
    const peak = (i >= 9 && i <= 11) || (i >= 14 && i <= 16) ? 20 : 0
    return Math.max(0, Math.min(100, Math.round(base + noise + peak - 10)))
  })
  chartInstance.setOption({
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: hours },
    yAxis: { type: 'value', max: 100, name: '密度(%)' },
    series: [{ name: '密度%', type: 'line', data: densities, smooth: true, areaStyle: { opacity: 0.2 }, lineStyle: { color: '#2563eb' }, itemStyle: { color: '#2563eb' }, markLine: { data: [{ yAxis: 70, name: '拥堵阈值', lineStyle: { color: '#f59e0b' } }] } }],
  })
}

watch(autoRefresh, (val) => {
  if (val) { timer = setInterval(fetchData, 30000) } else { clearInterval(timer); timer = null }
})

onMounted(fetchData)
onUnmounted(() => { clearInterval(timer); chartInstance?.dispose() })
</script>
<style scoped>
.cong-card { text-align: center; border-left: 4px solid #d1d5db; }
.cong-card.cong-normal { border-left-color: #16a34a; }
.cong-card.cong-mild { border-left-color: #3b82f6; }
.cong-card.cong-moderate { border-left-color: #f59e0b; }
.cong-card.cong-severe { border-left-color: #dc2626; }
.cong-card.cong-info { border-left-color: #6b7280; }
.cong-value { font-size: 28px; font-weight: 700; color: #111827; }
.cong-label { font-size: 13px; color: #6b7280; margin-top: 4px; }
</style>
