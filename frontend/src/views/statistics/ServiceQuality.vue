<!--
  7.3 配送服务质量分析
-->
<template>
  <PageLayout title="配送服务质量分析" subtitle="分析失败原因、服务评分，识别质量改进点">
    <div v-loading="loading">
      <el-row :gutter="16" style="margin-bottom:16px">
        <el-col :span="6" v-for="c in cards" :key="c.label">
          <div class="kpi-card">
            <div class="kpi-val" :style="{ color: c.color }">{{ c.value }}</div>
            <div class="kpi-lbl">{{ c.label }}</div>
          </div>
        </el-col>
      </el-row>
      <el-row :gutter="16">
        <el-col :span="12">
          <el-card header="配送失败原因分布">
            <div ref="pieChart" style="height:300px"></div>
          </el-card>
        </el-col>
        <el-col :span="12">
          <el-card header="失败原因统计">
            <el-table :data="reasons" size="small" border>
              <el-table-column prop="reason" label="原因" />
              <el-table-column prop="count" label="数量" width="80" />
              <el-table-column label="占比" width="100">
                <template #default="{ row }">
                  <el-progress :percentage="row.percent" :stroke-width="8" />
                </template>
              </el-table-column>
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

const loading = ref(false), cards = ref([]), reasons = ref([])
const pieChart = ref()

async function fetchData() {
  loading.value = true
  try {
    const { data } = await axios.get('/api/statistics/service/quality')
    reasons.value = data.failure_reasons || []
    cards.value = [
      { label: '订单总数', value: data.total_orders, color: '#3b82f6' },
      { label: '失败任务', value: data.failed_tasks, color: '#dc2626' },
      { label: '失败率', value: data.failure_rate + '%', color: '#f59e0b' },
      { label: '平均服务评分', value: data.avg_delivery_score + '⭐', color: '#16a34a' },
    ]
    await nextTick()
    renderPie(data.failure_reasons)
  } catch { ElMessage.error('获取数据失败') } finally { loading.value = false }
}

function renderPie(data) {
  if (!data?.length) return
  const chart = echarts.init(pieChart.value)
  chart.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: {c}次 ({d}%)' },
    legend: { bottom: 0 },
    series: [{
      type: 'pie', radius: ['38%', '65%'],
      data: data.map(d => ({ name: d.reason, value: d.count })),
      label: { formatter: '{b}\n{d}%' },
    }],
  })
}
onMounted(fetchData)
</script>

<style scoped>
.kpi-card { background: #fff; border-radius: 10px; padding: 20px; text-align: center; box-shadow: 0 1px 4px rgba(0,0,0,.06); }
.kpi-val { font-size: 28px; font-weight: 700; }
.kpi-lbl { font-size: 12px; color: var(--text-secondary); margin-top: 4px; }
</style>
