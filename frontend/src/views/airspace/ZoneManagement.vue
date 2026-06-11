<!--
  2.1 空域规则管理
  提供禁飞区和限高区的查询、新建、编辑、删除功能
-->
<template>
  <PageLayout title="空域规则管理" subtitle="维护禁飞区、限高区等空域约束规则">
    <template #actions>
      <el-button type="primary" @click="openCreate">
        <el-icon><Plus /></el-icon> 新建区域
      </el-button>
    </template>

    <!-- 标签切换 -->
    <el-tabs v-model="activeTab" @tab-change="fetchData">
      <el-tab-pane label="禁飞区" name="no-fly">
        <ZoneTable
          :data="tableData" :loading="loading" zone-type="no-fly"
          @edit="openEdit" @delete="handleDelete"
        />
      </el-tab-pane>
      <el-tab-pane label="限高区" name="height-limit">
        <ZoneTable
          :data="tableData" :loading="loading" zone-type="height-limit"
          @edit="openEdit" @delete="handleDelete"
        />
      </el-tab-pane>
    </el-tabs>

    <!-- 分页 -->
    <div class="pagination-row">
      <el-pagination
        v-model:current-page="page" v-model:page-size="pageSize"
        :total="total" layout="total, prev, pager, next"
        @change="fetchData" background small
      />
    </div>

    <!-- 新建/编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑区域' : '新建区域'" width="520px">
      <el-form :model="form" :rules="rules" ref="formRef" label-width="100px">
        <el-form-item label="区域名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入区域名称" />
        </el-form-item>
        <el-form-item v-if="activeTab === 'no-fly'" label="最低限高(m)" prop="altitude_min">
          <el-input-number v-model="form.altitude_min" :min="0" :max="9999" />
        </el-form-item>
        <el-form-item v-if="activeTab === 'no-fly'" label="最高限高(m)" prop="altitude_max">
          <el-input-number v-model="form.altitude_max" :min="0" :max="9999" />
        </el-form-item>
        <el-form-item v-if="activeTab === 'height-limit'" label="最大飞行高(m)" prop="max_altitude">
          <el-input-number v-model="form.max_altitude" :min="0" :max="9999" />
        </el-form-item>
        <el-form-item label="限制原因" prop="reason">
          <el-input v-model="form.reason" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="生效开始">
          <el-date-picker v-model="form.effective_start" type="datetime" value-format="YYYY-MM-DDTHH:mm:ss" />
        </el-form-item>
        <el-form-item label="生效结束">
          <el-date-picker v-model="form.effective_end" type="datetime" value-format="YYYY-MM-DDTHH:mm:ss" />
        </el-form-item>
        <el-form-item label="坐标(GeoJSON)" prop="coordinates">
          <el-input v-model="coordsText" type="textarea" :rows="3"
            placeholder='[[lng,lat],[lng,lat],...]' />
          <div class="form-hint">输入多边形顶点坐标数组，如 [[113.26,23.12],[113.28,23.12],...]</div>
        </el-form-item>
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
import ZoneTable from './ZoneTable.vue'

const activeTab = ref('no-fly')
const loading = ref(false)
const saving = ref(false)
const tableData = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)

const dialogVisible = ref(false)
const isEdit = ref(false)
const formRef = ref()
const coordsText = ref('')

const form = reactive({
  id: null, name: '', altitude_min: 0, altitude_max: 9999,
  max_altitude: 120, min_altitude: 0, reason: '',
  effective_start: null, effective_end: null,
})

const rules = {
  name: [{ required: true, message: '请输入区域名称', trigger: 'blur' }],
  max_altitude: [{ required: true, message: '请输入最大飞行高度', trigger: 'blur' }],
}

async function fetchData() {
  loading.value = true
  try {
    const endpoint = activeTab.value === 'no-fly' ? 'no-fly-zones' : 'height-limit-zones'
    const { data } = await axios.get(`/api/airspace/${endpoint}`, {
      params: { page: page.value, page_size: pageSize.value }
    })
    tableData.value = data.items || []
    total.value = data.total || 0
  } catch {
    ElMessage.error('获取数据失败')
  } finally {
    loading.value = false
  }
}

function openCreate() {
  isEdit.value = false
  Object.assign(form, { id: null, name: '', altitude_min: 0, altitude_max: 9999, max_altitude: 120, reason: '', effective_start: null, effective_end: null })
  coordsText.value = ''
  dialogVisible.value = true
}

function openEdit(row) {
  isEdit.value = true
  Object.assign(form, row)
  coordsText.value = ''
  dialogVisible.value = true
}

async function handleSave() {
  await formRef.value.validate()
  saving.value = true
  try {
    let coords = []
    if (coordsText.value.trim()) {
      coords = JSON.parse(coordsText.value.trim())
    }
    const payload = { ...form, coordinates: coords.length ? coords : undefined }
    const endpoint = activeTab.value === 'no-fly' ? 'no-fly-zones' : 'height-limit-zones'
    if (isEdit.value) {
      await axios.put(`/api/airspace/${endpoint}/${form.id}`, payload)
      ElMessage.success('更新成功')
    } else {
      await axios.post(`/api/airspace/${endpoint}`, payload)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    fetchData()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '操作失败')
  } finally {
    saving.value = false
  }
}

async function handleDelete(row) {
  await ElMessageBox.confirm(`确定删除区域「${row.name}」？`, '确认删除', { type: 'warning' })
  const endpoint = activeTab.value === 'no-fly' ? 'no-fly-zones' : 'height-limit-zones'
  await axios.delete(`/api/airspace/${endpoint}/${row.id}`)
  ElMessage.success('删除成功')
  fetchData()
}

onMounted(fetchData)
</script>

<style scoped>
.pagination-row { display: flex; justify-content: flex-end; margin-top: 16px; }
.form-hint { font-size: 12px; color: #9ca3af; margin-top: 4px; }
</style>
