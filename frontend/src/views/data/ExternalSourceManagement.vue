<!--
  8.3 外部数据源管理
  管理平台对接的外部数据服务（气象、航空情报、企业API等）
-->
<template>
  <PageLayout title="外部数据源管理" subtitle="配置和监控平台对接的外部数据服务连接">
    <template #actions>
      <el-button @click="testAllConnections" :loading="testingAll">
        <el-icon><Connection /></el-icon> 全部测试
      </el-button>
      <el-button type="primary" @click="openCreate" style="margin-left:8px">
        <el-icon><Plus /></el-icon> 新增数据源
      </el-button>
    </template>

    <el-row :gutter="16" style="margin-bottom:20px">
      <el-col :span="6" v-for="item in sources" :key="item.id">
        <el-card shadow="hover" :class="['source-card', `status-${item.status}`]">
          <div class="source-header">
            <span class="source-name">{{ item.name }}</span>
            <el-tag size="small" :type="STATUS_TYPES[item.status]">{{ STATUS_LABELS[item.status] }}</el-tag>
          </div>
          <div class="source-type">{{ TYPE_LABELS[item.type] || item.type }}</div>
          <div class="source-url">{{ item.base_url }}</div>
          <div class="source-meta">
            <span>更新间隔：{{ item.refresh_interval }}s</span>
            <span>上次同步：{{ fmtTime(item.last_sync_at) }}</span>
          </div>
          <div class="source-actions">
            <el-button size="small" @click="testConnection(item)" :loading="item.testing">连接测试</el-button>
            <el-button size="small" type="primary" @click="openEdit(item)">配置</el-button>
            <el-button size="small" type="danger" plain @click="handleDelete(item)">删除</el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑数据源' : '新增数据源'" width="540px">
      <el-form :model="form" ref="formRef" :rules="rules" label-width="100px">
        <el-form-item label="数据源名称" prop="name"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="数据类型">
          <el-select v-model="form.type" style="width:100%">
            <el-option v-for="(l, k) in TYPE_LABELS" :key="k" :label="l" :value="k" />
          </el-select>
        </el-form-item>
        <el-form-item label="Base URL" prop="base_url"><el-input v-model="form.base_url" placeholder="https://api.example.com/v1" /></el-form-item>
        <el-form-item label="API Key"><el-input v-model="form.api_key" show-password /></el-form-item>
        <el-form-item label="刷新间隔(s)"><el-input-number v-model="form.refresh_interval" :min="10" style="width:100%" /></el-form-item>
        <el-form-item label="启用状态"><el-switch v-model="form.enabled" /></el-form-item>
        <el-form-item label="备注"><el-input v-model="form.remark" type="textarea" :rows="2" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </PageLayout>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Connection } from '@element-plus/icons-vue'
import PageLayout from '@/components/PageLayout.vue'

const STATUS_LABELS = { connected: '已连接', disconnected: '断开', error: '异常', idle: '未测试' }
const STATUS_TYPES = { connected: 'success', disconnected: 'info', error: 'danger', idle: '' }
const TYPE_LABELS = { weather: '气象服务', aviation: '航空情报', enterprise: '企业API', map: '地图瓦片', other: '其他' }

const fmtTime = (s) => s ? new Date(s).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }) : '从未'

const sources = ref([])
const dialogVisible = ref(false), isEdit = ref(false), formRef = ref(), saving = ref(false), testingAll = ref(false)
const form = reactive({ id: null, name: '', type: 'weather', base_url: '', api_key: '', refresh_interval: 60, enabled: true, remark: '' })
const rules = { name: [{ required: true, message: '请填写名称' }], base_url: [{ required: true, message: '请填写URL' }] }

