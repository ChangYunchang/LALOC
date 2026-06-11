<!--
  1.6 企业运行监管看板
-->
<template>
  <PageLayout title="企业运行监管看板" subtitle="按企业汇总低空物流运行情况，辅助开展监管">
    <div v-loading="loading">
      <el-table :data="tableData" border stripe>
        <el-table-column prop="enterprise_name" label="企业名称" min-width="180" show-overflow-tooltip />
        <el-table-column prop="total_tasks" label="总任务数" width="100" />
        <el-table-column prop="completed_tasks" label="已完成" width="90" />
        <el-table-column label="完成率" width="150">
          <template #default="{ row }">
            <el-progress :percentage="row.completion_rate" :stroke-width="8"
              :color="row.completion_rate >= 90 ? '#16a34a' : row.completion_rate >= 70 ? '#f59e0b' : '#dc2626'" />
          </template>
        </el-table-column>
        <el-table-column prop="on_time_rate" label="准点率(%)" width="90" />
        <el-table-column prop="drone_count" label="无人机数" width="95" />
        <el-table-column prop="drone_utilization" label="无人机利用率(%)" width="130" />
        <el-table-column prop="anomaly_count" label="异常事件数" width="110">
          <template #default="{ row }">
            <el-tag :type="row.anomaly_count > 5 ? 'danger' : row.anomaly_count > 2 ? 'warning' : 'success'" size="small">
              {{ row.anomaly_count }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="viewDetail(row)">违规记录</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="detailVisible" :title="`${currentEnterprise?.enterprise_name} - 违规记录`" width="600px">
      <el-empty description="暂无违规记录" v-if="!violations.length" />
      <el-table v-else :data="violations" size="small" border>
        <el-table-column prop="event_no" label="事件编号" width="140" />
        <el-table-column prop="event_type" label="类型" width="130" />
        <el-table-column prop="description" label="描述" show-overflow-tooltip />
      </el-table>
    </el-dialog>
  </PageLayout>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'
import PageLayout from '@/components/PageLayout.vue'

const loading = ref(false), tableData = ref([]), detailVisible = ref(false)
const currentEnterprise = ref(null), violations = ref([])

async function fetchData() {
  loading.value = true
  try {
    const { data } = await axios.get('/api/statistics/enterprise/efficiency')
    tableData.value = data
  } catch { ElMessage.error('获取数据失败') } finally { loading.value = false }
}

async function viewDetail(row) {
  currentEnterprise.value = row
  try {
    const { data } = await axios.get('/api/safety/events', { params: { enterprise_id: row.enterprise_id, page_size: 20 } })
    violations.value = data.items || []
  } catch {}
  detailVisible.value = true
}

onMounted(fetchData)
</script>
