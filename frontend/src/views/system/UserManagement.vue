<!--
  9.1 用户管理
-->
<template>
  <PageLayout title="用户管理" subtitle="维护平台用户账号、角色和状态">
    <template #actions>
      <el-button type="primary" @click="openCreate">
        <el-icon><Plus /></el-icon> 新建用户
      </el-button>
    </template>

    <el-card style="margin-bottom:16px">
      <el-form inline>
        <el-form-item label="用户名"><el-input v-model="filters.username" clearable style="width:160px" /></el-form-item>
        <el-form-item label="角色">
          <el-select v-model="filters.role" clearable style="width:120px">
            <el-option label="管理员" value="admin" /><el-option label="监管员" value="supervisor" />
            <el-option label="操作员" value="operator" /><el-option label="企业用户" value="enterprise" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="filters.status" clearable style="width:110px">
            <el-option label="正常" value="active" /><el-option label="停用" value="inactive" /><el-option label="锁定" value="locked" />
          </el-select>
        </el-form-item>
        <el-form-item><el-button type="primary" @click="fetchData">查询</el-button></el-form-item>
      </el-form>
    </el-card>

    <el-table :data="tableData" v-loading="loading" stripe border>
      <el-table-column prop="username" label="用户名" width="130" />
      <el-table-column prop="real_name" label="姓名" width="100" />
      <el-table-column prop="email" label="邮箱" min-width="180" />
      <el-table-column prop="phone" label="手机号" width="130" />
      <el-table-column label="角色" width="100">
        <template #default="{ row }">
          <el-tag :type="roleType(row.role)" size="small">{{ roleLabel(row.role) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="row.status === 'active' ? 'success' : row.status === 'locked' ? 'danger' : 'info'" size="small">
            {{ { active: '正常', inactive: '停用', locked: '锁定' }[row.status] }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="最近登录" width="150">
        <template #default="{ row }">{{ fmtDt(row.last_login) || '从未登录' }}</template>
      </el-table-column>
      <el-table-column label="操作" width="160" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button link :type="row.status === 'active' ? 'warning' : 'success'" @click="toggleStatus(row)">
            {{ row.status === 'active' ? '停用' : '启用' }}
          </el-button>
          <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="pagination-row">
      <el-pagination v-model:current-page="page" v-model:page-size="pageSize"
        :total="total" layout="total, prev, pager, next" background small @change="fetchData" />
    </div>

    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑用户' : '新建用户'" width="500px">
      <el-form :model="form" ref="formRef" :rules="rules" label-width="90px">
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="用户名" prop="username"><el-input v-model="form.username" :disabled="isEdit" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="真实姓名"><el-input v-model="form.real_name" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="邮箱"><el-input v-model="form.email" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="手机号"><el-input v-model="form.phone" /></el-form-item></el-col>
          <el-col :span="12">
            <el-form-item label="角色">
              <el-select v-model="form.role" style="width:100%">
                <el-option label="管理员" value="admin" /><el-option label="监管员" value="supervisor" /><el-option label="操作员" value="operator" /><el-option label="企业用户" value="enterprise" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="状态">
              <el-select v-model="form.status" style="width:100%">
                <el-option label="正常" value="active" /><el-option label="停用" value="inactive" />
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

const ROLES = { admin: { label: '管理员', type: 'danger' }, supervisor: { label: '监管员', type: 'warning' }, operator: { label: '操作员', type: 'primary' }, enterprise: { label: '企业用户', type: 'success' } }
const roleLabel = (r) => ROLES[r]?.label || r
const roleType = (r) => ROLES[r]?.type || ''
const fmtDt = (s) => s ? new Date(s).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }) : null

const loading = ref(false), saving = ref(false)
const tableData = ref([]), total = ref(0), page = ref(1), pageSize = ref(20)
const dialogVisible = ref(false), isEdit = ref(false), formRef = ref()
const filters = reactive({ username: '', role: '', status: '' })
const form = reactive({ id: null, username: '', real_name: '', email: '', phone: '', role: 'operator', status: 'active' })
const rules = { username: [{ required: true, message: '请填写用户名' }] }

async function fetchData() {
  loading.value = true
  try {
    const { data } = await axios.get('/api/system/users', { params: { page: page.value, page_size: pageSize.value, ...filters } })
    tableData.value = data.items || []; total.value = data.total || 0
  } catch { ElMessage.error('获取用户失败') } finally { loading.value = false }
}
function openCreate() { isEdit.value = false; Object.assign(form, { id: null, username: '', real_name: '', email: '', phone: '', role: 'operator', status: 'active' }); dialogVisible.value = true }
function openEdit(row) { isEdit.value = true; Object.assign(form, row); dialogVisible.value = true }
async function handleSave() {
  await formRef.value.validate(); saving.value = true
  try {
    if (isEdit.value) await axios.put(`/api/system/users/${form.id}`, form)
    else await axios.post('/api/system/users', form)
    ElMessage.success('操作成功'); dialogVisible.value = false; fetchData()
  } catch (e) { ElMessage.error(e.response?.data?.detail || '操作失败') } finally { saving.value = false }
}
async function toggleStatus(row) {
  const newStatus = row.status === 'active' ? 'inactive' : 'active'
  await axios.put(`/api/system/users/${row.id}`, { status: newStatus })
  ElMessage.success('状态已更新'); fetchData()
}
async function handleDelete(row) {
  await ElMessageBox.confirm(`确定删除用户「${row.username}」？`, '确认', { type: 'warning' })
  await axios.delete(`/api/system/users/${row.id}`)
  ElMessage.success('删除成功'); fetchData()
}
onMounted(fetchData)
</script>
<style scoped>
.pagination-row { display: flex; justify-content: flex-end; margin-top: 16px; }
</style>
