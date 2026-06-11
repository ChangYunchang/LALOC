<!--
  7.1 城市运行统计
-->
<template>
  <PageLayout title="城市运行统计" subtitle="城市低空物流整体运行情况统计分析">
    <div v-loading="loading">
      <!-- 核心指标 -->
      <el-row :gutter="16" style="margin-bottom:20px">
        <el-col :span="6" v-for="c in cards" :key="c.label">
          <div class="metric-card" :style="{ '--accent': c.color }">
            <div class="metric-icon"><el-icon :size="22"><component :is="c.icon" /></el-icon></div>
            <div class="metric-body">
              <div class="metric-val">{{ c.value }}</div>
              <div class="metric-lbl">{{ c.label }}</div>
            </div>
            <div class="metric-badge" v-if="c.sub">{{ c.sub }}</div>
          </div>
        </el-col>
      </el-row>

      <el-row :gutter="16">
        <el-col :span="14">
          <el-card header="近7天飞行任务趋势">
            <div ref="trendChart" style="height:280px"></div>
          </el-card>
        </el-col>
        <el-col :span="10">
          <el-card header="航线利用率 Top 10">
            <div ref="routeChart" style="height:280px"></div>
          </el-card>
        </el-col>
      </el-row>
    </div>
  </PageLayout>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { Promotion, Van, Connection, Warning } from '@element-plus/icons-vue'
import axios from 'axios'
import * as echarts from 'echarts'
import PageLayout from '@/components/PageLayout.vue'

const loading = ref(false)
const cards = ref([])
const trendChart = ref(), routeChart = ref()

async function fetchAll() {
  loading.value = true
  try {
    const [ovr, trend, routes] = await Promise.all([
      axios.get('/api/statistics/city/overview'),
      axios.get('/api/statistics/city/tasks-trend', { params: { days: 7 } }),
      axios.get('/api/statistics/city/route-utilization'),
    ])
    const d = ovr.data
    cards.value = [
      { label: '飞行任务总数', value: d.tasks.total, sub: `完成率 ${d.tasks.completion_rate}%`, color: '#3b82f6', icon: 'Promotion' },
      { label: '配送订单总数', value: d.orders.total, color: '#16a34a', icon: 'Van' },
      { label: '无人机利用率', value: `${d.drones.utilization}%`, sub: `共 ${d.drones.total} 架`, color: '#8b5cf6', icon: 'Connection' },
      { label: '待处理事件', value: d.events.open, sub: `历史共 ${d.events.total}`, color: '#f59e0b', icon: 'Warning' },
    ]
    await nextTick()
    renderTrend(trend.data)
    renderRoutes(routes.data)
  } catch { ElMessage.error('获取统计数据失败') }
  finally { loading.value = false }
}

function renderTrend(data) {
  const chart = echarts.init(trendChart.value)
  chart.setOption({
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: data.map(d => d.date) },
    yAxis: { type: 'value', name: '任务数' },
    series: [{
      name: '飞行任务', type: 'bar', data: data.map(d => d.count),
      itemStyle: { color: '#3b82f6', borderRadius: [4, 4, 0, 0] },
    }],
    grid: { left: 40, right: 16, top: 20, bottom: 30 },
  })
}

function renderRoutes(data) {
  const chart = echarts.init(routeChart.value)
  chart.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    xAxis: { type: 'value' },
    yAxis: { type: 'category', data: data.slice(0, 10).map(r => r.route_name?.slice(0, 8) || `R${r.route_id}`), inverse: true },
    series: [{
      name: '使用次数', type: 'bar', data: data.slice(0, 10).map(r => r.use_count),
      itemStyle: { color: '#16a34a', borderRadius: [0, 4, 4, 0] },
    }],
    grid: { left: 80, right: 30, top: 10, bottom: 30 },
  })
}

onMounted(fetchAll)
</script>

<style scoped>
.metric-card {
  display: flex; align-items: center; gap: 14px;
  background: #fff; padding: 18px 20px; border-radius: 10px;
  border-left: 4px solid var(--accent);
  box-shadow: 0 1px 4px rgba(0,0,0,.06);
}
.metric-icon { width: 44px; height: 44px; border-radius: 50%; background: color-mix(in srgb, var(--accent) 12%, white); display: flex; align-items: center; justify-content: center; color: var(--accent); flex-shrink: 0; }
.metric-val { font-size: 26px; font-weight: 700; color: var(--text-primary); line-height: 1; }
.metric-lbl { font-size: 12px; color: var(--text-secondary); margin-top: 4px; }
.metric-badge { margin-left: auto; font-size: 11px; color: var(--text-secondary); white-space: nowrap; }
</style>
