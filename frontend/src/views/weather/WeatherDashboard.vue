<!--
  4.2 实时气象监测（扩展页面）
  在已有 WeatherPanel 的基础上提供完整的气象监测界面
-->
<template>
  <PageLayout title="实时气象监测" subtitle="当前气象状态、适飞判断及影响飞行的气象指标">
    <template #actions>
      <el-button @click="fetchWeather" :loading="loading">
        <el-icon><Refresh /></el-icon> 刷新
      </el-button>
    </template>

    <el-row :gutter="16" v-if="weather">
      <!-- 核心气象卡片 -->
      <el-col :span="6" v-for="c in weatherCards" :key="c.label">
        <div class="weather-card" :class="c.status">
          <div class="weather-icon">{{ c.icon }}</div>
          <div class="weather-body">
            <div class="weather-val">{{ c.value }}</div>
            <div class="weather-lbl">{{ c.label }}</div>
          </div>
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="16" style="margin-top:16px" v-if="weather">
      <!-- 适飞综合判断 -->
      <el-col :span="10">
        <el-card header="适飞性综合判断">
          <div class="flyable-result" :class="flyable.level">
            <div class="flyable-icon">{{ flyable.icon }}</div>
            <div class="flyable-text">{{ flyable.text }}</div>
          </div>
          <el-divider />
          <div v-for="r in flyable.reasons" :key="r" class="flyable-reason">
            <el-icon><WarningFilled /></el-icon>
            <span>{{ r }}</span>
          </div>
          <div v-if="!flyable.reasons.length" class="flyable-ok">当前气象条件满足所有飞行阈值要求</div>
        </el-card>
      </el-col>

      <!-- 气象详情 -->
      <el-col :span="14">
        <el-card header="气象详细数据">
          <el-descriptions :column="2" border v-if="weather">
            <el-descriptions-item label="天气现象">{{ weather.weather }}</el-descriptions-item>
            <el-descriptions-item label="温度">{{ weather.temperature }}℃</el-descriptions-item>
            <el-descriptions-item label="湿度">{{ weather.humidity }}%</el-descriptions-item>
            <el-descriptions-item label="风向">{{ weather.windDirection }}</el-descriptions-item>
            <el-descriptions-item label="风力等级">{{ weather.windPower }} 级</el-descriptions-item>
            <el-descriptions-item label="城市">{{ weather.city }}</el-descriptions-item>
            <el-descriptions-item label="数据时间" :span="2">{{ weather.reportTime }}</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>
    </el-row>

    <div v-if="!weather && !loading" class="empty-tip">
      <el-icon size="48"><Cloudy /></el-icon>
      <p>气象数据加载中…</p>
    </div>
  </PageLayout>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh, WarningFilled, Cloudy } from '@element-plus/icons-vue'
import axios from 'axios'
import PageLayout from '@/components/PageLayout.vue'

const loading = ref(false)
const weather = ref(null)

const weatherCards = computed(() => {
  if (!weather.value) return []
  const w = weather.value
  const wind = parseInt(w.windPower) || 0
  return [
    { label: '天气', value: w.weather, icon: '🌤', status: '' },
    { label: '温度', value: `${w.temperature}℃`, icon: '🌡', status: w.temperature > 40 ? 'warn' : '' },
    { label: '湿度', value: `${w.humidity}%`, icon: '💧', status: '' },
    { label: '风力', value: `${w.windDirection} ${wind}级`, icon: '💨', status: wind >= 6 ? 'danger' : wind >= 4 ? 'warn' : 'ok' },
  ]
})

const flyable = computed(() => {
  if (!weather.value) return { level: '', icon: '-', text: '暂无数据', reasons: [] }
  const w = weather.value
  const wind = parseInt(w.windPower) || 0
  const reasons = []
  if (wind >= 6) reasons.push(`风力 ${wind} 级，超过飞行安全阈值（5级）`)
  const badWeather = ['暴雨', '大雨', '雷阵雨', '雾', '大雾', '暴雪']
  if (badWeather.some(b => w.weather?.includes(b))) reasons.push(`当前天气「${w.weather}」不适合飞行`)
  if (w.temperature > 40) reasons.push(`气温 ${w.temperature}℃，超过最高飞行温度（40℃）`)
  if (reasons.length === 0) return { level: 'ok', icon: '✅', text: '适宜飞行', reasons: [] }
  if (reasons.length >= 2) return { level: 'danger', icon: '❌', text: '不宜飞行', reasons }
  return { level: 'warn', icon: '⚠️', text: '谨慎飞行', reasons }
})

async function fetchWeather() {
  loading.value = true
  try {
    const { data } = await axios.get('/api/weather/live')
    weather.value = data
  } catch { ElMessage.error('获取气象数据失败') }
  finally { loading.value = false }
}

onMounted(fetchWeather)
</script>

<style scoped>
.weather-card { display: flex; align-items: center; gap: 14px; background: #fff; padding: 18px 20px; border-radius: 10px; box-shadow: 0 1px 4px rgba(0,0,0,.06); }
.weather-card.warn { background: #fffbeb; }
.weather-card.danger { background: #fef2f2; }
.weather-card.ok { background: #f0fdf4; }
.weather-icon { font-size: 32px; }
.weather-val { font-size: 22px; font-weight: 700; color: var(--text-primary); }
.weather-lbl { font-size: 12px; color: var(--text-secondary); margin-top: 2px; }
.flyable-result { display: flex; align-items: center; gap: 16px; padding: 16px 0; }
.flyable-result.ok .flyable-text { color: #16a34a; }
.flyable-result.warn .flyable-text { color: #d97706; }
.flyable-result.danger .flyable-text { color: #dc2626; }
.flyable-icon { font-size: 36px; }
.flyable-text { font-size: 22px; font-weight: 700; }
.flyable-reason { display: flex; align-items: flex-start; gap: 6px; font-size: 13px; color: #d97706; margin-bottom: 6px; }
.flyable-ok { color: #16a34a; font-size: 13px; }
.empty-tip { text-align: center; color: #9ca3af; padding: 60px 0; }
</style>
