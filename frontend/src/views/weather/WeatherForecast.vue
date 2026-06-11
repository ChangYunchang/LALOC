<!--
  4.3 气象预报查询
-->
<template>
  <PageLayout title="气象预报查询" subtitle="查询未来天气变化，为任务安排和飞行计划提供参考">
    <el-card style="margin-bottom:16px">
      <el-form inline>
        <el-form-item label="查询城市">
          <el-input v-model="city" placeholder="广州" style="width:150px" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="fetchForecast" :loading="loading">查询预报</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <div v-if="forecast.length">
      <el-row :gutter="12">
        <el-col :span="6" v-for="f in forecast" :key="f.date">
          <el-card class="forecast-card" :class="{ 'no-fly': !f.flyable }">
            <div class="f-date">{{ f.date }}</div>
            <div class="f-week">{{ f.week }}</div>
            <div class="f-weather">{{ f.dayWeather }}</div>
            <div class="f-temp">{{ f.nightTemp }}℃ ～ {{ f.dayTemp }}℃</div>
            <div class="f-wind">{{ f.dayWindDirection }} {{ f.dayWindPower }}级</div>
            <div class="f-badge" :class="f.flyable ? 'ok' : 'no'">
              {{ f.flyable ? '✅ 适飞' : '❌ 不适飞' }}
            </div>
          </el-card>
        </el-col>
      </el-row>
    </div>

    <div v-else-if="!loading" class="empty-tip">
      <el-icon size="48"><Cloudy /></el-icon>
      <p>请点击「查询预报」获取天气预报数据</p>
    </div>
  </PageLayout>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Cloudy } from '@element-plus/icons-vue'
import axios from 'axios'
import PageLayout from '@/components/PageLayout.vue'

const loading = ref(false)
const city = ref('广州')
const forecast = ref([])

async function fetchForecast() {
  loading.value = true
  try {
    const { data } = await axios.get('/api/weather/forecast', { params: { city: city.value } })
    const casts = data.forecasts || data.forecast || []
    forecast.value = casts.map(f => {
      const wind = parseInt(f.dayWindPower) || 0
      const badWeather = ['暴雨', '大雨', '雷阵雨', '暴雪', '大雾']
      const flyable = wind < 6 && !badWeather.some(b => f.dayWeather?.includes(b))
      return { ...f, flyable }
    })
    if (!forecast.value.length) ElMessage.warning('暂无预报数据')
  } catch {
    ElMessage.error('获取预报数据失败，请检查气象服务配置')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.forecast-card { text-align: center; padding: 8px; }
.forecast-card.no-fly { background: #fef2f2; }
.f-date { font-size: 14px; font-weight: 600; color: var(--text-primary); }
.f-week { font-size: 12px; color: var(--text-secondary); }
.f-weather { font-size: 18px; margin: 8px 0; }
.f-temp { font-size: 14px; font-weight: 500; margin: 4px 0; }
.f-wind { font-size: 12px; color: var(--text-secondary); margin-bottom: 10px; }
.f-badge { font-size: 12px; font-weight: 600; }
.f-badge.ok { color: #16a34a; }
.f-badge.no { color: #dc2626; }
.empty-tip { text-align: center; color: #9ca3af; padding: 80px 0; }
</style>
