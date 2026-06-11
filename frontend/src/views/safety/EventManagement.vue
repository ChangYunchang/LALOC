<!--
  6.4 异常事件管理
-->
<template>
  <PageLayout title="异常事件管理" subtitle="采集、分类、处置飞行越界、冲突、故障等异常事件">
    <template #actions>
      <el-button type="primary" @click="openCreate">
        <el-icon><Plus /></el-icon> 录入事件
      </el-button>
    </template>

    <!-- 统计卡 -->
    <el-row :gutter="12" style="margin-bottom:16px">
      <el-col :span="6" v-for="s in summaryCards" :key="s.label">
        <div class="stat-card" :style="{ borderTopColor: s.color }">
          <div class="stat-val">{{ s.count }}</div>
          <div class="stat-lbl">{{ s.label }}</div>
        </div>
      </el-col>
    </el-row>

    <!-- 筛选 -->
    <el-card style="margin-bottom:16px">
      <el-form inline>
        <el-form-item label="事件类型">
          <el-select v-model="filters.event_type" clearable style="width:150px">
            <el-option v-for="t in EVENT_TYPES" :key="t.value" :label="t.label" :value="t.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="严重程度">
          <el-select v-model="filters.severity" clearable style="width:110px">
            <el-option label="低" value="low" /><el-option label="中" value="medium" />
            <el-option label="高" value="high" /><el-option label="严重" value="critical" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="filters.status" clearable style="width:110px">
            <el-option label="待处理" value="open" /><el-option label="处置中" value="processing" /><el-option label="已关闭" value="closed" />
          </el-select>
        </el-form-item>
        <el-form-item><el-button type="primary" @click="fetchData">查询</el-button></el-form-item>
      </el-form>
    </el-card>

    <el-table :data="tableData" v-loading="loading" stripe border>
      <el-table-column prop="event_no" label="事件编号" width="140" />
      <el-table-column label="类型" width="120">
        <template #default="{ row }">
          <el-tag :type="typeColor(row.event_type)" size="small">{{ typeLabel(row.event_type) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="严重程度" width="100">
        <template #default="{ row }">
          <el-tag :type="sevType(row.severity)" size="small">{{ sevLabel(row.severity) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
      <el-table-column label="发生时间" width="150">
        <template #default="{ row }">{{ fmtDt(row.occurred_at) }}</template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="statusType(row.status)">{{ statusLabel(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="handler" label="处置人" width="100" />
      <el-table-column label="操作" width="140" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openHandle(row)" v-if="row.status !== 'closed'">处置</el-button>
          <el-button link type="info" @click="openView(row)">查看</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="pagination-row">
      <el-pagination v-model:current-page="page" v-model:page-size="pageSize"
        :total="total" layout="total, prev, pager, next" background small @change="fetchData" />
    </div>

    <!-- 录入对话框 -->
    <el-dialog v-model="createVisible" title="录入异常事件" width="520px">
      <el-form :model="createForm" ref="createRef" :rules="createRules" label-width="100px">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="事件类型" prop="event_type">
              <el-select v-model="createForm.event_type" style="width:100%">
                <el-option v-for="t in EVENT_TYPES" :key="t.value" :label="t.label" :value="t.value" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="严重程度">
              <el-select v-model="createForm.severity" style="width:100%">
                <el-option label="低" value="low" /><el-option label="中" value="medium" /><el-option label="高" value="high" /><el-option label="严重" value="critical" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12"><el-form-item label="经度"><el-input-number v-model="createForm.lng" :precision="6" style="width:100%" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="纬度"><el-input-number v-model="createForm.lat" :precision="6" style="width:100%" /></el-form-item></el-col>
          <el-col :span="24">
            <el-form-item label="事件描述" prop="description"><el-input v-model="createForm.description" type="textarea" :rows="3" /></el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="doCreate">提交</el-button>
      </template>
    </el-dialog>

    <!-- 处置对话框 -->
    <el-dialog v-model="handleVisible" title="事件处置" width="460px">
      <el-form :model="handleForm" label-width="100px">
        <el-form-item label="处置人"><el-input v-model="handleForm.handler" /></el-form-item>
        <el-form-item label="处置说明"><el-input v-model="handleForm.handle_notes" type="textarea" :rows="3" /></el-form-item>
        <el-form-item label="处理状态">
          <el-select v-model="handleForm.status" style="width:100%">
            <el-option label="处置中" value="processing" /><el-option label="已关闭" value="closed" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="handleVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="doHandle">提交处置</el-button>
      </template>
    </el-dialog>

    <!-- 查看详情 -->
    <el-dialog v-model="viewVisible" title="事件详情" width="500px">
      <el-descriptions :column="2" border v-if="viewEvent">
        <el-descriptions-item label="事件编号">{{ viewEvent.event_no }}</el-descriptions-item>
        <el-descriptions-item label="事件类型">{{ typeLabel(viewEvent.event_type) }}</el-descriptions-item>
        <el-descriptions-item label="严重程度">{{ sevLabel(viewEvent.severity) }}</el-descriptions-item>
        <el-descriptions-item label="状态">{{ statusLabel(viewEvent.status) }}</el-descriptions-item>
        <el-descriptions-item label="发生时间" :span="2">{{ fmtDt(viewEvent.occurred_at) }}</el-descriptions-item>
        <el-descriptions-item label="位置" :span="2">{{ viewEvent.lng?.toFixed(4) }}, {{ viewEvent.lat?.toFixed(4) }}</el-descriptions-item>
        <el-descriptions-item label="描述" :span="2">{{ viewEvent.description }}</el-descriptions-item>
        <el-descriptions-item label="处置人">{{ viewEvent.handler || '-' }}</el-descriptions-item>
        <el-descriptions-item label="关闭时间">{{ fmtDt(viewEvent.closed_at) || '-' }}</el-descriptions-item>
        <el-descriptions-item label="处置说明" :span="2">{{ viewEvent.handle_notes || '-' }}</el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </PageLayout>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import axios from 'axios'
import PageLayout from '@/components/PageLayout.vue'

const EVENT_TYPES = [
  { value: 'boundary_violation', label: '越界飞行' },
  { value: 'route_conflict', label: '航线冲突' },
  { value: 'weather_anomaly', label: '气象异常' },
  { value: 'comm_loss', label: '通信中断' },
  { value: 'device_fault', label: '设备故障' },
  { value: 'congestion', label: '低空拥堵' },
]
const typeLabel = (v) => EVENT_TYPES.find(t => t.value === v)?.label || v
const typeColor = (v) => ({ boundary_violation: 'danger', route_conflict: 'warning', weather_anomaly: 'info', comm_loss: 'warning', device_fault: 'danger', congestion: 'primary' }[v] || '')
const sevType = (s) => ({ low: 'info', medium: 'warning', high: 'danger', critical: 'danger' }[s] || '')
const sevLabel = (s) => ({ low: '低', medium: '中', high: '高', critical: '严重' }[s] || s)
const statusType = (s) => ({ open: 'danger', processing: 'warning', closed: 'success' }[s] || '')
const statusLabel = (s) => ({ open: '待处理', processing: '处置中', closed: '已关闭' }[s] || s)
const fmtDt = (s) => s ? new Date(s).toLocaleString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }) : null

const loading = ref(false), saving = ref(false)
const tableData = ref([]), total = ref(0), page = ref(1), pageSize = ref(20)
const summaryCards = ref([])
const createVisible = ref(false), handleVisible = ref(false), viewVisible = ref(false)
const viewEvent = ref(null), currentEvent = ref(null), createRef = ref()
const filters = reactive({ event_type: '', severity: '', status: '' })
const createForm = reactive({ event_type: 'boundary_violation', severity: 'medium', lng: 113.2644, lat: 23.1291, description: '' })
const handleForm = reactive({ handler: '', handle_notes: '', status: 'processing' })
const createRules = { event_type: [{ required: true }], description: [{ required: true, message: '请输入描述' }] }

async function fetchData() {
  loading.value = true
  try {
    const [listRes, statsRes] = await Promise.all([
      axios.get('/api/safety/events', { params: { page: page.value, page_size: pageSize.value, ...filters } }),
      axios.get('/api/safety/events/stats'),
    ])
    tableData.value = listRes.data.items || []; total.value = listRes.data.total || 0
    const s = statsRes.data
    summaryCards.value = [
      { label: '待处理', count: s.by_status?.open || 0, color: '#dc2626' },
      { label: '处置中', count: s.by_status?.processing || 0, color: '#f59e0b' },
      { label: '已关闭', count: s.by_status?.closed || 0, color: '#16a34a' },
      { label: '事件总数', count: s.total || 0, color: '#3b82f6' },
    ]
  } catch { ElMessage.error('获取数据失败') } finally { loading.value = false }
}
function openCreate() { Object.assign(createForm, { event_type: 'boundary_violation', severity: 'medium', lng: 113.2644, lat: 23.1291, description: '' }); createVisible.value = true }
function openHandle(row) { currentEvent.value = row; Object.assign(handleForm, { handler: '', handle_notes: '', status: 'processing' }); handleVisible.value = true }
function openView(row) { viewEvent.value = row; viewVisible.value = true }
async function doCreate() {
  await createRef.value.validate(); saving.value = true
  try {
    await axios.post('/api/safety/events', createForm)
    ElMessage.success('事件已记录'); createVisible.value = false; fetchData()
  } catch { ElMessage.error('操作失败') } finally { saving.value = false }
}
async function doHandle() {
  saving.value = true
  try {
    await axios.put(`/api/safety/events/${currentEvent.value.id}/handle`, handleForm)
    ElMessage.success('处置记录已更新'); handleVisible.value = false; fetchData()
  } catch { ElMessage.error('操作失败') } finally { saving.value = false }
}
onMounted(fetchData)
</script>

<style scoped>
.pagination-row { display: flex; justify-content: flex-end; margin-top: 16px; }
.stat-card { background: #fff; border-top: 3px solid; padding: 16px 20px; border-radius: 8px; text-align: center; }
.stat-val { font-size: 28px; font-weight: 700; color: var(--text-primary); }
.stat-lbl { font-size: 12px; color: var(--text-secondary); margin-top: 4px; }
</style>
