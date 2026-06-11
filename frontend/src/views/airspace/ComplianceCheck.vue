<!--
  2.3 航线合规审查
  检查航线是否穿越禁飞区/违反限高要求
-->
<template>
  <PageLayout title="航线合规审查" subtitle="提交航路点和飞行时间，系统自动审查合规性">
    <el-row :gutter="20">
      <!-- 左侧输入 -->
      <el-col :span="10">
        <el-card header="审查参数设置">
          <el-form label-width="90px">
            <el-form-item label="飞行时间">
              <el-date-picker v-model="taskTime" type="datetime" value-format="YYYY-MM-DDTHH:mm:ss"
                placeholder="计划执行时间" style="width:100%" />
            </el-form-item>
            <el-form-item label="航路点列表">
              <div class="wp-list">
                <div v-for="(wp, i) in waypoints" :key="i" class="wp-row">
                  <span class="wp-idx">{{ i + 1 }}</span>
                  <el-input-number v-model="wp[0]" :precision="4" placeholder="经度" size="small" style="width:100px" />
                  <el-input-number v-model="wp[1]" :precision="4" placeholder="纬度" size="small" style="width:100px" />
                  <el-input-number v-model="wp[2]" placeholder="高度(m)" size="small" style="width:90px" />
                  <el-button link type="danger" @click="removeWaypoint(i)" :disabled="waypoints.length <= 2">✕</el-button>
                </div>
              </div>
              <el-button text @click="addWaypoint" style="margin-top:8px">
                <el-icon><Plus /></el-icon> 添加航路点
              </el-button>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="runCheck" :loading="checking" block>开始审查</el-button>
              <el-button @click="loadSample" style="margin-left:8px">加载示例</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <!-- 右侧结果 -->
      <el-col :span="14">
        <el-card header="审查结果">
          <div v-if="!result" class="empty-tip">请在左侧填写参数后点击「开始审查」</div>

          <template v-else>
            <el-alert
              :title="result.compliant ? '✅ 航线合规 - 可以飞行' : `❌ 存在 ${result.violations.length} 项违规`"
              :type="result.compliant ? 'success' : 'error'"
              :closable="false"
              style="margin-bottom:16px"
            />

            <div v-if="result.violations.length" class="section">
              <div class="section-title danger">违规项</div>
              <el-timeline>
                <el-timeline-item
                  v-for="(v, i) in result.violations" :key="i"
                  type="danger" :timestamp="v.zone_name"
                >
                  {{ v.description }}
                </el-timeline-item>
              </el-timeline>
            </div>

            <div v-if="result.warnings.length" class="section">
              <div class="section-title warning">警告项（{{ result.warnings.length }}）</div>
              <el-timeline>
                <el-timeline-item
                  v-for="(w, i) in result.warnings" :key="i"
                  type="warning" :timestamp="w.zone_name"
                >
                  {{ w.description }}
                </el-timeline-item>
              </el-timeline>
            </div>

            <div v-if="result.compliant && result.warnings.length === 0" class="all-clear">
              航线通过所有合规检查，可安全执行飞行任务。
            </div>
          </template>
        </el-card>
      </el-col>
    </el-row>
  </PageLayout>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import axios from 'axios'
import PageLayout from '@/components/PageLayout.vue'

const taskTime = ref(null)
const checking = ref(false)
const result = ref(null)

const waypoints = ref([
  [113.2644, 23.1291, 120],
  [113.3000, 23.1400, 150],
])

function addWaypoint() { waypoints.value.push([113.2644, 23.1291, 120]) }
function removeWaypoint(i) { waypoints.value.splice(i, 1) }

function loadSample() {
  waypoints.value = [
    [113.2644, 23.1291, 50],
    [113.2800, 23.1350, 120],
    [113.3100, 23.1420, 150],
    [113.3303, 23.1355, 80],
  ]
  taskTime.value = new Date().toISOString().slice(0, 19)
}

async function runCheck() {
  if (waypoints.value.length < 2) {
    ElMessage.warning('至少需要2个航路点')
    return
  }
  checking.value = true
  try {
    const { data } = await axios.post('/api/airspace/compliance/check', {
      waypoints: waypoints.value,
      task_time: taskTime.value,
    })
    result.value = data
  } catch {
    ElMessage.error('审查请求失败')
  } finally {
    checking.value = false
  }
}
</script>

<style scoped>
.wp-list { display: flex; flex-direction: column; gap: 8px; }
.wp-row { display: flex; align-items: center; gap: 6px; }
.wp-idx { font-size: 12px; color: #6b7280; width: 18px; text-align: right; }
.empty-tip { text-align: center; color: #9ca3af; padding: 60px 0; }
.section { margin-bottom: 16px; }
.section-title { font-weight: 600; margin-bottom: 8px; font-size: 13px; }
.section-title.danger { color: #dc2626; }
.section-title.warning { color: #d97706; }
.all-clear { color: #16a34a; text-align: center; padding: 24px; }
</style>
