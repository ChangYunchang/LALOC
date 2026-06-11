<!--
  空域规则表格子组件（禁飞区/限高区通用）
-->
<template>
  <el-table :data="data" v-loading="loading" stripe border style="width:100%">
    <el-table-column prop="id" label="ID" width="60" />
    <el-table-column prop="name" label="区域名称" min-width="160" show-overflow-tooltip />
    <el-table-column v-if="zoneType === 'no-fly'" label="限制高度" width="160">
      <template #default="{ row }">
        {{ row.altitude_min }}m ～ {{ row.altitude_max }}m
      </template>
    </el-table-column>
    <el-table-column v-if="zoneType === 'height-limit'" label="最大飞行高度" width="130">
      <template #default="{ row }">
        {{ row.max_altitude }}m
      </template>
    </el-table-column>
    <el-table-column prop="reason" label="限制原因" min-width="180" show-overflow-tooltip />
    <el-table-column label="生效时间" width="240">
      <template #default="{ row }">
        <span v-if="row.effective_start">
          {{ fmtDt(row.effective_start) }} ～ {{ fmtDt(row.effective_end) || '长期' }}
        </span>
        <span v-else class="text-gray">长期有效</span>
      </template>
    </el-table-column>
    <el-table-column label="操作" width="140" fixed="right">
      <template #default="{ row }">
        <el-button link type="primary" @click="$emit('edit', row)">编辑</el-button>
        <el-button link type="danger" @click="$emit('delete', row)">删除</el-button>
      </template>
    </el-table-column>
  </el-table>
</template>

<script setup>
defineProps({
  data: Array,
  loading: Boolean,
  zoneType: { type: String, default: 'no-fly' },
})
defineEmits(['edit', 'delete'])

function fmtDt(s) {
  if (!s) return ''
  return new Date(s).toLocaleString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}
</script>

<style scoped>
.text-gray { color: #9ca3af; }
</style>
