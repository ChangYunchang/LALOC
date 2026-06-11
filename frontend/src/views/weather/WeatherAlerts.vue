<!--
  4.5 气象风险预警
-->
<template>
  <PageLayout title="气象风险预警" subtitle="识别可能影响无人机运行的气象风险，发布预警提示">
    <el-row :gutter="16">
      <el-col :span="14">
        <el-card header="当前气象预警评估" v-loading="loading">
          <div v-if="assessment">
            <el-alert
              :title="assessment.overall"
              :type="assessment.level === 'safe' ? 'success' : assessment.level === 'caution' ? 'warning' : 'error'"
              :closable="false" style="margin-bottom:16px"
            />
            <div v-for="alert in assessment.alerts" :key="alert.type" class="alert-item" :class="alert.severity">
              <div class="alert-head">
                <el-tag :type="alert.severity === 'high' ? 'danger' : 'warning'" size="small">{{ alert.name }}</el-tag>
                <span class="alert-time">{{ alert.time }}</span>
              </div>
              <div class="alert-desc">{{ alert.description }}</div>
              <div class="alert-action">建议：{{ alert.suggestion }}</div>
            </div>
            <div v-if="!assessment.alerts.length" class="safe-msg">
              当前无气象预警，飞行环境良好。
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="10">
        <el-card header="气象阈值参数">
          <el-table :data="thresholds" size="small" border>
            <el-table-column prop="name" label="指标" />
            <el-table-column prop="threshold" label="阈值" width="100" />
            <el-table-column label="当前值" width="100">
              <template #default="{ row }">
                <span :class="row.exceeded ? 'exceed' : 'normal'">{{ row.current }}</span>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </PageLayout>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'
import PageLayout from '@/components/PageLayout.vue'

const loading = ref(false)
const assessment = ref(null)
const thresholds = ref([])

async function fetchData() {
  loading.value = true
  try {
    const [liveRes, flyRes] = await Promise.all([
      axios.get('/api/weather/live'),
      axios.get('/api/weather/flyable'),
    ])
    const w = liveRes.data
    const fly = flyRes.data
    const wind = parseInt(w?.windPower) || 0

    const alerts = []
    if (wind >= 6) {
      alerts.push({
        type: 'wind', name: '大风预警', severity: 'high',
        time: new Date().toLocaleTimeString('zh-CN'),
        description: `当前风力 ${wind} 级，已超过安全飞行阈值（5级）`,
        suggestion: '暂停所有飞行任务，等待风速降低后再恢复',
      })
    } else if (wind >= 4) {
      alerts.push({
        type: 'wind', name: '风力提示', severity: 'medium',
        time: new Date().toLocaleTimeString('zh-CN'),
        description: `当前风力 ${wind} 级，请注意飞行安全`,
        suggestion: '缩短飞行距离，优先执行近距离任务',
      })
    }
    const bad = ['暴雨', '大雨', '雷阵雨', '大雾', '暴雪']
    if (bad.some(b => w?.weather?.includes(b))) {
      alerts.push({
        type: 'weather', name: '恶劣天气预警', severity: 'high',
        time: new Date().toLocaleTimeString('zh-CN'),
        description: `当前天气「${w.weather}」不适合无人机飞行`,
        suggestion: '立即暂停飞行任务，等待天气好转',
      })
    }

    assessment.value = {
      overall: fly.status === 'flyable' ? '气象条件良好，适宜飞行' : fly.status === 'caution' ? '气象条件需关注，谨慎飞行' : '当前气象条件不适宜飞行',
      level: fly.status === 'flyable' ? 'safe' : fly.status === 'caution' ? 'caution' : 'danger',
      alerts,
    }

    thresholds.value = [
      { name: '最大风速(级)', threshold: '≤5级', current: `${wind}级`, exceeded: wind > 5 },
      { name: '温度(℃)', threshold: '-10～45℃', current: `${w?.temperature}℃`, exceeded: false },
      { name: '湿度(%)', threshold: '≤95%', current: `${w?.humidity}%`, exceeded: w?.humidity > 95 },
    ]
  } catch { ElMessage.error('获取气象预警数据失败') }
  finally { loading.value = false }
}

onMounted(fetchData)
</script>

<style scoped>
.alert-item { border: 1px solid #e5e7eb; border-radius: 8px; padding: 12px; margin-bottom: 10px; }
.alert-item.high { border-color: #fca5a5; background: #fef2f2; }
.alert-item.medium { border-color: #fde68a; background: #fffbeb; }
.alert-head { display: flex; align-items: center; gap: 10px; margin-bottom: 6px; }
.alert-time { font-size: 12px; color: #9ca3af; margin-left: auto; }
.alert-desc { font-size: 13px; color: #374151; margin-bottom: 4px; }
.alert-action { font-size: 12px; color: #6b7280; }
.safe-msg { color: #16a34a; font-size: 14px; text-align: center; padding: 20px 0; }
.exceed { color: #dc2626; font-weight: 600; }
.normal { color: #16a34a; }
</style>
