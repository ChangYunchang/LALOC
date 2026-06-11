<!--
  5.6 无人机资源管理
-->
<template>
  <PageLayout title="无人机资源管理" subtitle="维护无人机档案、能力参数、电量和可用状态">
    <template #actions>
      <el-button type="primary" @click="openCreate">
        <el-icon><Plus /></el-icon> 新增无人机
      </el-button>
    </template>

    <el-card style="margin-bottom:16px">
      <el-form inline>
        <el-form-item label="企业">
          <el-select v-model="filters.enterprise_id" clearable placeholder="全部企业" style="width:180px">
            <el-option v-for="e in enterprises" :key="e.id" :label="e.name" :value="e.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="filters.status" clearable style="width:120px">
            <el-option label="空闲" value="idle" /><el-option label="执行任务" value="executing" />
            <el-option label="充电中" value="charging" /><el-option label="维护中" value="maintenance" />
            <el-option label="故障" value="fault" />
          </el-select>
        </el-form-item>
        <el-form-item><el-button type="primary" @click="fetchData">查询</el-button></el-form-item>
      </el-form>
    </el-card>

    <el-table :data="tableData" v-loading="loading" stripe border>
      <el-table-column prop="drone_no" label="无人机编号" width="150" />
      <el-table-column prop="model" label="型号" width="150" />
      <el-table-column prop="max_payload" label="最大载重(kg)" width="115" />
      <el-table-column prop="max_range" label="最大航程(km)" width="115" />
      <el-table-column label="电量" width="130">
        <template #default="{ row }">
          <el-progress :percentage="row.battery_level"
            :color="row.battery_level < 30 ? '#dc2626' : row.battery_level < 60 ? '#f59e0b' : '#16a34a'"
            :stroke-width="10" />
        </template>
      </el-table-column>
      <el-table-column label="状态" width="110">
        <template #default="{ row }">
          <el-tag :type="droneStatusType(row.status)">{{ droneStatusLabel(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="当前任务" width="100">
        <template #default="{ row }">
          <span v-if="row.current_task_id" class="task-link">任务 #{{ row.current_task_id }}</span>
          <span v-else class="text-gray">-</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="140" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="pagination-row">
      <el-pagination v-model:current-page="page" v-model:page-size="pageSize"
        :total="total" layout="total, prev, pager, next" background small @change="fetchData" />
    </div>

    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑无人机' : '新增无人机'" width="540px">
      <el-form :model="form" ref="formRef" :rules="rules" label-width="110px">
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="无人机编号" prop="drone_no"><el-input v-model="form.drone_no" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="型号"><el-input v-model="form.model" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="最大载重(kg)"><el-input-number v-model="form.max_payload" :min="0" style="width:100%" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="最大航程(km)"><el-input-number v-model="form.max_range" :min="0" style="width:100%" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="最大续航(分钟)"><el-input-number v-model="form.max_endurance" :min="0" style="width:100%" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="当前电量(%)"><el-input-number v-model="form.battery_level" :min="0" :max="100" style="width:100%" /></el-form-item></el-col>
          <el-col :span="12">
            <el-form-item label="所属企业" prop="enterprise_id">
              <el-select v-model="form.enterprise_id" style="width:100%">
                <el-option v-for="e in enterprises" :key="e.id" :label="e.name" :value="e.id" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="状态">
              <el-select v-model="form.status" style="width:100%">
                <el-option label="空闲" value="idle" /><el-option label="充电中" value="charging" /><el-option label="维护中" value="maintenance" />
              </el-select>
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

const DRONE_STATUS = { idle: { label: '空闲', type: 'success' }, executing: { label: '执行任务', type: 'primary' }, charging: { label: '充电中', type: 'warning' }, maintenance: { label: '维护中', type: 'info' }, fault: { label: '故障', type: 'danger' } }
const droneStatusType = (s) => DRONE_STATUS[s]?.type || ''
const droneStatusLabel = (s) => DRONE_STATUS[s]?.label || s

const loading = ref(false), saving = ref(false)
const tableData = ref([]), total = ref(0), page = ref(1), pageSize = ref(20)
const enterprises = ref([]), dialogVisible = ref(false), isEdit = ref(false), formRef = ref()
const filters = reactive({ enterprise_id: null, status: '' })
const form = reactive({ id: null, drone_no: '', model: '', max_payload: 10, max_range: 20, max_endurance: 30, battery_level: 100, enterprise_id: null, status: 'idle' })
const rules = { drone_no: [{ required: true, message: '请填写编号' }], enterprise_id: [{ required: true, message: '请选择企业' }] }

async function fetchData() {
  loading.value = true
  try {
    const { data } = await axios.get('/api/logistics/drones', { params: { page: page.value, page_size: pageSize.value, ...filters } })
    tableData.value = data.items || []; total.value = data.total || 0
  } catch { ElMessage.error('获取无人机失败') } finally { loading.value = false }
}
async function fetchEnterprises() {
  const { data } = await axios.get('/api/logistics/enterprises', { params: { page_size: 100 } })
  enterprises.value = data.items || []
}
function openCreate() { isEdit.value = false; Object.assign(form, { id: null, drone_no: '', model: '', max_payload: 10, max_range: 20, max_endurance: 30, battery_level: 100, enterprise_id: enterprises.value[0]?.id, status: 'idle' }); dialogVisible.value = true }
function openEdit(row) { isEdit.value = true; Object.assign(form, row); dialogVisible.value = true }
async function handleSave() {
  await formRef.value.validate(); saving.value = true
  try {
    if (isEdit.value) await axios.put(`/api/logistics/drones/${form.id}`, form)
    else await axios.post('/api/logistics/drones', form)
    ElMessage.success('操作成功'); dialogVisible.value = false; fetchData()
  } catch { ElMessage.error('操作失败') } finally { saving.value = false }
}
async function handleDelete(row) {
  await ElMessageBox.confirm(`确定删除无人机「${row.drone_no}」？`, '确认', { type: 'warning' })
  await axios.delete(`/api/logistics/drones/${row.id}`)
  ElMessage.success('删除成功'); fetchData()
}
onMounted(() => { fetchEnterprises(); fetchData() })
</script>
<style scoped>
.pagination-row { display: flex; justify-content: flex-end; margin-top: 16px; }
.task-link { color: #2563eb; font-size: 13px; }
.text-gray { color: #9ca3af; }
</style>
