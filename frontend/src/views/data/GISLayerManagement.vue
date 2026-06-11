<!--
  8.1 GIS图层管理
-->
<template>
  <PageLayout title="GIS图层管理" subtitle="统一组织和管理平台地图中使用的业务及空间图层">
    <template #actions>
      <el-button type="primary" @click="openCreate">
        <el-icon><Plus /></el-icon> 新增图层
      </el-button>
    </template>

    <el-table :data="layers" v-loading="loading" stripe border>
      <el-table-column prop="sort_order" label="排序" width="70" />
      <el-table-column prop="name" label="图层名称" min-width="160" />
      <el-table-column prop="code" label="图层编码" width="150" />
      <el-table-column label="图层类型" width="100">
        <template #default="{ row }">
          <el-tag size="small">{{ TYPE_LABELS[row.layer_type] || row.layer_type }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="data_source" label="数据来源" min-width="160" show-overflow-tooltip />
      <el-table-column prop="description" label="说明" min-width="180" show-overflow-tooltip />
      <el-table-column label="发布状态" width="100">
        <template #default="{ row }">
          <el-switch v-model="row.published" @change="togglePublish(row)" />
        </template>
      </el-table-column>
      <el-table-column label="操作" width="120" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑图层' : '新增图层'" width="480px">
      <el-form :model="form" ref="formRef" :rules="rules" label-width="90px">
        <el-form-item label="图层名称" prop="name"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="图层编码"><el-input v-model="form.code" /></el-form-item>
        <el-form-item label="图层类型">
          <el-select v-model="form.layer_type" style="width:100%">
            <el-option v-for="(l, k) in TYPE_LABELS" :key="k" :label="l" :value="k" />
          </el-select>
        </el-form-item>
        <el-form-item label="数据来源"><el-input v-model="form.data_source" /></el-form-item>
        <el-form-item label="说明"><el-input v-model="form.description" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="排序"><el-input-number v-model="form.sort_order" :min="0" style="width:100%" /></el-form-item>
        <el-form-item label="是否发布"><el-switch v-model="form.published" /></el-form-item>
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

const TYPE_LABELS = { base: '底图', zone: '空域区域', route: '航线', poi: '兴趣点', custom: '自定义' }
const loading = ref(false), saving = ref(false), layers = ref([])
const dialogVisible = ref(false), isEdit = ref(false), formRef = ref()
const form = reactive({ id: null, name: '', code: '', layer_type: 'custom', data_source: '', description: '', sort_order: 0, published: true })
const rules = { name: [{ required: true, message: '请填写图层名称' }] }

async function fetchData() {
  loading.value = true
  try { const { data } = await axios.get('/api/system/gis-layers'); layers.value = data.items || [] }
  catch { ElMessage.error('获取图层失败') } finally { loading.value = false }
}
function openCreate() { isEdit.value = false; Object.assign(form, { id: null, name: '', code: '', layer_type: 'custom', data_source: '', description: '', sort_order: 0, published: true }); dialogVisible.value = true }
function openEdit(row) { isEdit.value = true; Object.assign(form, row); dialogVisible.value = true }
async function handleSave() {
  await formRef.value.validate(); saving.value = true
  try {
    if (isEdit.value) await axios.put(`/api/system/gis-layers/${form.id}`, form)
    else await axios.post('/api/system/gis-layers', form)
    ElMessage.success('操作成功'); dialogVisible.value = false; fetchData()
  } catch { ElMessage.error('操作失败') } finally { saving.value = false }
}
async function handleDelete(row) {
  await ElMessageBox.confirm(`确定删除图层「${row.name}」？`, '确认', { type: 'warning' })
  await axios.delete(`/api/system/gis-layers/${row.id}`)
  ElMessage.success('删除成功'); fetchData()
}
async function togglePublish(row) {
  await axios.put(`/api/system/gis-layers/${row.id}`, { published: row.published })
}
onMounted(fetchData)
</script>
