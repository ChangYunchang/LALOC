<!--
  7.5 配送站布局分析
-->
<template>
  <PageLayout title="配送站布局分析" subtitle="分析配送站服务覆盖与需求热点，提供布局优化建议">
    <div v-loading="loading">
      <el-row :gutter="16">
        <el-col :span="14">
          <el-card header="配送站负荷与服务覆盖">
            <div ref="barChart" style="height:280px"></div>
          </el-card>
        </el-col>
        <el-col :span="10">
          <el-card header="需求热点与优化建议">
            <div class="section-label">需求热点区域</div>
            <el-table :data="hotspots" size="small" border style="margin-bottom:16px">
              <el-table-column prop="area" label="区域" />
              <el-table-column prop="demand_index" label="需求指数" width="90">
                <template #default="{ row }">
                  <el-progress :percentage="row.demand_index" :stroke-width="8" />
                </template>
              </el-table-column>
            </el-table>
            <div class="section-label">布局优化建议</div>
            <div v-for="(hint, i) in hints" :key="i" class="hint-item">
              <el-icon><InfoFilled /></el-icon>
              <span>{{ hint }}</span>
            </div>
            <el-divider />
            <div class="coverage-row">
              <span>当前城区覆盖率</span>
              <el-progress :percentage="coverageRate" :stroke-width="12" style="width:140px" />
            </div>
          </el-card>
        </el-col>
      </el-row>
    </div>
  </PageLayout>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { InfoFilled } from '@element-plus/icons-vue'
import axios from 'axios'
import * as echarts from 'echarts'
import PageLayout from '@/components/PageLayout.vue'

const loading = ref(false), hotspots = ref([]), hints = ref([]), coverageRate = ref(0)
const barChart = ref()

async function fetchData() {
  loading.value = true
  try {
    const { data } = await axios.get('/api/statistics/station/layout')
    hotspots.value = data.demand_hotspots || []
    hints.value = data.optimization_hints || []
    coverageRate.value = data.coverage_rate || 0
    await nextTick()
    renderChart(data.stations || [])
  } catch { ElMessage.error('获取数据失败') } finally { loading.value = false }
}

function renderChart(stations) {
  const chart = echarts.init(barChart.value)
  chart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { bottom: 0 },
    xAxis: { type: 'category', data: stations.map(s => s.name?.slice(0, 6) || `S${s.id}`), axisLabel: { rotate: 20, fontSize: 11 } },
    yAxis: [
      { type: 'value', name: '任务数', position: 'left' },
      { type: 'value', name: '负荷率(%)', position: 'right', max: 100 },
    ],
    series: [
      { name: '承接任务数', type: 'bar', yAxisIndex: 0, data: stations.map(s => s.task_count), itemStyle: { color: '#3b82f6', borderRadius: [3, 3, 0, 0] } },
      { name: '负荷率', type: 'line', yAxisIndex: 1, data: stations.map(s => s.load_rate), smooth: true, itemStyle: { color: '#dc2626' } },
    ],
    grid: { left: 40, right: 50, top: 16, bottom: 60 },
  })
}
onMounted(fetchData)
</script>

<style scoped>
.section-label { font-weight: 600; font-size: 13px; margin-bottom: 8px; }
.hint-item { display: flex; align-items: flex-start; gap: 6px; font-size: 13px; color: #374151; margin-bottom: 8px; line-height: 1.5; }
.coverage-row { display: flex; align-items: center; gap: 16px; font-size: 13px; }
</style>
