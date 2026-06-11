<!--
  2.2 空域空间查询
  支持点位约束查询和范围约束查询
-->
<template>
  <PageLayout title="空域空间查询" subtitle="输入位置或范围，查询相关空域限制规则">

    <el-tabs v-model="queryType">
      <!-- 点位查询 -->
      <el-tab-pane label="点位约束查询" name="point">
        <el-card class="query-card">
          <el-form inline>
            <el-form-item label="经度">
              <el-input-number v-model="pointLng" :precision="6" :step="0.001" placeholder="经度" style="width:160px" />
            </el-form-item>
            <el-form-item label="纬度">
              <el-input-number v-model="pointLat" :precision="6" :step="0.001" placeholder="纬度" style="width:160px" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="queryPoint" :loading="loading">查询</el-button>
              <el-button @click="useGZ">使用广州中心点</el-button>
            </el-form-item>
          </el-form>

          <div v-if="pointResult" class="result-block">
            <el-alert
              :title="pointResult.flyable ? '✅ 该位置可飞行' : '❌ 该位置存在飞行限制'"
              :type="pointResult.flyable ? 'success' : 'error'"
              :closable="false"
              style="margin-bottom:16px"
            />

            <div v-if="pointResult.no_fly_zones.length" class="section">
              <div class="section-title">禁飞区（{{ pointResult.no_fly_zones.length }}）</div>
              <el-tag v-for="z in pointResult.no_fly_zones" :key="z.id" type="danger" style="margin:4px">
                {{ z.name }}
              </el-tag>
            </div>
            <div v-if="pointResult.height_limit_zones.length" class="section">
              <div class="section-title">限高区（{{ pointResult.height_limit_zones.length }}）</div>
              <div v-for="z in pointResult.height_limit_zones" :key="z.id" class="zone-item">
                <el-tag type="warning">{{ z.name }}</el-tag>
                <span class="zone-detail">最大飞行高度 {{ z.max_altitude }}m</span>
              </div>
            </div>
            <div v-if="pointResult.max_altitude" class="section">
              <el-descriptions :column="2" border size="small">
                <el-descriptions-item label="综合最大飞行高度">{{ pointResult.max_altitude }}m</el-descriptions-item>
              </el-descriptions>
            </div>
          </div>
        </el-card>
      </el-tab-pane>

      <!-- 范围查询 -->
      <el-tab-pane label="范围约束查询" name="range">
        <el-card class="query-card">
          <el-form inline>
            <el-form-item label="最小经度">
              <el-input-number v-model="range.minLng" :precision="4" style="width:140px" />
            </el-form-item>
            <el-form-item label="最大经度">
              <el-input-number v-model="range.maxLng" :precision="4" style="width:140px" />
            </el-form-item>
            <el-form-item label="最小纬度">
              <el-input-number v-model="range.minLat" :precision="4" style="width:140px" />
            </el-form-item>
            <el-form-item label="最大纬度">
              <el-input-number v-model="range.maxLat" :precision="4" style="width:140px" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="queryRange" :loading="loading">查询范围</el-button>
              <el-button @click="useGZRange">广州城区范围</el-button>
            </el-form-item>
          </el-form>

          <div v-if="rangeResult" class="result-block">
            <el-alert
              :title="`范围内共有 ${rangeResult.total_constraints} 项空域限制`"
              :type="rangeResult.total_constraints > 0 ? 'warning' : 'success'"
              :closable="false" style="margin-bottom:16px"
            />
            <el-row :gutter="16">
              <el-col :span="12">
                <div class="section-title">禁飞区（{{ rangeResult.no_fly_zones.length }}）</div>
                <el-table :data="rangeResult.no_fly_zones" size="small" border>
                  <el-table-column prop="name" label="名称" />
                  <el-table-column prop="reason" label="原因" show-overflow-tooltip />
                </el-table>
              </el-col>
              <el-col :span="12">
                <div class="section-title">限高区（{{ rangeResult.height_limit_zones.length }}）</div>
                <el-table :data="rangeResult.height_limit_zones" size="small" border>
                  <el-table-column prop="name" label="名称" />
                  <el-table-column prop="max_altitude" label="限高(m)" width="80" />
                </el-table>
              </el-col>
            </el-row>
          </div>
        </el-card>
      </el-tab-pane>
    </el-tabs>
  </PageLayout>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'
import PageLayout from '@/components/PageLayout.vue'

const queryType = ref('point')
const loading = ref(false)
const pointLng = ref(113.2644)
const pointLat = ref(23.1291)
const pointResult = ref(null)
const rangeResult = ref(null)

const range = reactive({ minLng: 113.15, maxLng: 113.40, minLat: 23.05, maxLat: 23.25 })

function useGZ() { pointLng.value = 113.2644; pointLat.value = 23.1291 }
function useGZRange() { Object.assign(range, { minLng: 113.15, maxLng: 113.40, minLat: 23.05, maxLat: 23.25 }) }

async function queryPoint() {
  loading.value = true
  try {
    const { data } = await axios.get('/api/airspace/query/point', {
      params: { lng: pointLng.value, lat: pointLat.value }
    })
    pointResult.value = data
  } catch {
    ElMessage.error('查询失败')
  } finally {
    loading.value = false
  }
}

async function queryRange() {
  loading.value = true
  try {
    const { data } = await axios.get('/api/airspace/query/range', {
      params: { min_lng: range.minLng, max_lng: range.maxLng, min_lat: range.minLat, max_lat: range.maxLat }
    })
    rangeResult.value = data
  } catch {
    ElMessage.error('查询失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.query-card { margin-top: 12px; }
.result-block { margin-top: 20px; }
.section { margin-bottom: 16px; }
.section-title { font-weight: 600; color: var(--text-primary); margin-bottom: 8px; font-size: 13px; }
.zone-item { display: flex; align-items: center; gap: 8px; margin: 4px 0; }
.zone-detail { font-size: 13px; color: var(--text-secondary); }
</style>
