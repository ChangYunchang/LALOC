<template>
  <div class="weather-panel">
    <div class="panel-header">
      <span class="panel-icon">🌤️</span>
      <span class="panel-title">广州实时天气</span>
      <el-button
        type="primary"
        size="small"
        :icon="Refresh"
        circle
        @click="fetchWeather"
        :loading="loading"
      />
    </div>

    <div v-if="weather" class="weather-content">
      <div class="weather-main">
        <span class="weather-temp">{{ weather.temperature }}°</span>
        <span class="weather-desc">{{ weather.weather }}</span>
      </div>

      <div class="weather-details">
        <div class="detail-item">
          <span class="detail-label">湿度</span>
          <span class="detail-value">{{ weather.humidity }}%</span>
        </div>
        <div class="detail-item">
          <span class="detail-label">风向</span>
          <span class="detail-value">{{ weather.windDirection }}</span>
        </div>
        <div class="detail-item">
          <span class="detail-label">风力</span>
          <span class="detail-value">{{ weather.windPower }}级</span>
        </div>
      </div>

      <div class="fly-status" :class="isFlyable ? 'flyable' : 'not-flyable'">
        {{ isFlyable ? '✅ 适宜飞行' : '⛔ 不宜飞行' }}
      </div>

      <div v-if="warnings.length > 0" class="warnings">
        <div v-for="(w, i) in warnings" :key="i" class="warning-item">⚠️ {{ w }}</div>
      </div>

      <div class="weather-time">更新: {{ weather.reportTime }}</div>
    </div>

    <div v-else-if="loading" class="weather-loading">
      <el-icon class="is-loading"><Loading /></el-icon>
      <span>加载中...</span>
    </div>

    <div v-else class="weather-error">暂无天气数据</div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { Refresh, Loading } from '@element-plus/icons-vue'
import AMapLoader from '@amap/amap-jsapi-loader'

const weather = ref(null)
const loading = ref(false)
const isFlyable = ref(true)
const warnings = ref([])
let timer = null
let AMapInstance = null

const amapKey = import.meta.env.VITE_AMAP_KEY
const amapSecurityCode = import.meta.env.VITE_AMAP_SECURITY_CODE

async function initAMap() {
  if (AMapInstance) return AMapInstance
  window._AMapSecurityConfig = { securityJsCode: amapSecurityCode }
  AMapInstance = await AMapLoader.load({
    key: amapKey,
    version: '2.0',
    plugins: ['AMap.Weather'],
  })
  return AMapInstance
}

async function fetchWeather() {
  loading.value = true
  try {
    const AMap = await initAMap()
    const weatherPlugin = new AMap.Weather()

    const liveData = await new Promise((resolve, reject) => {
      weatherPlugin.getLive('广州市', (err, data) => {
        if (err) reject(err)
        else resolve(data)
      })
    })

    weather.value = liveData

    // 判断飞行适宜性
    checkFlyable(liveData)
  } catch (e) {
    console.error('获取天气失败:', e)
  } finally {
    loading.value = false
  }
}

function checkFlyable(data) {
  const ws = []
  let flyable = true

  // 温度检查
  const temp = parseFloat(data.temperature)
  if (temp < -10 || temp > 45) {
    ws.push(`温度${temp}℃，不建议飞行`)
    flyable = false
  }

  // 风力检查
  try {
    const windLevel = parseInt(data.windPower)
    if (windLevel >= 6) {
      ws.push(`风力${data.windPower}级，不建议飞行`)
      flyable = false
    } else if (windLevel >= 4) {
      ws.push(`风力${data.windPower}级，注意安全`)
    }
  } catch {}

  // 天气状况
  const bad = ['暴雨', '大雨', '雷阵雨', '冰雹', '暴雪', '大雪', '台风', '沙尘暴', '雾', '霾']
  for (const bw of bad) {
    if (data.weather?.includes(bw)) {
      ws.push(`天气"${data.weather}"，不建议飞行`)
      flyable = false
      break
    }
  }

  isFlyable.value = flyable
  warnings.value = ws
}

onMounted(() => {
  fetchWeather()
  timer = setInterval(fetchWeather, 10 * 60 * 1000)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<style scoped>
.weather-panel {
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
}

.panel-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 14px;
}

.panel-icon { font-size: 18px; }
.panel-title { font-size: 14px; font-weight: 600; flex: 1; color: #1f2937; }

.weather-content { text-align: center; }

.weather-main { margin-bottom: 14px; }
.weather-temp { font-size: 44px; font-weight: 700; color: #1f2937; display: block; line-height: 1; }
.weather-desc { font-size: 14px; color: #6b7280; margin-top: 4px; }

.weather-details {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  margin-bottom: 14px;
}

.detail-item { text-align: center; }
.detail-label { display: block; font-size: 11px; color: #9ca3af; margin-bottom: 2px; }
.detail-value { font-size: 14px; font-weight: 600; color: #374151; }

.fly-status {
  padding: 6px 12px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  text-align: center;
  margin-bottom: 10px;
}

.fly-status.flyable { background: #f0fdf4; color: #16a34a; border: 1px solid #bbf7d0; }
.fly-status.not-flyable { background: #fef2f2; color: #dc2626; border: 1px solid #fecaca; }

.warnings { margin-bottom: 10px; }
.warning-item { font-size: 12px; color: #ea580c; margin-bottom: 3px; text-align: left; }
.weather-time { font-size: 11px; color: #9ca3af; text-align: right; }

.weather-loading, .weather-error { text-align: center; padding: 20px; color: #9ca3af; }
</style>