const SEED_SOURCES = [
  { id: 1, name: '国家气象局数据接口', type: 'weather', base_url: 'https://api.nmc.cn/rest', api_key: 'nmc_api_key_***', refresh_interval: 300, enabled: true, status: 'connected', last_sync_at: new Date(Date.now() - 300000).toISOString(), remark: '全国气象站实况数据' },
  { id: 2, name: '广州气象台精细化格点', type: 'weather', base_url: 'https://api.gzqxj.cn/grid', api_key: 'gzqxj_key_***', refresh_interval: 600, enabled: true, status: 'connected', last_sync_at: new Date(Date.now() - 600000).toISOString(), remark: '1km格点气象预报' },
  { id: 3, name: '中国航空情报服务中心', type: 'aviation', base_url: 'https://aisa.caac.gov.cn/api', api_key: 'caac_aisa_key_***', refresh_interval: 3600, enabled: true, status: 'idle', last_sync_at: null, remark: 'NOTAM/临时禁飞区' },
  { id: 4, name: '高德地图Web API', type: 'map', base_url: 'https://restapi.amap.com/v3', api_key: 'amap_web_key_***', refresh_interval: 0, enabled: true, status: 'connected', last_sync_at: new Date().toISOString(), remark: '逆地理编码/POI' },
]

function loadSources() {
  sources.value = (JSON.parse(localStorage.getItem('ext_sources') || 'null') || SEED_SOURCES).map(s => ({ ...s, testing: false }))
}

async function testConnection(item) {
  item.testing = true
  await new Promise(r => setTimeout(r, 800 + Math.random() * 400))
  // 模拟连接测试结果：80% 成功
  item.status = Math.random() > 0.2 ? 'connected' : 'error'
  item.last_sync_at = item.status === 'connected' ? new Date().toISOString() : item.last_sync_at
  item.testing = false
  ElMessage({ type: item.status === 'connected' ? 'success' : 'error', message: `「${item.name}」${item.status === 'connected' ? '连接成功' : '连接失败'}` })
  saveSources()
}

async function testAllConnections() {
  testingAll.value = true
  for (const s of sources.value) await testConnection(s)
  testingAll.value = false
}

function saveSources() {
  localStorage.setItem('ext_sources', JSON.stringify(sources.value.map(({ testing, ...rest }) => rest)))
}

function openCreate() {
  isEdit.value = false
  Object.assign(form, { id: null, name: '', type: 'weather', base_url: '', api_key: '', refresh_interval: 60, enabled: true, remark: '' })
  dialogVisible.value = true
}
function openEdit(item) { isEdit.value = true; Object.assign(form, item); dialogVisible.value = true }

async function handleSave() {
  await formRef.value.validate(); saving.value = true
  const stored = JSON.parse(localStorage.getItem('ext_sources') || 'null') || [...SEED_SOURCES]
  if (isEdit.value) {
    const idx = stored.findIndex(s => s.id === form.id)
    if (idx >= 0) stored[idx] = { ...stored[idx], ...form }
  } else {
    stored.push({ ...form, id: Date.now(), status: 'idle', last_sync_at: null })
  }
  localStorage.setItem('ext_sources', JSON.stringify(stored))
  ElMessage.success('保存成功'); dialogVisible.value = false; saving.value = false; loadSources()
}

async function handleDelete(item) {
  await ElMessageBox.confirm(`确定删除数据源「${item.name}」？`, '确认', { type: 'warning' })
  const stored = JSON.parse(localStorage.getItem('ext_sources') || 'null') || [...SEED_SOURCES]
  localStorage.setItem('ext_sources', JSON.stringify(stored.filter(s => s.id !== item.id)))
  ElMessage.success('删除成功'); loadSources()
}

onMounted(loadSources)
</script>
<style scoped>
.source-card { margin-bottom: 0; }
.source-card.status-connected { border-left: 3px solid #16a34a; }
.source-card.status-error { border-left: 3px solid #dc2626; }
.source-card.status-disconnected { border-left: 3px solid #6b7280; }
.source-card.status-idle { border-left: 3px solid #d1d5db; }
.source-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.source-name { font-weight: 600; font-size: 14px; }
.source-type { font-size: 12px; color: #6b7280; margin-bottom: 4px; }
.source-url { font-size: 11px; color: #9ca3af; font-family: monospace; margin-bottom: 8px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.source-meta { font-size: 11px; color: #9ca3af; display: flex; gap: 12px; margin-bottom: 10px; }
.source-actions { display: flex; gap: 6px; }
</style>
