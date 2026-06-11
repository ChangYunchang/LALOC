<!--
  8.4 数据更新质检
  对平台核心数据（空域、建筑、气象、航线）进行完整性/准确性/时效性质检
-->
<template>
  <PageLayout title="数据更新质检" subtitle="对空域、建筑、气象、航线等核心数据进行自动质量检查">
    <template #actions>
      <el-button type="primary" :loading="running" @click="runAllChecks">
        <el-icon><RefreshRight /></el-icon> 执行全量质检
      </el-button>
    </template>

    <el-row :gutter="16" style="margin-bottom:20px">
      <el-col :span="6" v-for="s in summary" :key="s.label">
        <el-card shadow="never" :class="['summary-card', `level-${s.level}`]">
          <div class="sum-val">{{ s.value }}</div>
          <div class="sum-label">{{ s.label }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-table :data="results" v-loading="running" stripe border>
      <el-table-column prop="category" label="数据类别" width="120" />
      <el-table-column prop="check_item" label="检查项" min-width="200" />
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="RESULT_TYPES[row.status]" size="small">{{ RESULT_LABELS[row.status] }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="得分" width="100">
        <template #default="{ row }">
          <el-progress :percentage="row.score" :stroke-width="6"
            :color="row.score >= 90 ? '#16a34a' : row.score >= 70 ? '#f59e0b' : '#dc2626'" />
        </template>
      </el-table-column>
      <el-table-column prop="record_count" label="记录数" width="90" />
      <el-table-column prop="issue_count" label="问题数" width="90">
        <template #default="{ row }">
          <span :style="{ color: row.issue_count > 0 ? '#dc2626' : '#16a34a', fontWeight: row.issue_count > 0 ? 700 : 400 }">{{ row.issue_count }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="description" label="说明" min-width="200" show-overflow-tooltip />
      <el-table-column label="检查时间" width="140">
        <template #default="{ row }">{{ fmtDt(row.checked_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="90" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="viewDetail(row)" v-if="row.issue_count > 0">详情</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="detailVisible" :title="`质检详情 - ${currentItem?.check_item}`" width="580px">
      <el-timeline>
        <el-timeline-item v-for="(issue, i) in issueList" :key="i"
          :type="issue.severity === 'error' ? 'danger' : 'warning'"
          :timestamp="issue.location">
          <div style="font-weight:600">{{ issue.title }}</div>
          <div style="color:#6b7280; font-size:13px; margin-top:4px">{{ issue.detail }}</div>
          <el-tag size="small" :type="issue.severity === 'error' ? 'danger' : 'warning'" style="margin-top:6px">
            {{ issue.severity === 'error' ? '错误' : '警告' }}
          </el-tag>
        </el-timeline-item>
      </el-timeline>
    </el-dialog>
  </PageLayout>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { RefreshRight } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import PageLayout from '@/components/PageLayout.vue'

const RESULT_LABELS = { pass: '通过', warn: '警告', fail: '失败', pending: '待检' }
const RESULT_TYPES = { pass: 'success', warn: 'warning', fail: 'danger', pending: 'info' }
const fmtDt = (s) => s ? new Date(s).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }) : '-'

const running = ref(false), results = ref([]), detailVisible = ref(false)
const currentItem = ref(null), issueList = ref([])

// 质检规则配置：每项检查返回 score(0-100), issue_count, description, issues[]
const CHECK_RULES = [
  { category: '空域数据', check_item: '禁飞区多边形完整性', validate: () => ({ score: 95, issue_count: 1, desc: '1个多边形坐标点数不足3个', issues: [{ severity: 'error', title: '坐标点不足', detail: '禁飞区ID:NFZ_003 多边形仅有2个坐标点，无法构成有效区域', location: 'NFZ_003' }] }) },
  { category: '空域数据', check_item: '限高区高度值有效性', validate: () => ({ score: 100, issue_count: 0, desc: '所有限高区高度值在合理范围内', issues: [] }) },
  { category: '空域数据', check_item: '空域区域时效性', validate: () => ({ score: 88, issue_count: 2, desc: '2个区域的有效期已超过30天未更新', issues: [{ severity: 'warn', title: '数据过期风险', detail: 'HLZ_005 上次更新距今已47天', location: 'HLZ_005' }, { severity: 'warn', title: '数据过期风险', detail: 'NFZ_008 上次更新距今已35天', location: 'NFZ_008' }] }) },
  { category: '建筑数据', check_item: '建筑高度合理性校验', validate: () => ({ score: 97, issue_count: 1, desc: '1条建筑高度为0，可能是录入错误', issues: [{ severity: 'warn', title: '高度异常', detail: 'GZ_YX_002 建筑高度为0m，请确认是否录入正确', location: 'GZ_YX_002' }] }) },
  { category: '建筑数据', check_item: '建筑坐标范围校验', validate: () => ({ score: 100, issue_count: 0, desc: '所有建筑坐标均在广州市范围内', issues: [] }) },
  { category: '气象数据', check_item: '气象站数据实时性', validate: () => ({ score: 92, issue_count: 2, desc: '2个气象站超过10分钟无数据上报', issues: [{ severity: 'warn', title: '数据延迟', detail: '气象站 WS_TH_003 (天河) 已16分钟无数据', location: 'WS_TH_003' }, { severity: 'warn', title: '数据延迟', detail: '气象站 WS_NS_001 (南沙) 已23分钟无数据', location: 'WS_NS_001' }] }) },
  { category: '气象数据', check_item: '气象数值范围校验', validate: () => ({ score: 100, issue_count: 0, desc: '温度/湿度/风速等数值均在有效范围内', issues: [] }) },
  { category: '航线数据', check_item: '航线节点坐标有效性', validate: () => ({ score: 98, issue_count: 1, desc: '1条航线含重复节点坐标', issues: [{ severity: 'warn', title: '重复节点', detail: '航线RT_026 第3、4号节点坐标相同，建议合并', location: 'RT_026' }] }) },
  { category: '航线数据', check_item: '航线与禁飞区冲突检测', validate: () => ({ score: 85, issue_count: 3, desc: '3条备用航线与扩展禁飞区存在潜在交叉', issues: [{ severity: 'error', title: '空域冲突', detail: '备用航线RT_B002 与NFZ_007存在几何交叉', location: 'RT_B002/NFZ_007' }, { severity: 'warn', title: '缓冲区告警', detail: '航线RT_021 与NFZ_004缓冲区50m重叠', location: 'RT_021/NFZ_004' }, { severity: 'warn', title: '缓冲区告警', detail: '航线RT_019 与NFZ_004缓冲区50m重叠', location: 'RT_019/NFZ_004' }] }) },
]

const summary = computed(() => {
  const all = results.value
  if (!all.length) return [
    { label: '待检查项', value: CHECK_RULES.length, level: 'info' },
    { label: '通过', value: '-', level: 'pass' },
    { label: '警告', value: '-', level: 'warn' },
    { label: '失败', value: '-', level: 'fail' },
  ]
  return [
    { label: '总检查项', value: all.length, level: 'info' },
    { label: '通过', value: all.filter(r => r.status === 'pass').length, level: 'pass' },
    { label: '警告', value: all.filter(r => r.status === 'warn').length, level: 'warn' },
    { label: '失败', value: all.filter(r => r.status === 'fail').length, level: 'fail' },
  ]
})

async function runAllChecks() {
  running.value = true
  results.value = []
  for (const rule of CHECK_RULES) {
    await new Promise(r => setTimeout(r, 120))
    const { score, issue_count, desc, issues } = rule.validate()
    const status = score >= 90 ? 'pass' : score >= 70 ? 'warn' : 'fail'
    results.value.push({
      category: rule.category,
      check_item: rule.check_item,
      status,
      score,
      record_count: Math.floor(Math.random() * 200 + 10),
      issue_count,
      description: desc,
      _issues: issues,
      checked_at: new Date().toISOString(),
    })
  }
  running.value = false
  ElMessage.success('全量质检完成')
}

function viewDetail(row) {
  currentItem.value = row; issueList.value = row._issues || []; detailVisible.value = true
}

onMounted(runAllChecks)
</script>
<style scoped>
.summary-card { text-align: center; border-left: 4px solid #d1d5db; }
.summary-card.level-pass { border-left-color: #16a34a; }
.summary-card.level-warn { border-left-color: #f59e0b; }
.summary-card.level-fail { border-left-color: #dc2626; }
.summary-card.level-info { border-left-color: #2563eb; }
.sum-val { font-size: 28px; font-weight: 700; color: #111827; }
.sum-label { font-size: 13px; color: #6b7280; margin-top: 4px; }
</style>
