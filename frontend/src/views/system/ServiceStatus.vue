<!--
  9.6 服务状态监测
-->
<template>
  <PageLayout title="服务状态监测" subtitle="实时监测平台及依赖服务运行状态，及时发现异常">
    <template #actions>
      <el-button @click="fetchStatus" :loading="loading">
        <el-icon><Refresh /></el-icon> 刷新检查
      </el-button>
    </template>

    <div v-loading="loading">
      <el-alert v-if="status"
        :title="`系统整体状态：${overallLabel}`"
        :type="overallType" :closable="false" style="margin-bottom:20px"
      />

      <el-row :gutter="16">
        <el-col :span="8" v-for="svc in services" :key="svc.name">
          <div class="svc-card" :class="svc.status">
            <div class="svc-head">
              <span class="svc-dot"></span>
              <span class="svc-name">{{ svc.name }}</span>
            </div>
            <div class="svc-meta">
              <span>响应 {{ svc.latency_ms }}ms</span>
              <span>{{ fmtTime(svc.last_check) }}</span>
            </div>
          </div>
        </el-col>
      </el-row>

      <div class="check-time" v-if="status">最后检查：{{ fmtTime(status.checked_at) }}</div>
    </div>
  </PageLayout>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import axios from 'axios'
import PageLayout from '@/components/PageLayout.vue'

const loading = ref(false), status = ref(null)
const services = computed(() => status.value?.services || [])
const overallLabel = computed(() => ({ healthy: '正常', degraded: '部分降级', error: '异常' }[status.value?.overall] || '未知')
)
const overallType = computed(() => ({ healthy: 'success', degraded: 'warning', error: 'error' }[status.value?.overall] || 'info'))
const fmtTime = (s) => s ? new Date(s).toLocaleTimeString('zh-CN') : '-'

async function fetchStatus() {
  loading.value = true
  try { const { data } = await axios.get('/api/system/service-status'); status.value = data }
  catch { ElMessage.error('获取服务状态失败') } finally { loading.value = false }
}
onMounted(fetchStatus)
</script>

<style scoped>
.svc-card { background: #fff; border-radius: 8px; padding: 16px 20px; border-left: 4px solid #e5e7eb; margin-bottom: 12px; }
.svc-card.healthy { border-left-color: #16a34a; }
.svc-card.degraded { border-left-color: #f59e0b; }
.svc-card.error { border-left-color: #dc2626; background: #fef2f2; }
.svc-head { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.svc-dot { width: 10px; height: 10px; border-radius: 50%; background: currentColor; flex-shrink: 0; }
.svc-card.healthy .svc-dot { color: #16a34a; }
.svc-card.degraded .svc-dot { color: #f59e0b; }
.svc-card.error .svc-dot { color: #dc2626; }
.svc-name { font-weight: 500; font-size: 14px; }
.svc-meta { display: flex; justify-content: space-between; font-size: 12px; color: #9ca3af; }
.check-time { margin-top: 16px; font-size: 12px; color: #9ca3af; text-align: right; }
</style>
