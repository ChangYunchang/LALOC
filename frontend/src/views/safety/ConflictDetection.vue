<!--
  6.1/6.2 航线冲突检测与低空拥堵识别
-->
<template>
  <PageLayout title="航线冲突检测" subtitle="提交航路和飞行时间，检测与其他任务的时空冲突">
    <el-row :gutter="20">
      <el-col :span="10">
        <el-card header="冲突检测参数">
          <el-form label-width="90px">
            <el-form-item label="计划开始">
              <el-date-picker v-model="form.planned_start" type="datetime" value-format="YYYY-MM-DDTHH:mm:ss" style="width:100%" />
            </el-form-item>
            <el-form-item label="计划结束">
              <el-date-picker v-model="form.planned_end" type="datetime" value-format="YYYY-MM-DDTHH:mm:ss" style="width:100%" />
            </el-form-item>
            <el-form-item label="航路点">
              <div class="wp-list">
                <div v-for="(wp, i) in form.waypoints" :key="i" class="wp-row">
                  <span class="wp-idx">{{ i + 1 }}</span>
                  <el-input-number v-model="wp[0]" :precision="4" size="small" style="width:100px" />
                  <el-input-number v-model="wp[1]" :precision="4" size="small" style="width:100px" />
                  <el-input-number v-model="wp[2]" size="small" style="width:80px" />
                  <el-button link type="danger" @click="form.waypoints.splice(i,1)" :disabled="form.waypoints.length<=2">✕</el-button>
                </div>
              </div>
              <el-button text @click="form.waypoints.push([113.26,23.13,120])">
                <el-icon><Plus /></el-icon> 添加
              </el-button>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="runCheck" :loading="checking" block>开始检测</el-button>
            </el-form-item>
          </el-form>
        </el-card>

        <!-- 拥堵状态 -->
        <el-card header="低空拥堵实时状态" style="margin-top:16px">
          <div v-loading="congLoading">
            <div v-if="congData">
              <el-alert
                :title="`当前活跃任务 ${congData.total_active_tasks} 个，${congData.congested_zones_count > 0 ? '存在拥堵区域' : '运行正常'}`"
                :type="congData.alert ? 'warning' : 'success'" :closable="false" style="margin-bottom:12px" />
              <div v-for="z in congData.zones" :key="z.area" class="cong-zone" :class="{ congested: z.congested }">
                <span class="zone-name">{{ z.area }}</span>
                <span class="zone-count">{{ z.task_count }} 任务</span>
                <el-tag size="small" :type="z.congested ? 'danger' : 'success'">{{ z.congested ? '拥堵' : '正常' }}</el-tag>
              </div>
            </div>
          </div>
          <el-button size="small" @click="fetchCongestion" style="margin-top:8px">刷新</el-button>
        </el-card>
      </el-col>

      <el-col :span="14">
        <el-card header="检测结果">
          <div v-if="!result" class="empty-tip">请在左侧填写参数后点击「开始检测」</div>
          <template v-else>
            <el-alert
              :title="result.has_conflict ? `⚠ 发现 ${result.conflicts.length} 项冲突` : '✅ 未发现飞行冲突'"
              :type="result.has_conflict ? 'warning' : 'success'" :closable="false" style="margin-bottom:16px"
            />
            <div class="result-meta">
              检测了 {{ result.checked_tasks }} 个并行任务 &nbsp;|&nbsp; {{ result.summary }}
            </div>
            <div v-if="result.conflicts.length" style="margin-top:16px">
              <div class="section-title">冲突详情</div>
              <el-table :data="result.conflicts" size="small" border>
                <el-table-column prop="task_no" label="冲突任务" width="140" />
                <el-table-column prop="conflict_type" label="冲突类型" width="130">
                  <template #default="{ row }">
                    <el-tag type="warning" size="small">
                      {{ row.conflict_type === 'route_cross' ? '航线交叉' : '缓冲区重叠' }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="description" label="描述" show-overflow-tooltip />
              </el-table>
            </div>
          </template>
        </el-card>
      </el-col>
    </el-row>
  </PageLayout>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import axios from 'axios'
import PageLayout from '@/components/PageLayout.vue'

const checking = ref(false), congLoading = ref(false)
const result = ref(null), congData = ref(null)

const form = reactive({
  planned_start: null, planned_end: null,
  waypoints: [[113.2644, 23.1291, 120], [113.3000, 23.1400, 150]],
})

async function runCheck() {
  checking.value = true
  try {
    const { data } = await axios.post('/api/safety/conflict/check', form)
    result.value = data
  } catch { ElMessage.error('检测请求失败') } finally { checking.value = false }
}

async function fetchCongestion() {
  congLoading.value = true
  try {
    const { data } = await axios.get('/api/safety/congestion')
    congData.value = data
  } catch { ElMessage.error('获取拥堵数据失败') } finally { congLoading.value = false }
}

onMounted(fetchCongestion)
</script>

<style scoped>
.wp-list { display: flex; flex-direction: column; gap: 6px; }
.wp-row { display: flex; align-items: center; gap: 6px; }
.wp-idx { font-size: 12px; color: #9ca3af; width: 16px; }
.empty-tip { color: #9ca3af; text-align: center; padding: 60px 0; }
.result-meta { font-size: 13px; color: var(--text-secondary); }
.section-title { font-weight: 600; font-size: 13px; margin-bottom: 8px; }
.cong-zone { display: flex; align-items: center; gap: 10px; padding: 6px 0; border-bottom: 1px solid #f3f4f6; }
.cong-zone:last-child { border-bottom: none; }
.cong-zone.congested { background: #fef2f2; border-radius: 4px; padding: 6px 8px; }
.zone-name { flex: 1; font-size: 13px; color: var(--text-primary); }
.zone-count { font-size: 12px; color: var(--text-secondary); }
</style>
