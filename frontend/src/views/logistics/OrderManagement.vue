<!--
  5.2/5.3 配送订单管理（含异常订单）
-->
<template>
  <PageLayout title="配送订单管理" subtitle="查询、管理配送订单及异常订单处理">
    <template #actions>
      <el-button type="primary" @click="openCreate">
        <el-icon><Plus /></el-icon> 新建订单
      </el-button>
    </template>

    <!-- 筛选栏 -->
    <el-card style="margin-bottom:16px">
      <el-form inline>
        <el-form-item label="订单号">
          <el-input v-model="filters.order_no" placeholder="搜索订单号" clearable style="width:160px" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="filters.status" placeholder="全部状态" clearable style="width:130px">
            <el-option v-for="s in ORDER_STATUSES" :key="s.value" :label="s.label" :value="s.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="企业">
          <el-select v-model="filters.enterprise_id" placeholder="全部企业" clearable style="width:180px">
            <el-option v-for="e in enterprises" :key="e.id" :label="e.name" :value="e.id" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="fetchData">查询</el-button>
          <el-button @click="resetFilters">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 订单统计 -->
    <el-row :gutter="12" style="margin-bottom:16px">
      <el-col :span="4" v-for="s in orderStats" :key="s.label">
        <div class="stat-mini" :style="{ borderLeftColor: s.color }">
          <div class="stat-mini-val">{{ s.count }}</div>
          <div class="stat-mini-lbl">{{ s.label }}</div>
        </div>
      </el-col>
    </el-row>

    <!-- 表格 -->
    <el-table :data="tableData" v-loading="loading" stripe border style="width:100%">
      <el-table-column prop="order_no" label="订单号" width="140" />
      <el-table-column prop="cargo_type" label="货物类型" width="100" />
      <el-table-column prop="cargo_weight" label="重量(kg)" width="90" />
      <el-table-column label="寄件" min-width="140" show-overflow-tooltip>
        <template #default="{ row }">{{ row.sender_name }} - {{ row.sender_address }}</template>
      </el-table-column>
      <el-table-column label="收件" min-width="140" show-overflow-tooltip>
        <template #default="{ row }">{{ row.receiver_name }} - {{ row.receiver_address }}</template>
      </el-table-column>
      <el-table-column label="计划时间" width="160">
        <template #default="{ row }">{{ fmtDt(row.planned_time) }}</template>
      </el-table-column>
      <el-table-column label="状态" width="110">
        <template #default="{ row }">
          <el-tag :type="statusType(row.status)">{{ statusLabel(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="abnormal_reason" label="异常原因" width="120" show-overflow-tooltip />
      <el-table-column label="操作" width="120" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button link type="warning" @click="markAbnormal(row)" v-if="row.status === 'pending'">标记异常</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="pagination-row">
      <el-pagination v-model:current-page="page" v-model:page-size="pageSize"
        :total="total" layout="total, prev, pager, next" background small @change="fetchData" />
    </div>

    <!-- 创建/编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑订单' : '新建订单'" width="600px">
      <el-form :model="form" ref="formRef" label-width="90px">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="货物类型" prop="cargo_type">
              <el-select v-model="form.cargo_type" style="width:100%">
                <el-option v-for="t in CARGO_TYPES" :key="t" :label="t" :value="t" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="重量(kg)">
              <el-input-number v-model="form.cargo_weight" :min="0.1" :max="50" :precision="1" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="寄件人"><el-input v-model="form.sender_name" /></el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="收件人"><el-input v-model="form.receiver_name" /></el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="寄件地址"><el-input v-model="form.sender_address" /></el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="收件地址"><el-input v-model="form.receiver_address" /></el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="企业">
              <el-select v-model="form.enterprise_id" style="width:100%">
                <el-option v-for="e in enterprises" :key="e.id" :label="e.name" :value="e.id" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="计划时间">
              <el-date-picker v-model="form.planned_time" type="datetime" value-format="YYYY-MM-DDTHH:mm:ss" style="width:100%" />
            </el-form-item>
          </el-col>
        </el-row>
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
import { Plus } from '@element-plus/icons-vue'
import axios from 'axios'
import PageLayout from '@/components/PageLayout.vue'

const ORDER_STATUSES = [
  { value: 'pending', label: '待处理' }, { value: 'dispatched', label: '已派单' },
  { value: 'delivering', label: '配送中' }, { value: 'completed', label: '已完成' },
  { value: 'cancelled', label: '已取消' }, { value: 'abnormal', label: '异常' },
]
const CARGO_TYPES = ['医疗器械', '食品生鲜', '文件快递', '电子产品', '药品', '日用品']

const loading = ref(false)
const saving = ref(false)
const tableData = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const enterprises = ref([])
const orderStats = ref([])
const dialogVisible = ref(false)
const isEdit = ref(false)
const formRef = ref()

const filters = reactive({ order_no: '', status: '', enterprise_id: null })
const form = reactive({
  id: null, order_no: '', enterprise_id: null, cargo_type: '文件快递',
  cargo_weight: 1.0, sender_name: '', sender_address: '', receiver_name: '',
  receiver_address: '', planned_time: null,
})

const STATUS_COLOR = { pending: '', dispatched: 'warning', delivering: 'primary', completed: 'success', cancelled: 'info', abnormal: 'danger' }
const statusType = (s) => STATUS_COLOR[s] || ''
const statusLabel = (s) => ORDER_STATUSES.find(x => x.value === s)?.label || s
const fmtDt = (s) => s ? new Date(s).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }) : '-'

async function fetchData() {
  loading.value = true
  try {
    const { data } = await axios.get('/api/logistics/orders', {
      params: { page: page.value, page_size: pageSize.value, ...filters }
    })
    tableData.value = data.items || []
    total.value = data.total || 0
  } catch { ElMessage.error('获取订单失败') }
  finally { loading.value = false }
}

async function fetchStats() {
  try {
    const { data } = await axios.get('/api/logistics/orders/stats')
    const colorMap = { pending: '#f59e0b', dispatched: '#3b82f6', delivering: '#8b5cf6', completed: '#16a34a', cancelled: '#6b7280', abnormal: '#dc2626' }
    const labelMap = { pending: '待处理', dispatched: '已派单', delivering: '配送中', completed: '已完成', cancelled: '已取消', abnormal: '异常' }
    orderStats.value = Object.entries(data).map(([k, v]) => ({ label: labelMap[k] || k, count: v, color: colorMap[k] || '#9ca3af' }))
  } catch {}
}

async function fetchEnterprises() {
  const { data } = await axios.get('/api/logistics/enterprises', { params: { page_size: 100 } })
  enterprises.value = data.items || []
}

function openCreate() {
  isEdit.value = false
  Object.assign(form, { id: null, cargo_type: '文件快递', cargo_weight: 1, sender_name: '', sender_address: '', receiver_name: '', receiver_address: '', planned_time: null, enterprise_id: enterprises.value[0]?.id })
  dialogVisible.value = true
}

function openEdit(row) {
  isEdit.value = true
  Object.assign(form, row)
  dialogVisible.value = true
}

async function handleSave() {
  saving.value = true
  try {
    if (isEdit.value) {
      await axios.put(`/api/logistics/orders/${form.id}`, form)
    } else {
      await axios.post('/api/logistics/orders', form)
    }
    ElMessage.success(isEdit.value ? '更新成功' : '创建成功')
    dialogVisible.value = false
    fetchData()
    fetchStats()
  } catch { ElMessage.error('操作失败') }
  finally { saving.value = false }
}

async function markAbnormal(row) {
  const reason = await ElMessageBox.prompt('请输入异常原因', '标记异常', { confirmButtonText: '确定', cancelButtonText: '取消' })
  await axios.put(`/api/logistics/orders/${row.id}`, { status: 'abnormal', abnormal_reason: reason.value })
  ElMessage.success('已标记为异常')
  fetchData()
}

function resetFilters() { Object.assign(filters, { order_no: '', status: '', enterprise_id: null }); fetchData() }

onMounted(() => { fetchEnterprises(); fetchData(); fetchStats() })
</script>

<style scoped>
.pagination-row { display: flex; justify-content: flex-end; margin-top: 16px; }
.stat-mini { background: #fff; border-left: 3px solid; padding: 12px 16px; border-radius: 6px; }
.stat-mini-val { font-size: 24px; font-weight: 700; color: var(--text-primary); }
.stat-mini-lbl { font-size: 12px; color: var(--text-secondary); margin-top: 2px; }
</style>
