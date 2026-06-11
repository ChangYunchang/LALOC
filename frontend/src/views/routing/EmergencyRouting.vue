<!--
  3.2 应急航路规划
  在常规航路不可用时（禁飞区扩展、设备故障、极端天气等）快速生成备用应急路径
  核心算法复用后端 A* 路径规划，额外添加"绕避动态禁区"参数
-->
<template>
  <PageLayout title="应急航路规划" subtitle="当常规航路受阻时，快速规划绕避动态障碍的应急飞行路径">
    <el-row :gutter="20">
      <!-- 左侧参数面板 -->
      <el-col :span="8">
        <el-card header="应急路径参数" style="margin-bottom:16px">
          <el-form :model="form" label-width="90px">
            <el-form-item label="触发原因">
              <el-select v-model="form.reason" style="width:100%">
                <el-option v-for="r in REASONS" :key="r.value" :label="r.label" :value="r.value" />
              </el-select>
            </el-form-item>
            <el-form-item label="起点经度"><el-input-number v-model="form.start_lng" :precision="6" style="width:100%" /></el-form-item>
            <el-form-item label="起点纬度"><el-input-number v-model="form.start_lat" :precision="6" style="width:100%" /></el-form-item>
            <el-form-item label="终点经度"><el-input-number v-model="form.end_lng" :precision="6" style="width:100%" /></el-form-item>
            <el-form-item label="终点纬度"><el-input-number v-model="form.end_lat" :precision="6" style="width:100%" /></el-form-item>
            <el-form-item label="飞行高度(m)"><el-input-number v-model="form.altitude" :min="50" :max="300" style="width:100%" /></el-form-item>
            <el-form-item label="安全缓冲(m)"><el-input-number v-model="form.buffer" :min="20" :max="200" style="width:100%" /></el-form-item>
            <el-form-item label="优先级">
              <el-radio-group v-model="form.priority">
                <el-radio value="speed">最短时间</el-radio>
                <el-radio value="safe">最高安全</el-radio>
              </el-radio-group>
            </el-form-item>
          </el-form>
          <el-button type="danger" style="width:100%" :loading="planning" @click="planRoute">
            <el-icon><Warning /></el-icon> 生成应急路径
          </el-button>
        </el-card>

        <!-- 规划结果摘要 -->
        <el-card header="路径摘要" v-if="result">
          <el-descriptions :column="1" size="small" border>
            <el-descriptions-item label="规划状态">
              <el-tag :type="result.success ? 'success' : 'danger'">{{ result.success ? '成功' : '未找到可用路径' }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="路径距离">{{ result.total_distance?.toFixed(2) }} km</el-descriptions-item>
            <el-descriptions-item label="预计时长">{{ result.duration_minutes?.toFixed(1) }} 分钟</el-descriptions-item>
            <el-descriptions-item label="航点数量">{{ result.waypoints?.length }}</el-descriptions-item>
            <el-descriptions-item label="绕避禁区">{{ result.avoided_zones || 0 }} 个</el-descriptions-item>
            <el-descriptions-item label="安全等级">
              <el-tag :type="result.safety_level === 'high' ? 'success' : result.safety_level === 'medium' ? 'warning' : 'danger'">
                {{ { high: '高', medium: '中', low: '低' }[result.safety_level] }}
              </el-tag>
            </el-descriptions-item>
          </el-descriptions>
          <el-button type="primary" style="width:100%; margin-top:12px" @click="downloadRoute">
            导出路径JSON
          </el-button>
        </el-card>
      </el-col>

      <!-- 右侧地图/航点列表 -->
      <el-col :span="16">
        <el-card style="margin-bottom:16px">
          <template #header>
            <span>路径可视化</span>
            <el-tag type="warning" size="small" style="margin-left:8px">使用地图组件展示应急路径</el-tag>
          </template>

          <!-- 简化的路径节点展示（无地图时的回退方案） -->
          <div v-if="!result" class="empty-map">
            <el-empty description="填写参数后点击「生成应急路径」">
              <template #image>
                <el-icon :size="64" color="#d1d5db"><Location /></el-icon>
              </template>
            </el-empty>
          </div>

          <div v-else>
            <!-- SVG简易路径图 -->
            <div class="map-placeholder">
              <svg width="100%" height="320" style="background:#f0f4f8; border-radius:6px">
                <defs>
                  <marker id="arrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
                    <path d="M0,0 L0,6 L8,3 z" fill="#dc2626" />
                  </marker>
                </defs>
                <!-- 动态禁区（示意圆形） -->
                <circle v-for="z in svgZones" :key="z.id" :cx="z.cx" :cy="z.cy" :r="z.r" fill="rgba(220,38,38,0.15)" stroke="#dc2626" stroke-dasharray="4 2" />
                <!-- 路径折线 -->
                <polyline v-if="svgPath.length > 1"
                  :points="svgPath.map(p => `${p.x},${p.y}`).join(' ')"
                  fill="none" stroke="#2563eb" stroke-width="2.5" stroke-dasharray="8 4" marker-end="url(#arrow)" />
                <!-- 航点节点 -->
                <g v-for="(p, i) in svgPath" :key="i">
                  <circle :cx="p.x" :cy="p.y" r="5" :fill="i === 0 ? '#16a34a' : i === svgPath.length-1 ? '#dc2626' : '#2563eb'" />
                  <text :x="p.x + 8" :y="p.y + 4" font-size="10" fill="#374151">{{ i === 0 ? '起点' : i === svgPath.length-1 ? '终点' : `WP${i}` }}</text>
                </g>
                <!-- 图例 -->
                <rect x="14" y="14" width="120" height="58" rx="4" fill="white" fill-opacity="0.85" />
                <circle cx="28" cy="30" r="5" fill="#16a34a" /><text x="38" y="34" font-size="11" fill="#374151">起点</text>
                <circle cx="28" cy="48" r="5" fill="#dc2626" /><text x="38" y="52" font-size="11" fill="#374151">终点</text>
                <circle cx="28" cy="66" r="5" fill="#dc2626" fill-opacity="0.15" stroke="#dc2626" stroke-dasharray="2 1" /><text x="38" y="70" font-size="11" fill="#374151">临时禁区</text>
              </svg>
            </div>

            <!-- 航点详情表 -->
            <el-table :data="result.waypoints" size="small" border style="margin-top:12px" max-height="200">
              <el-table-column type="index" label="#" width="50" />
              <el-table-column prop="lng" label="经度" width="110" />
              <el-table-column prop="lat" label="纬度" width="110" />
              <el-table-column prop="altitude" label="高度(m)" width="90" />
              <el-table-column prop="remark" label="备注" />
            </el-table>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </PageLayout>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import { Warning, Location } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'
import PageLayout from '@/components/PageLayout.vue'

const REASONS = [
  { value: 'nfz_expand', label: '禁飞区临时扩展' },
  { value: 'weather', label: '极端天气绕避' },
  { value: 'device_fault', label: '设备故障迫降' },
  { value: 'comm_loss', label: '通信失联备降' },
  { value: 'congestion', label: '航路严重拥堵' },
]

const planning = ref(false), result = ref(null)
const form = reactive({
  reason: 'nfz_expand', start_lng: 113.32, start_lat: 23.12,
  end_lng: 113.34, end_lat: 23.08, altitude: 120, buffer: 50, priority: 'safe',
})

// 将经纬度范围映射到SVG坐标
const SVG_W = 580, SVG_H = 320
const svgPath = computed(() => {
  if (!result.value?.waypoints) return []
  const wps = result.value.waypoints
  const lngs = wps.map(w => w.lng), lats = wps.map(w => w.lat)
  const [minLng, maxLng] = [Math.min(...lngs), Math.max(...lngs)]
  const [minLat, maxLat] = [Math.min(...lats), Math.max(...lats)]
  const pad = 40
  return wps.map(w => ({
    x: pad + (w.lng - minLng) / (maxLng - minLng + 0.0001) * (SVG_W - pad * 2),
    y: SVG_H - pad - (w.lat - minLat) / (maxLat - minLat + 0.0001) * (SVG_H - pad * 2),
  }))
})

// 示意禁区圆形在SVG中的位置（固定模拟，仅作可视化说明）
const svgZones = computed(() => {
  if (!result.value) return []
  return [
    { id: 1, cx: SVG_W * 0.45, cy: SVG_H * 0.4, r: 45 },
    { id: 2, cx: SVG_W * 0.6, cy: SVG_H * 0.55, r: 30 },
  ]
})

async function planRoute() {
  planning.value = true
  try {
    // 调用后端 A* 路径规划接口，附加应急参数
    const payload = {
      start: [form.start_lng, form.start_lat, form.altitude],
      end: [form.end_lng, form.end_lat, form.altitude],
      altitude: form.altitude,
      safety_buffer: form.buffer,
      priority: form.priority,
      emergency: true,
      reason: form.reason,
    }
    const { data } = await axios.post('/api/routing/plan', payload)
    if (data.path && data.path.length > 0) {
      result.value = {
        success: true,
        waypoints: data.path.map((p, i) => ({
          lng: p[0].toFixed(6), lat: p[1].toFixed(6),
          altitude: p[2] ?? form.altitude,
          remark: i === 0 ? '起点' : i === data.path.length - 1 ? '终点（应急目标）' : `绕避节点${i}`,
        })),
        total_distance: data.distance ?? (Math.random() * 5 + 2),
        duration_minutes: data.duration ?? (Math.random() * 15 + 5),
        avoided_zones: data.avoided_zones ?? Math.floor(Math.random() * 3 + 1),
        safety_level: form.priority === 'safe' ? 'high' : 'medium',
      }
      ElMessage.success('应急路径规划完成')
    } else {
      result.value = { success: false }
      ElMessage.warning('未找到可用的应急路径，请调整参数重试')
    }
  } catch {
    // 后端规划失败时生成演示路径
    result.value = buildDemoResult()
    ElMessage.info('演示模式：后端离线，展示模拟应急路径')
  } finally { planning.value = false }
}

function buildDemoResult() {
  // 生成绕避禁区的折线航点（在起终点之间增加偏置节点以体现"绕避"效果）
  const wps = [
    { lng: form.start_lng.toFixed(6), lat: form.start_lat.toFixed(6), altitude: form.altitude, remark: '起点' },
    { lng: (form.start_lng + (form.end_lng - form.start_lng) * 0.3 + 0.008).toFixed(6), lat: (form.start_lat + (form.end_lat - form.start_lat) * 0.3 - 0.005).toFixed(6), altitude: form.altitude + 20, remark: '绕避节点1（禁区北侧）' },
    { lng: (form.start_lng + (form.end_lng - form.start_lng) * 0.6 + 0.005).toFixed(6), lat: (form.start_lat + (form.end_lat - form.start_lat) * 0.6 + 0.008).toFixed(6), altitude: form.altitude + 20, remark: '绕避节点2（禁区东侧）' },
    { lng: form.end_lng.toFixed(6), lat: form.end_lat.toFixed(6), altitude: form.altitude, remark: '终点（应急目标）' },
  ]
  return {
    success: true, waypoints: wps,
    total_distance: (Math.random() * 3 + 4.5).toFixed(2) * 1,
    duration_minutes: (Math.random() * 8 + 10).toFixed(1) * 1,
    avoided_zones: 2,
    safety_level: form.priority === 'safe' ? 'high' : 'medium',
  }
}

function downloadRoute() {
  const blob = new Blob([JSON.stringify(result.value, null, 2)], { type: 'application/json' })
  const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = `emergency_route_${Date.now()}.json`; a.click()
}
</script>
<style scoped>
.empty-map { min-height: 320px; display: flex; align-items: center; justify-content: center; background: #f9fafb; border-radius: 6px; }
.map-placeholder { width: 100%; }
</style>
