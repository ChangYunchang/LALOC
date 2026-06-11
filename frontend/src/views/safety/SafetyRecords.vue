<!--
  6.5 安全监管台账
-->
<template>
  <PageLayout title="安全监管台账" subtitle="汇总安全监管活动和异常处置记录，支持查询与归档">
    <template #actions>
      <el-button type="primary" @click="openCreate">
        <el-icon><Plus /></el-icon> 新增记录
      </el-button>
    </template>

    <el-card style="margin-bottom:16px">
      <el-form inline>
        <el-form-item label="记录类型">
          <el-select v-model="filters.record_type" clearable style="width:130px">
            <el-option label="事件处置" value="event" /><el-option label="巡查检查" value="inspection" />
            <el-option label="违规记录" value="violation" /><el-option label="告警记录" value="alert" />
          </el-select>
        </el-form-item>
        <el-form-item label="归档状态">
          <el-select v-model="archivedFilter" clearable style="width:110px">
            <el-option label="未归档" :value="0" /><el-option label="已归档" :value="1" />
          </el-select>
        </el-form-item>
        <el-form-item><el-button type="primary" @click="fetchData">查询</el-button></el-form-item>
      </el-form>
    </el-card>

    <el-table :data="tableData" v-loading="loading" stripe border>
      <el-table-column prop="record_no" label="记录编号" width="140" />
      <el-table-column label="类型" width="100">
        <template #default="{ row }">
          <el-tag size="small">{{ typeLabel(row.record_type) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="title" label="记录标题" min-width="200" show-overflow-tooltip />
      <el-table-column prop="content" label="内容" min-width="200" show-overflow-tooltip />
      <el-table-column prop="result" label="处理结果" width="120" />
      <el-table-column prop="operator" label="操作人" width="100" />
      <el-table-column label="记录时间" width="150">
        <template #default="{ row }">{{ fmtDt(row.record_time) }}</template>
      </el-table-column>
      <el-table-column label="归档" width="80">
        <template #default="{ row }">
          <el-tag :type="row.archived ? 'success' : 'info'" size="small">{{ row.archived ? '已归档' : '未归档' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="120" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="doArchive(row)" v-if="!row.archived">归档</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="pagination-row">
      <el-pagination v-model:current-page="page" v-model:page-size="pageSize"
        :total="total" layout="total, prev, pager, next" background small @change="fetchData" />
    </div>

    <el-dialog v-model="createVisible" title="新增监管记录" width="500px">
      <el-form :model="form" ref="formRef" label-width="100px">
        <el-form-item label="记录类型">
          <el-select v-model="form.record_type" style="width:100%">
            <el-option label="事件处置" value="event" /><el-option label="巡查检查" value="inspection" />
            <el-option label="违规记录" value="violation" /><el-option label="告警记录" value="alert" />
          </el-select>
        </el-form-item>
        <el-form-item label="记录标题"><el-input v-model="form.title" /></el-form-item>
        <el-form-item label="内容"><el-input v-model="form.content" type="textarea" :rows="3" /></el-form-item>
        <el-form-item label="处理结果"><el-input v-model="form.result" /></el-form-item>
        <el-form-item label="操作人"><el-input v-model="form.operator" /></el-form-item>
        <el-form-item label="记录时间">
          <el-date-picker v-model="form.record_time" type="datetime" value-format="YYYY-MM-DDTHH:mm:ss" style="width:100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="doCreate">保存</el-button>
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

const typeLabel = (t) => ({ event: '事件处置', inspection: '巡查检查', violation: '违规记录', alert: '告警记录' }[t] || t)
const fmtDt = (s) => s ? new Date(s).toLocaleString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }) : '-'

const loading = ref(false), saving = ref(false)
const tableData = ref([]), total = ref(0), page = ref(1), pageSize = ref(20)
const createVisible = ref(false), formRef = ref()
const filters = reactive({ record_type: '' })
const archivedFilter = ref(null)
const form = reactive({ record_type: 'event', title: '', content: '', result: '', operator: '管理员', record_time: null })

async function fetchData() {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize.value, ...filters }
    if (archivedFilter.value !== null) params.archived = archivedFilter.value
    const { data } = await axios.get('/api/safety/records', { params })
    tableData.value = data.items || []; total.value = data.total || 0
  } catch { ElMessage.error('获取台账失败') } finally { loading.value = false }
}
function openCreate() { Object.assign(form, { record_type: 'event', title: '', content: '', result: '', operator: '管理员', record_time: new Date().toISOString().slice(0, 19) }); createVisible.value = true }
async function doCreate() {
  saving.value = true
  try { await axios.post('/api/safety/records', form); ElMessage.success('创建成功'); createVisible.value = false; fetchData() }
  catch { ElMessage.error('操作失败') } finally { saving.value = false }
}
async function doArchive(row) {
  await ElMessageBox.confirm('确认归档此记录？', '归档确认', { type: 'warning' })
  await axios.put(`/api/safety/records/${row.id}/archive`)
  ElMessage.success('已归档'); fetchData()
}
onMounted(fetchData)
</script>
<style scoped>
.pagination-row { display: flex; justify-content: flex-end; margin-top: 16px; }
</style>
