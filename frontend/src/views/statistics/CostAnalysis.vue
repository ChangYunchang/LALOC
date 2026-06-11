<!--
  7.4 能耗成本分析
-->
<template>
  <PageLayout title="能耗成本分析" subtitle="分析无人机配送任务的能源消耗和单位运营成本">
    <div v-loading="loading">
      <el-row :gutter="16">
        <el-col :span="14">
          <el-card header="近7天成本与能耗趋势">
            <div ref="trendChart" style="height:280px"></div>
          </el-card>
        </el-col>
        <el-col :span="10">
          <el-card header="各企业成本对比">
            <el-table :data="byEnterprise" size="small" border>
              <el-table-column prop="enterprise_name" label="企业" min-width="100" show-overflow-tooltip />
              <el-table-column prop="completed_tasks" label="完成任务" width="90" />
              <el-table-column prop="energy_kwh" label="能耗(kWh)" width="95" />
              <el-table-column prop="unit_cost" label="单位成本(元)" width="110" />
            </el-table>
          </el-card>
        </el-col>
      </el-row>
    </div>
  </PageLayout>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'
import * as echarts from 'echarts'
import PageLayout from '@/components/PageLayout.vue'

const loading = ref(false), byEnterprise = ref([])
const trendChart = ref()

async function fetchData() {
  loading.value = true
  try {
    const { data } = await axios.get('/api/statistics/cost/analysis')
    byEnterprise.value = data.by_enterprise || []
    await nextTick()
    renderTrend(data.trend || [])
  } catch { ElMessage.error('获取数据失败') } finally { loading.value = false }
}

function renderTrend(data) {
  const chart = echarts.init(trendChart.value)
  chart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { bottom: 0 },
    xAxis: { type: 'category', data: data.map(d => d.date) },
    yAxis: [
      { type: 'value', name: '成本(元)', position: 'left' },
      { type: 'value', name: '能耗(kWh)', position: 'right' },
    ],
    series: [
      { name: '成本', type: 'bar', yAxisIndex: 0, data: data.map(d => d.cost), itemStyle: { color: '#3b82f6', borderRadius: [3, 3, 0, 0] } },
      { name: '能耗', type: 'line', yAxisIndex: 1, data: data.map(d => d.energy), smooth: true, itemStyle: { color: '#f59e0b' } },
    ],
    grid: { left: 50, right: 50, top: 20, bottom: 50 },
  })
}
onMounted(fetchData)
</script>
