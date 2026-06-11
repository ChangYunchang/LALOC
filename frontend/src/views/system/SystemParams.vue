<!--
  9.4 系统参数配置
-->
<template>
  <PageLayout title="系统参数配置" subtitle="维护适飞判断、风险预警、规划参数等业务阈值">
    <div v-loading="loading">
      <el-tabs v-model="activeCategory">
        <el-tab-pane
          v-for="cat in categories" :key="cat.value"
          :label="cat.label" :name="cat.value"
        >
          <el-table :data="paramsInCategory(cat.value)" border stripe>
            <el-table-column prop="param_name" label="参数名称" width="200" />
            <el-table-column prop="param_key" label="参数键" width="200" />
            <el-table-column label="当前值" width="180">
              <template #default="{ row }">
                <el-input
                  v-if="editing === row.id"
                  v-model="editVal" size="small" style="width:140px"
                  @keyup.enter="saveParam(row)"
                />
                <span v-else class="param-val">{{ row.param_value }}</span>
                <span class="param-unit">{{ row.unit }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="description" label="说明" min-width="200" show-overflow-tooltip />
            <el-table-column label="操作" width="120" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" @click="startEdit(row)" v-if="editing !== row.id">修改</el-button>
                <el-button link type="success" @click="saveParam(row)" v-if="editing === row.id">保存</el-button>
                <el-button link @click="editing = null" v-if="editing === row.id">取消</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </div>
  </PageLayout>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'
import PageLayout from '@/components/PageLayout.vue'

const CAT_LABELS = { flight_threshold: '飞行阈值', planning: '规划参数', alert: '告警阈值', external_service: '外部服务' }
const loading = ref(false), params = ref([]), editing = ref(null), editVal = ref('')
const activeCategory = ref('flight_threshold')
const categories = computed(() => [...new Set(params.value.map(p => p.category))].map(c => ({ value: c, label: CAT_LABELS[c] || c })))
const paramsInCategory = (cat) => params.value.filter(p => p.category === cat)

async function fetchParams() {
  loading.value = true
  try { const { data } = await axios.get('/api/system/params'); params.value = data.items || [] }
  catch { ElMessage.error('获取参数失败') } finally { loading.value = false }
}
function startEdit(row) { editing.value = row.id; editVal.value = row.param_value }
async function saveParam(row) {
  try {
    await axios.put(`/api/system/params/${row.id}`, { param_value: editVal.value })
    row.param_value = editVal.value
    editing.value = null
    ElMessage.success('参数已更新')
  } catch { ElMessage.error('更新失败') }
}
onMounted(fetchParams)
</script>

<style scoped>
.param-val { font-weight: 500; color: var(--text-primary); margin-right: 4px; }
.param-unit { font-size: 12px; color: #9ca3af; }
</style>
