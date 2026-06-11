<!--
  8.2 三维建筑数据管理
  用于管理低空空域感知所需的三维建筑障碍物数据集
-->
<template>
  <PageLayout title="三维建筑数据管理" subtitle="管理城市三维建筑障碍物数据，为航路规划提供避障依据">
    <template #actions>
      <el-upload :show-file-list="false" :before-upload="handleUpload" accept=".json,.geojson,.csv">
        <el-button><el-icon><Upload /></el-icon> 导入数据</el-button>
      </el-upload>
      <el-button type="primary" @click="openCreate" style="margin-left:8px">
        <el-icon><Plus /></el-icon> 手动录入
      </el-button>
    </template>

    <el-row :gutter="16" style="margin-bottom:16px">
      <el-col :span="6" v-for="s in stats" :key="s.label">
        <el-card shadow="never" class="stat-card">
          <div class="stat-label">{{ s.label }}</div>
          <div class="stat-value" :style="{ color: s.color }">{{ s.value }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-card style="margin-bottom:16px">
      <el-form inline>
        <el-form-item label="区域"><el-input v-model="filters.district" clearable style="width:130px" placeholder="行政区" /></el-form-item>
        <el-form-item label="高度范围">
          <el-input-number v-model="filters.min_height" :min="0" style="width:90px" placeholder="最小" />
          <span style="margin:0 4px">~</span>
          <el-input-number v-model="filters.max_height" :min="0" style="width:90px" placeholder="最大" />
          <span style="margin-left:4px">m</span>
        </el-form-item>
        <el-form-item><el-button type="primary" @click="fetchData">查询</el-button></el-form-item>
      </el-form>
    </el-card>

    <el-table :data="tableData" v-loading="loading" stripe border>
      <el-table-column prop="building_id" label="建筑ID" width="130" />
      <el-table-column prop="name" label="建筑名称" min-width="160" show-overflow-tooltip />
      <el-table-column prop="district" label="行政区" width="100" />
      <el-table-column prop="address" label="地址" min-width="200" show-overflow-tooltip />
      <el-table-column label="底部高度(m)" width="110">
        <template #default="{ row }">{{ row.base_elevation ?? 0 }}</template>
      </el-table-column>
      <el-table-column label="建筑高度(m)" width="110">
        <template #default="{ row }">
          <el-tag :type="row.height >= 100 ? 'danger' : row.height >= 50 ? 'warning' : 'info'" size="small">{{ row.height }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="顶部海拔(m)" width="110">
        <template #default="{ row }">{{ (row.base_elevation ?? 0) + row.height }}</template>
      </el-table-column>
      <el-table-column prop="data_source" label="数据来源" width="120" />
      <el-table-column label="操作" width="120" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="pagination-row">
      <el-pagination v-model:current-page="page" v-model:page-size="pageSize"
        :total="total" layout="total, prev, pager, next" background small @change="fetchData" />
    </div>

    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑建筑数据' : '录入建筑数据'" width="520px">
      <el-form :model="form" ref="formRef" :rules="rules" label-width="100px">
        <el-row :gutter="12">
          <el-col :span="12"><el-form-item label="建筑ID" prop="building_id"><el-input v-model="form.building_id" :disabled="isEdit" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="建筑名称"><el-input v-model="form.name" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="行政区"><el-input v-model="form.district" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="数据来源"><el-input v-model="form.data_source" /></el-form-item></el-col>
          <el-col :span="24"><el-form-item label="地址"><el-input v-model="form.address" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="经度" prop="lng"><el-input-number v-model="form.lng" :precision="6" style="width:100%" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="纬度" prop="lat"><el-input-number v-model="form.lat" :precision="6" style="width:100%" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="底部高度(m)"><el-input-number v-model="form.base_elevation" :min="0" style="width:100%" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="建筑高度(m)" prop="height"><el-input-number v-model="form.height" :min="1" style="width:100%" /></el-form-item></el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </PageLayout>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Upload } from '@element-plus/icons-vue'
import PageLayout from '@/components/PageLayout.vue'

// 建筑数据由前端本地管理（后端无专用endpoint，通过GIS图层机制提供给航路规划模块）
const loading = ref(false), saving = ref(false)
const tableData = ref([]), total = ref(0), page = ref(1), pageSize = ref(20)
const dialogVisible = ref(false), isEdit = ref(false), formRef = ref()
const filters = reactive({ district: '', min_height: null, max_height: null })
const form = reactive({ id: null, building_id: '', name: '', district: '', address: '', lng: 113.3, lat: 23.1, base_elevation: 0, height: 30, data_source: '人工录入' })
const rules = { building_id: [{ required: true, message: '请填写建筑ID' }], height: [{ required: true, type: 'number', min: 1, message: '建筑高度必须大于0' }] }

// 模拟种子数据 —— 实际部署时应从PostGIS buildings表获取
const SEED = [
  { id: 1, building_id: 'GZ_CBD_001', name: '广州国际金融中心', district: '天河区', address: '珠江新城花城大道6号', lng: 113.3245, lat: 23.1201, base_elevation: 10, height: 440, data_source: 'GIS导入' },
  { id: 2, building_id: 'GZ_CBD_002', name: '广州周大福金融中心', district: '天河区', address: '珠江新城兴盛路128号', lng: 113.3278, lat: 23.1188, base_elevation: 10, height: 530, data_source: 'GIS导入' },
  { id: 3, building_id: 'GZ_HZ_001', name: '广州塔', district: '海珠区', address: '赤岗塔路222号', lng: 113.3244, lat: 23.1066, base_elevation: 0, height: 600, data_source: 'GIS导入' },
  { id: 4, building_id: 'GZ_YX_001', name: '白云机场T1航站楼', district: '白云区', address: '白云机场', lng: 113.2994, lat: 23.3924, base_elevation: 11, height: 45, data_source: 'CAD转换' },
  { id: 5, building_id: 'GZ_PY_001', name: '广州南站综合体', district: '番禺区', address: '番禺区石壁街', lng: 113.2671, lat: 22.9748, base_elevation: 0, height: 28, data_source: 'CAD转换' },
]

const stats = computed(() => {
  const all = tableData.value
  const maxH = all.length ? Math.max(...all.map(b => b.height)) : 0
  const above100 = all.filter(b => b.height >= 100).length
  return [
    { label: '建筑总数', value: total.value, color: '#2563eb' },
    { label: '100m以上超高', value: above100, color: '#dc2626' },
    { label: '最高建筑(m)', value: maxH, color: '#d97706' },
    { label: '数据更新', value: '今日', color: '#16a34a' },
  ]
})

function applyFilters(list) {
  return list.filter(b => {
    if (filters.district && !b.district.includes(filters.district)) return false
    if (filters.min_height != null && b.height < filters.min_height) return false
    if (filters.max_height != null && b.height > filters.max_height) return false
    return true
  })
}

function fetchData() {
  loading.value = true
  setTimeout(() => {
    const stored = JSON.parse(localStorage.getItem('buildings_data') || 'null') || SEED
    const filtered = applyFilters(stored)
    total.value = filtered.length
    const start = (page.value - 1) * pageSize.value
    tableData.value = filtered.slice(start, start + pageSize.value)
    loading.value = false
  }, 300)
}

function openCreate() {
  isEdit.value = false
  Object.assign(form, { id: null, building_id: '', name: '', district: '', address: '', lng: 113.3, lat: 23.1, base_elevation: 0, height: 30, data_source: '人工录入' })
  dialogVisible.value = true
}
function openEdit(row) { isEdit.value = true; Object.assign(form, row); dialogVisible.value = true }

async function handleSave() {
  await formRef.value.validate()
  saving.value = true
  const stored = JSON.parse(localStorage.getItem('buildings_data') || 'null') || [...SEED]
  if (isEdit.value) {
    const idx = stored.findIndex(b => b.id === form.id)
    if (idx >= 0) stored[idx] = { ...form }
  } else {
    stored.push({ ...form, id: Date.now() })
  }
  localStorage.setItem('buildings_data', JSON.stringify(stored))
  ElMessage.success('保存成功'); dialogVisible.value = false; saving.value = false; fetchData()
}

async function handleDelete(row) {
  await ElMessageBox.confirm(`确定删除建筑「${row.name || row.building_id}」？`, '确认', { type: 'warning' })
  const stored = JSON.parse(localStorage.getItem('buildings_data') || 'null') || [...SEED]
  localStorage.setItem('buildings_data', JSON.stringify(stored.filter(b => b.id !== row.id)))
  ElMessage.success('删除成功'); fetchData()
}

function handleUpload(file) {
  const reader = new FileReader()
  reader.onload = (e) => {
    try {
      const json = JSON.parse(e.target.result)
      const features = json.features || (Array.isArray(json) ? json : [json])
      const imported = features.map((f, i) => ({
        id: Date.now() + i,
        building_id: f.properties?.building_id || `IMP_${Date.now()}_${i}`,
        name: f.properties?.name || '未命名建筑',
        district: f.properties?.district || '',
        address: f.properties?.address || '',
        lng: f.geometry?.coordinates?.[0] || 0,
        lat: f.geometry?.coordinates?.[1] || 0,
        base_elevation: f.properties?.base_elevation || 0,
        height: f.properties?.height || 20,
        data_source: '文件导入',
      }))
      const stored = JSON.parse(localStorage.getItem('buildings_data') || 'null') || [...SEED]
      localStorage.setItem('buildings_data', JSON.stringify([...stored, ...imported]))
      ElMessage.success(`成功导入 ${imported.length} 条建筑数据`); fetchData()
    } catch { ElMessage.error('文件解析失败，请检查格式') }
  }
  reader.readAsText(file)
  return false
}

onMounted(fetchData)
</script>
<style scoped>
.stat-card { text-align: center; }
.stat-label { font-size: 13px; color: #6b7280; margin-bottom: 4px; }
.stat-value { font-size: 24px; font-weight: 700; }
.pagination-row { display: flex; justify-content: flex-end; margin-top: 16px; }
</style>
