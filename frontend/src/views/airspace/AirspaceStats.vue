<!--
  2.4 空域资源统计
  展示禁飞区/限高区数量、面积和类型占比
-->
<template>
  <PageLayout title="空域资源统计" subtitle="空域限制区域数量、面积与类型分布统计">
    <div v-loading="loading">
      <!-- 核心指标卡 -->
      <el-row :gutter="16" style="margin-bottom:20px">
        <el-col :span="8">
          <div class="stat-card red">
            <div class="stat-value">{{ stats.no_fly_zones?.count ?? '-' }}</div>
            <div class="stat-label">禁飞区数量</div>
            <div class="stat-sub">{{ stats.no_fly_zones?.area_km2 ?? '-' }} km²</div>
          </div>
        </el-col>
        <el-col :span="8">
          <div class="stat-card orange">
            <div class="stat-value">{{ stats.height_limit_zones?.count ?? '-' }}</div>
            <div class="stat-label">限高区数量</div>
            <div class="stat-sub">{{ stats.height_limit_zones?.area_km2 ?? '-' }} km²</div>
          </div>
        </el-col>
        <el-col :span="8">
          <div class="stat-card blue">
            <div class="stat-value">{{ stats.total?.count ?? '-' }}</div>
            <div class="stat-label">限制区总数</div>
            <div class="stat-sub">共 {{ stats.total?.area_km2 ?? '-' }} km²</div>
          </div>
        </el-col>
      </el-row>

      <!-- 图表区 -->
      <el-row :gutter="20">
        <el-col :span="12">
          <el-card header="区域类型占比（面积）">
            <div ref="pieChart" style="height:300px"></div>
          </el-card>
        </el-col>
        <el-col :span="12">
          <el-card header="区域数量对比">
            <div ref="barChart" style="height:300px"></div>
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

const loading = ref(false)
const stats = ref({})
const pieChart = ref()
const barChart = ref()

async function fetchStats() {
  loading.value = true
  try {
    const { data } = await axios.get('/api/airspace/stats')
    stats.value = data
    await nextTick()
    renderCharts(data)
  } catch {
    ElMessage.error('获取统计数据失败')
  } finally {
    loading.value = false
  }
}

function renderCharts(data) {
  // 饼图
  const pie = echarts.init(pieChart.value)
  pie.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: {c} km² ({d}%)' },
    legend: { bottom: 0 },
    series: [{
      type: 'pie', radius: ['40%', '70%'],
      data: [
        { name: '禁飞区', value: data.no_fly_zones?.area_km2 ?? 0, itemStyle: { color: '#dc2626' } },
        { name: '限高区', value: data.height_limit_zones?.area_km2 ?? 0, itemStyle: { color: '#f59e0b' } },
      ],
      label: { formatter: '{b}\n{d}%' },
    }],
  })

  // 柱状图
  const bar = echarts.init(barChart.value)
  bar.setOption({
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: ['禁飞区', '限高区'] },
    yAxis: [
      { type: 'value', name: '数量', position: 'left' },
      { type: 'value', name: '面积(km²)', position: 'right' },
    ],
    series: [
      {
        name: '数量', type: 'bar', yAxisIndex: 0, barWidth: '30%',
        data: [data.no_fly_zones?.count ?? 0, data.height_limit_zones?.count ?? 0],
        itemStyle: { color: '#3b82f6' },
      },
      {
        name: '面积(km²)', type: 'line', yAxisIndex: 1,
        data: [data.no_fly_zones?.area_km2 ?? 0, data.height_limit_zones?.area_km2 ?? 0],
        itemStyle: { color: '#16a34a' },
      },
    ],
  })
}

onMounted(fetchStats)
</script>

<style scoped>
.stat-card {
  padding: 24px 20px; border-radius: 10px; text-align: center; color: #fff;
}
.stat-card.red { background: linear-gradient(135deg, #dc2626, #ef4444); }
.stat-card.orange { background: linear-gradient(135deg, #d97706, #f59e0b); }
.stat-card.blue { background: linear-gradient(135deg, #2563eb, #3b82f6); }
.stat-value { font-size: 36px; font-weight: 700; }
.stat-label { font-size: 14px; opacity: 0.9; margin: 4px 0; }
.stat-sub { font-size: 13px; opacity: 0.75; }
</style>
