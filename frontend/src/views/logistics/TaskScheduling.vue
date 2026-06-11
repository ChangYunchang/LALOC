<!--
  5.7 无人机任务调度
  支持任务匹配、无人机分配和执行控制
-->
<template>
  <PageLayout title="无人机任务调度" subtitle="根据任务需求匹配空闲无人机并执行调度分配">
    <el-row :gutter="20">
      <!-- 待调度任务列表 -->
      <el-col :span="14">
        <el-card header="待调度任务">
          <el-table :data="pendingTasks" v-loading="taskLoading" size="small" border
            @row-click="selectTask" :row-class-name="rowClass" style="cursor:pointer">
            <el-table-column prop="task_no" label="任务编号" width="140" />
            <el-table-column prop="enterprise_id" label="企业ID" width="80" />
            <el-table-column prop="priority" label="优先级" width="80">
              <template #default="{ row }">
                <el-tag size="small" :type="row.priority >= 7 ? 'danger' : 'warning'">P{{ row.priority }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="计划开始" width="130">
              <template #default="{ row }">{{ fmtDt(row.planned_start) }}</template>
            </el-table-column>
            <el-table-column label="状态" width="90">
              <template #default="{ row }">
                <el-tag :type="row.status === 'pending' ? '' : 'warning'" size="small">
                  {{ row.status === 'pending' ? '待处理' : '已分配' }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
          <div class="hint">点击任务行进行调度操作</div>
        </el-card>
      </el-col>

      <!-- 调度操作面板 -->
      <el-col :span="10">
        <el-card :header="`调度操作${selectedTask ? ' - ' + selectedTask.task_no : ''}`">
          <div v-if="!selectedTask" class="empty-tip">请先在左侧选择一个待调度任务</div>

          <template v-else>
            <el-descriptions :column="1" size="small" border style="margin-bottom:16px">
              <el-descriptions-item label="任务编号">{{ selectedTask.task_no }}</el-descriptions-item>
              <el-descriptions-item label="优先级">P{{ selectedTask.priority }}</el-descriptions-item>
              <el-descriptions-item label="计划时间">{{ fmtDt(selectedTask.planned_start) }}</el-descriptions-item>
            </el-descriptions>

            <div class="section-label">匹配空闲无人机</div>
            <el-form inline style="margin-bottom:8px">
              <el-form-item label="货物重量(kg)">
                <el-input-number v-model="matchWeight" :min="0" :precision="1" size="small" style="width:110px" />
              </el-form-item>
              <el-form-item>
                <el-button size="small" @click="matchDrones" :loading="matching">匹配</el-button>
              </el-form-item>
            </el-form>

            <el-table :data="matchedDrones" size="small" border @row-click="selectDrone"
              :row-class-name="droneRowClass" style="cursor:pointer; margin-bottom:16px">
              <el-table-column prop="drone_no" label="编号" width="130" />
              <el-table-column prop="model" label="型号" />
              <el-table-column prop="battery_level" label="电量(%)" width="70" />
            </el-table>

            <div v-if="selectedDrone" class="selected-drone">
              已选择：<strong>{{ selectedDrone.drone_no }}</strong> ({{ selectedDrone.model }})
            </div>

            <div style="margin-top:16px">
              <el-button type="primary" @click="doAssign" :disabled="!selectedDrone" :loading="assigning" block>
                分配无人机
              </el-button>
            </div>

            <el-divider />

            <div class="section-label">执行控制</div>
            <div class="control-btns">
              <el-button size="small" type="success" @click="control('start')" :disabled="selectedTask.status !== 'assigned'">开始</el-button>
              <el-button size="small" type="warning" @click="control('pause')" :disabled="selectedTask.status !== 'executing'">暂停</el-button>
              <el-button size="small" type="primary" @click="control('resume')" :disabled="selectedTask.status !== 'assigned'">继续</el-button>
              <el-button size="small" type="success" @click="control('complete')" :disabled="selectedTask.status !== 'executing'">完成</el-button>
              <el-button size="small" type="danger" @click="control('cancel')">取消</el-button>
            </div>
          </template>
        </el-card>
      </el-col>
    </el-row>
  </PageLayout>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'
import PageLayout from '@/components/PageLayout.vue'

const taskLoading = ref(false), matching = ref(false), assigning = ref(false)
const pendingTasks = ref([])
const selectedTask = ref(null)
const selectedDrone = ref(null)
const matchedDrones = ref([])
const matchWeight = ref(5)

const fmtDt = (s) => s ? new Date(s).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }) : '-'
const rowClass = ({ row }) => row.id === selectedTask.value?.id ? 'selected-row' : ''
const droneRowClass = ({ row }) => row.id === selectedDrone.value?.id ? 'selected-row' : ''

async function fetchPendingTasks() {
  taskLoading.value = true
  try {
    const { data } = await axios.get('/api/logistics/tasks', { params: { page_size: 50 } })
    pendingTasks.value = (data.items || []).filter(t => ['pending', 'assigned'].includes(t.status))
  } catch { ElMessage.error('获取任务失败') } finally { taskLoading.value = false }
}

function selectTask(row) {
  selectedTask.value = row
  selectedDrone.value = null
  matchedDrones.value = []
}

function selectDrone(row) { selectedDrone.value = row }

async function matchDrones() {
  if (!selectedTask.value) return
  matching.value = true
  try {
    const { data } = await axios.post('/api/logistics/scheduling/match', {
      enterprise_id: selectedTask.value.enterprise_id,
      cargo_weight: matchWeight.value,
    })
    matchedDrones.value = data.matched_drones || []
    if (!matchedDrones.value.length) ElMessage.warning('暂无满足条件的空闲无人机')
  } catch { ElMessage.error('匹配失败') } finally { matching.value = false }
}

async function doAssign() {
  if (!selectedTask.value || !selectedDrone.value) return
  assigning.value = true
  try {
    await axios.post('/api/logistics/scheduling/assign', {
      task_id: selectedTask.value.id, drone_id: selectedDrone.value.id,
    })
    ElMessage.success(`无人机 ${selectedDrone.value.drone_no} 已分配给任务 ${selectedTask.value.task_no}`)
    fetchPendingTasks()
    selectedTask.value = null
    selectedDrone.value = null
    matchedDrones.value = []
  } catch (e) { ElMessage.error(e.response?.data?.detail || '分配失败') } finally { assigning.value = false }
}

async function control(action) {
  if (!selectedTask.value) return
  try {
    const { data } = await axios.post('/api/logistics/scheduling/control', { task_id: selectedTask.value.id, action })
    ElMessage.success(data.message)
    selectedTask.value.status = data.new_status
    fetchPendingTasks()
  } catch (e) { ElMessage.error(e.response?.data?.detail || '操作失败') }
}

onMounted(fetchPendingTasks)
</script>

<style scoped>
.hint { font-size: 12px; color: #9ca3af; text-align: center; margin-top: 8px; }
.empty-tip { color: #9ca3af; text-align: center; padding: 40px 0; }
.section-label { font-weight: 600; font-size: 13px; color: var(--text-primary); margin-bottom: 8px; }
.selected-drone { font-size: 13px; color: #16a34a; margin-top: 4px; }
.control-btns { display: flex; gap: 8px; flex-wrap: wrap; }
:deep(.selected-row) { background-color: #eff6ff !important; }
</style>
