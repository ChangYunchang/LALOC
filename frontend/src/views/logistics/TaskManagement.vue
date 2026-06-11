<!--
  5.4 配送任务管理
-->
<template>
  <PageLayout title="配送任务管理" subtitle="管理配送任务全生命周期，跟踪任务执行状态">
    <template #actions>
      <el-button type="primary" @click="openCreate">
        <el-icon><Plus /></el-icon> 新建任务
      </el-button>
    </template>

    <el-card style="margin-bottom:16px">
      <el-form inline>
        <el-form-item label="状态">
          <el-select v-model="filters.status" clearable style="width:130px" placeholder="全部状态">
            <el-option v-for="s in TASK_STATUSES" :key="s.value" :label="s.label" :value="s.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="企业">
          <el-select v-model="filters.enterprise_id" clearable style="width:180px" placeholder="全部企业">
            <el-option v-for="e in enterprises" :key="e.id" :label="e.name" :value="e.id" />
          </el-select>
        </el-form-item>
        <el-form-item><el-button type="primary" @click="fetchData">查询</el-button></el-form-item>
      </el-form>
    </el-card>

    <el-table :data="tableData" v-loading="loading" stripe border>
      <el-table-column prop="task_no" label="任务编号" width="140" />
      <el-table-column prop="order_id" label="关联订单" width="90">
        <template #default="{ row }"><span>{{ row.order_id ? `#${row.order_id}` : '-' }}</span></template>
      </el-table-column>
      <el-table-column prop="drone_id" label="无人机" width="80">
        <template #default="{ row }"><span>{{ row.drone_id ? `#${row.drone_id}` : '未分配' }}</span></template>
      </el-table-column>
      <el-table-column label="计划时间" width="220">
        <template #default="{ row }">
          {{ fmtDt(row.planned_start) }} → {{ fmtDt(row.planned_end) }}
        </template>
      </el-table-column>
      <el-table-column prop="priority" label="优先级" width="80">
        <template #default="{ row }">
          <el-tag size="small" :type="row.priority >= 7 ? 'danger' : row.priority >= 5 ? 'warning' : ''">P{{ row.priority }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="110">
        <template #default="{ row }">
          <el-tag :type="taskStatusType(row.status)">{{ taskStatusLabel(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="180" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button link type="success" @click="quickAction(row, 'start')" v-if="row.status === 'assigned'">开始</el-button>
          <el-button link type="warning" @click="quickAction(row, 'complete')" v-if="row.status === 'executing'">完成</el-button>
          <el-button link type="danger" @click="quickAction(row, 'cancel')" v-if="['pending','assigned'].includes(row.status)">取消</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="pagination-row">
      <el-pagination v-model:current-page="page" v-model:page-size="pageSize"
        :total="total" layout="total, prev, pager, next" background small @change="fetchData" />
    </div>

    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑任务' : '新建任务'" width="520px">
      <el-form :model="form" ref="formRef" :rules="rules" label-width="100px">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="所属企业" prop="enterprise_id">
              <el-select v-model="form.enterprise_id" style="width:100%">
                <el-option v-for="e in enterprises" :key="e.id" :label="e.name" :value="e.id" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="优先级">
              <el-slider v-model="form.priority" :min="1" :max="10" show-stops />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="计划开始">
              <el-date-picker v-model="form.planned_start" type="datetime" value-format="YYYY-MM-DDTHH:mm:ss" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="计划结束">
              <el-date-picker v-model="form.planned_end" type="datetime" value-format="YYYY-MM-DDTHH:mm:ss" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="备注"><el-input v-model="form.notes" type="textarea" :rows="2" /></el-form-item>
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

const TASK_STATUSES = [
  { value: 'pending', label: '待处理' }, { value: 'assigned', label: '已分配' },
  { value: 'executing', label: '执行中' }, { value: 'completed', label: '已完成' },
  { value: 'failed', label: '失败' }, { value: 'cancelled', label: '已取消' },
]
const STATUS_TYPES = { pending: '', assigned: 'warning', executing: 'primary', completed: 'success', failed: 'danger', cancelled: 'info' }
const taskStatusType = (s) => STATUS_TYPES[s] || ''
const taskStatusLabel = (s) => TASK_STATUSES.find(x => x.value === s)?.label || s
const fmtDt = (s) => s ? new Date(s).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }) : '-'

const loading = ref(false), saving = ref(false)
const tableData = ref([]), total = ref(0), page = ref(1), pageSize = ref(20)
const enterprises = ref([]), dialogVisible = ref(false), isEdit = ref(false), formRef = ref()
const filters = reactive({ status: '', enterprise_id: null })
const form = reactive({ id: null, enterprise_id: null, planned_start: null, planned_end: null, priority: 5, notes: '' })
const rules = { enterprise_id: [{ required: true, message: '请选择企业' }] }

async function fetchData() {
  loading.value = true
  try {
    const { data } = await axios.get('/api/logistics/tasks', { params: { page: page.value, page_size: pageSize.value, ...filters } })
    tableData.value = data.items || []; total.value = data.total || 0
  } catch { ElMessage.error('获取任务失败') } finally { loading.value = false }
}
async function fetchEnterprises() {
  const { data } = await axios.get('/api/logistics/enterprises', { params: { page_size: 100 } })
  enterprises.value = data.items || []
}
function openCreate() { isEdit.value = false; Object.assign(form, { id: null, enterprise_id: enterprises.value[0]?.id, planned_start: null, planned_end: null, priority: 5, notes: '' }); dialogVisible.value = true }
function openEdit(row) { isEdit.value = true; Object.assign(form, row); dialogVisible.value = true }
async function handleSave() {
  await formRef.value.validate(); saving.value = true
  try {
    if (isEdit.value) await axios.put(`/api/logistics/tasks/${form.id}`, form)
    else await axios.post('/api/logistics/tasks', form)
    ElMessage.success('操作成功'); dialogVisible.value = false; fetchData()
  } catch { ElMessage.error('操作失败') } finally { saving.value = false }
}
async function quickAction(row, action) {
  const labels = { start: '开始执行', complete: '标记完成', cancel: '取消任务' }
  await ElMessageBox.confirm(`确认 ${labels[action]}？`, '操作确认', { type: 'warning' })
  await axios.post('/api/logistics/scheduling/control', { task_id: row.id, action })
  ElMessage.success('操作成功'); fetchData()
}
onMounted(() => { fetchEnterprises(); fetchData() })
</script>
<style scoped>
.pagination-row { display: flex; justify-content: flex-end; margin-top: 16px; }
</style>
