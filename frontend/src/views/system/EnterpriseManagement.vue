<!--
  9.3 企业信息管理（复用 logistics/enterprises 数据）
-->
<template>
  <PageLayout title="企业信息管理" subtitle="维护接入平台的物流运营企业档案、凭证和监管状态">
    <template #actions>
      <el-button type="primary" @click="openCreate">
        <el-icon><Plus /></el-icon> 新建企业
      </el-button>
    </template>

    <el-card style="margin-bottom:16px">
      <el-form inline>
        <el-form-item label="企业名称"><el-input v-model="filters.name" clearable style="width:200px" /></el-form-item>
        <el-form-item label="状态">
          <el-select v-model="filters.status" clearable style="width:120px">
            <el-option label="正常" value="active" /><el-option label="暂停" value="suspended" /><el-option label="限制" value="restricted" />
          </el-select>
        </el-form-item>
        <el-form-item><el-button type="primary" @click="fetchData">查询</el-button></el-form-item>
      </el-form>
    </el-card>

    <el-table :data="tableData" v-loading="loading" stripe border>
      <el-table-column prop="code" label="企业代码" width="110" />
      <el-table-column prop="name" label="企业名称" min-width="200" show-overflow-tooltip />
      <el-table-column prop="contact_person" label="联系人" width="100" />
      <el-table-column prop="contact_phone" label="联系电话" width="130" />
      <el-table-column prop="license_no" label="营业执照号" width="180" show-overflow-tooltip />
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="row.status === 'active' ? 'success' : row.status === 'suspended' ? 'warning' : 'danger'" size="small">
            {{ { active: '正常', suspended: '暂停', restricted: '限制' }[row.status] || row.status }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="API密钥" width="170">
        <template #default="{ row }">
          <span class="api-key">{{ row.api_key ? row.api_key.slice(0, 12) + '****' : '-' }}</span>
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

    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑企业' : '新建企业'" width="560px">
      <el-form :model="form" ref="formRef" :rules="rules" label-width="100px">
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="企业代码" prop="code"><el-input v-model="form.code" :disabled="isEdit" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="企业名称" prop="name"><el-input v-model="form.name" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="联系人"><el-input v-model="form.contact_person" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="联系电话"><el-input v-model="form.contact_phone" /></el-form-item></el-col>
          <el-col :span="24"><el-form-item label="企业地址"><el-input v-model="form.address" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="营业执照号"><el-input v-model="form.license_no" /></el-form-item></el-col>
          <el-col :span="12">
            <el-form-item label="监管状态">
              <el-select v-model="form.status" style="width:100%">
                <el-option label="正常" value="active" /><el-option label="暂停接入" value="suspended" /><el-option label="限制接入" value="restricted" />
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
const dialogVisible = ref(false), isEdit = ref(false), formRef = ref()
const filters = reactive({ name: '', status: '' })
const form = reactive({ id: null, code: '', name: '', contact_person: '', contact_phone: '', address: '', license_no: '', status: 'active' })
const rules = { code: [{ required: true }], name: [{ required: true, message: '请填写企业名称' }] }

async function fetchData() {
  loading.value = true
  try {
    const { data } = await axios.get('/api/logistics/enterprises', { params: { page: page.value, page_size: pageSize.value, ...filters } })
    tableData.value = data.items || []; total.value = data.total || 0
  } catch { ElMessage.error('获取企业失败') } finally { loading.value = false }
}
function openCreate() { isEdit.value = false; Object.assign(form, { id: null, code: '', name: '', contact_person: '', contact_phone: '', address: '', license_no: '', status: 'active' }); dialogVisible.value = true }
function openEdit(row) { isEdit.value = true; Object.assign(form, row); dialogVisible.value = true }
async function handleSave() {
  await formRef.value.validate(); saving.value = true
  try {
    if (isEdit.value) await axios.put(`/api/logistics/enterprises/${form.id}`, form)
    else await axios.post('/api/logistics/enterprises', form)
    ElMessage.success('操作成功'); dialogVisible.value = false; fetchData()
  } catch { ElMessage.error('操作失败') } finally { saving.value = false }
}
async function handleDelete(row) {
  await ElMessageBox.confirm(`确定删除企业「${row.name}」？`, '确认', { type: 'warning' })
  await axios.delete(`/api/logistics/enterprises/${row.id}`)
  ElMessage.success('删除成功'); fetchData()
}
onMounted(fetchData)
</script>
<style scoped>
.pagination-row { display: flex; justify-content: flex-end; margin-top: 16px; }
.api-key { font-family: monospace; font-size: 12px; color: #6b7280; }
</style>
