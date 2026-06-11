<!--
  5.5 配送站管理
-->
<template>
  <PageLayout title="配送站管理" subtitle="维护配送站点档案、运行状态和服务范围">
    <template #actions>
      <el-button type="primary" @click="openCreate">
        <el-icon><Plus /></el-icon> 新增站点
      </el-button>
    </template>

    <!-- 筛选 -->
    <el-card style="margin-bottom:16px">
      <el-form inline>
        <el-form-item label="站点名称">
          <el-input v-model="filters.name" placeholder="搜索站点" clearable style="width:180px" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="filters.status" clearable style="width:120px">
            <el-option label="运行中" value="active" />
            <el-option label="停用" value="inactive" />
            <el-option label="维护中" value="maintenance" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="fetchData">查询</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-table :data="tableData" v-loading="loading" stripe border>
      <el-table-column prop="name" label="站点名称" min-width="160" />
      <el-table-column prop="code" label="编码" width="100" />
      <el-table-column prop="address" label="地址" min-width="180" show-overflow-tooltip />
      <el-table-column label="位置(经/纬)" width="160">
        <template #default="{ row }">{{ row.lng?.toFixed(4) }}, {{ row.lat?.toFixed(4) }}</template>
      </el-table-column>
      <el-table-column prop="landing_capacity" label="起降能力" width="90" />
      <el-table-column prop="service_radius" label="服务半径(km)" width="110" />
      <el-table-column prop="pending_tasks" label="待处理任务" width="110">
        <template #default="{ row }">
          <el-badge :value="row.pending_tasks" :type="row.pending_tasks > 3 ? 'danger' : 'primary'" :hidden="!row.pending_tasks">
            <span>{{ row.pending_tasks }}</span>
          </el-badge>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="row.status === 'active' ? 'success' : row.status === 'maintenance' ? 'warning' : 'info'">
            {{ { active: '运行中', inactive: '停用', maintenance: '维护中' }[row.status] }}
          </el-tag>
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

    <!-- 对话框 -->
    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑站点' : '新增站点'" width="560px">
      <el-form :model="form" ref="formRef" :rules="rules" label-width="100px">
        <el-row :gutter="16">
          <el-col :span="16"><el-form-item label="站点名称" prop="name"><el-input v-model="form.name" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="编码"><el-input v-model="form.code" /></el-form-item></el-col>
          <el-col :span="24"><el-form-item label="地址"><el-input v-model="form.address" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="经度" prop="lng"><el-input-number v-model="form.lng" :precision="6" style="width:100%" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="纬度" prop="lat"><el-input-number v-model="form.lat" :precision="6" style="width:100%" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="起降能力"><el-input-number v-model="form.landing_capacity" :min="1" :max="20" style="width:100%" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="服务半径(km)"><el-input-number v-model="form.service_radius" :precision="1" :min="0.5" style="width:100%" /></el-form-item></el-col>
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
                <el-option label="运行中" value="active" /><el-option label="停用" value="inactive" /><el-option label="维护中" value="maintenance" />
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

const loading = ref(false), saving = ref(false)
const tableData = ref([]), total = ref(0), page = ref(1), pageSize = ref(20)
const enterprises = ref([]), dialogVisible = ref(false), isEdit = ref(false), formRef = ref()
const filters = reactive({ name: '', status: '' })
const form = reactive({ id: null, name: '', code: '', address: '', lng: 113.2644, lat: 23.1291, landing_capacity: 2, service_radius: 5, enterprise_id: null, status: 'active' })
const rules = { name: [{ required: true, message: '请填写站点名称' }], enterprise_id: [{ required: true, message: '请选择企业' }] }

async function fetchData() {
  loading.value = true
  try {
    const { data } = await axios.get('/api/logistics/stations', { params: { page: page.value, page_size: pageSize.value, ...filters } })
    tableData.value = data.items || []; total.value = data.total || 0
  } catch { ElMessage.error('获取站点失败') } finally { loading.value = false }
}
async function fetchEnterprises() {
  const { data } = await axios.get('/api/logistics/enterprises', { params: { page_size: 100 } })
  enterprises.value = data.items || []
}
function openCreate() { isEdit.value = false; Object.assign(form, { id: null, name: '', code: '', address: '', lng: 113.2644, lat: 23.1291, landing_capacity: 2, service_radius: 5, enterprise_id: enterprises.value[0]?.id, status: 'active' }); dialogVisible.value = true }
function openEdit(row) { isEdit.value = true; Object.assign(form, row); dialogVisible.value = true }
async function handleSave() {
  await formRef.value.validate(); saving.value = true
  try {
    if (isEdit.value) await axios.put(`/api/logistics/stations/${form.id}`, form)
    else await axios.post('/api/logistics/stations', form)
    ElMessage.success('操作成功'); dialogVisible.value = false; fetchData()
  } catch { ElMessage.error('操作失败') } finally { saving.value = false }
}
async function handleDelete(row) {
  await ElMessageBox.confirm(`确定删除站点「${row.name}」？`, '确认', { type: 'warning' })
  await axios.delete(`/api/logistics/stations/${row.id}`)
  ElMessage.success('删除成功'); fetchData()
}
onMounted(() => { fetchEnterprises(); fetchData() })
</script>
<style scoped>
.pagination-row { display: flex; justify-content: flex-end; margin-top: 16px; }
</style>
