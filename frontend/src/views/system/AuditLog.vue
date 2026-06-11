<!--
  9.5 日志审计
-->
<template>
  <PageLayout title="日志审计" subtitle="查询用户操作、服务调用和重要业务处理日志">
    <el-card style="margin-bottom:16px">
      <el-form inline>
        <el-form-item label="用户名"><el-input v-model="filters.username" clearable style="width:140px" /></el-form-item>
        <el-form-item label="模块"><el-input v-model="filters.module" clearable style="width:130px" /></el-form-item>
        <el-form-item label="结果">
          <el-select v-model="filters.result" clearable style="width:100px">
            <el-option label="成功" value="success" /><el-option label="失败" value="failure" />
          </el-select>
        </el-form-item>
        <el-form-item><el-button type="primary" @click="fetchData">查询</el-button></el-form-item>
      </el-form>
    </el-card>

    <el-table :data="tableData" v-loading="loading" stripe border>
      <el-table-column prop="username" label="操作用户" width="120" />
      <el-table-column prop="module" label="模块" width="120" />
      <el-table-column prop="action" label="操作" min-width="150" show-overflow-tooltip />
      <el-table-column prop="resource_type" label="资源类型" width="130" />
      <el-table-column prop="ip_address" label="IP地址" width="130" />
      <el-table-column label="结果" width="80">
        <template #default="{ row }">
          <el-tag :type="row.result === 'success' ? 'success' : 'danger'" size="small">{{ row.result === 'success' ? '成功' : '失败' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="时间" width="160">
        <template #default="{ row }">{{ fmtDt(row.created_at) }}</template>
      </el-table-column>
    </el-table>

    <div class="pagination-row">
      <el-pagination v-model:current-page="page" v-model:page-size="pageSize"
        :total="total" layout="total, prev, pager, next" background small @change="fetchData" />
    </div>
  </PageLayout>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'
import PageLayout from '@/components/PageLayout.vue'

const fmtDt = (s) => s ? new Date(s).toLocaleString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit' }) : '-'
const loading = ref(false), tableData = ref([]), total = ref(0), page = ref(1), pageSize = ref(30)
const filters = reactive({ username: '', module: '', result: '' })

async function fetchData() {
  loading.value = true
  try {
    const { data } = await axios.get('/api/system/logs', { params: { page: page.value, page_size: pageSize.value, ...filters } })
    tableData.value = data.items || []; total.value = data.total || 0
  } catch { ElMessage.error('获取日志失败') } finally { loading.value = false }
}
onMounted(fetchData)
</script>
<style scoped>
.pagination-row { display: flex; justify-content: flex-end; margin-top: 16px; }
</style>
