<!--
  7.2 企业运营效率分析
-->
<template>
  <PageLayout title="企业运营效率分析" subtitle="分析各物流企业任务完成率、准点率和无人机利用率">
    <div v-loading="loading">
      <el-row :gutter="16" style="margin-bottom:16px">
        <el-col :span="14">
          <el-card header="各企业运营效率对比">
            <div ref="barChart" style="height:320px"></div>
          </el-card>
        </el-col>
        <el-col :span="10">
          <el-card header="企业详细数据">
            <el-table :data="tableData" size="small" border>
              <el-table-column prop="enterprise_name" label="企业" min-width="130" show-overflow-tooltip />
              <el-table-column prop="completion_rate" label="完成率(%)" width="95">
                <template #default="{ row }">
                  <el-progress :percentage="row.completion_rate" :stroke-width="8" :format="(v) => v + '%'" />
                </template>
              </el-table-column>
              <el-table-column prop="on_time_rate" label="准点率(%)" width="80" />
              <el-table-column prop="drone_utilization" label="无人机利用率(%)" width="110" />
              <el-table-column prop="anomaly_count" label="异常数" width="75" />
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

const loading = ref(false), tableData = ref([])
const barChart = ref()

async function fetchData() {
  loading.value = true
  try {
    const { data } = await axios.get('/api/statistics/enterprise/efficiency')
    tableData.value = data
    await nextTick()
    renderChart(data)
  } catch { ElMessage.error('获取数据失败') } finally { loading.value = false }
}

function renderChart(data) {
  const chart = echarts.init(barChart.value)
  const names = data.map(d => d.enterprise_name.slice(0, 6))
  chart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { bottom: 0, textStyle: { fontSize: 11 } },
    xAxis: { type: 'category', data: names, axisLabel: { rotate: 15, fontSize: 11 } },
    yAxis: { type: 'value', max: 100, axisLabel: { formatter: '{value}%' } },
    series: [
      { name: '任务完成率', type: 'bar', barWidth: '20%', data: data.map(d => d.completion_rate), itemStyle: { color: '#3b82f6', borderRadius: [3, 3, 0, 0] } },
      { name: '准点率', type: 'bar', barWidth: '20%', data: data.map(d => d.on_time_rate), itemStyle: { color: '#16a34a', borderRadius: [3, 3, 0, 0] } },
      { name: '无人机利用率', type: 'bar', barWidth: '20%', data: data.map(d => d.drone_utilization), itemStyle: { color: '#f59e0b', borderRadius: [3, 3, 0, 0] } },
    ],
    grid: { left: 40, right: 16, top: 16, bottom: 60 },
  })
}
onMounted(fetchData)
</script>
