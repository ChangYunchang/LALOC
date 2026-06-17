<!--
  区域密度统计（7.1.3）— 城市运行统计
  功能：用 ECharts 图表统计低空飞行密度数据，包括：
    - 高密度空域排行（柱状图）
    - 高频航线统计（横向柱状图）
    - 各时段过境密度趋势（折线图）
  数据：模拟广州低空物流场景的统计数据，可按时段筛选。
-->
<template>
  <div class="density-stats-page">
    <!-- 顶部筛选栏 -->
    <div class="filter-bar">
      <div class="filter-group">
        <span class="filter-label">统计时段：</span>
        <el-radio-group v-model="selectedPeriod" size="small" @change="refreshCharts">
          <el-radio-button value="all">全天</el-radio-button>
          <el-radio-button value="morning">早高峰</el-radio-button>
          <el-radio-button value="noon">午间</el-radio-button>
          <el-radio-button value="evening">晚高峰</el-radio-button>
        </el-radio-group>
      </div>
      <div class="filter-group">
        <span class="filter-label">统计维度：</span>
        <el-select v-model="topN" size="small" style="width:100px" @change="refreshCharts">
          <el-option label="Top 5" :value="5" />
          <el-option label="Top 8" :value="8" />
          <el-option label="全部" :value="20" />
        </el-select>
      </div>
      <div class="summary-chips">
        <span class="chip">总航次：<strong>{{ summary.totalFlights }}</strong></span>
        <span class="chip">高密度区：<strong>{{ summary.highDensityZones }}</strong></span>
        <span class="chip">最高密度：<strong>{{ summary.maxDensity }}次/时</strong></span>
        <span class="chip danger">告警区域：<strong>{{ summary.alertZones }}</strong></span>
      </div>
    </div>

    <!-- 图表区域 3列布局 -->
    <div class="charts-grid">
      <!-- 图1：高密度空域排行 -->
      <div class="chart-card">
        <div class="card-header">
          <span class="card-title">高密度空域排行</span>
          <span class="card-sub">按过境次数（次/时）</span>
        </div>
        <div ref="chartBarRef" class="chart-body"></div>
      </div>

      <!-- 图2：高频航线统计 -->
      <div class="chart-card">
        <div class="card-header">
          <span class="card-title">高频航线统计</span>
          <span class="card-sub">按日均飞行次数</span>
        </div>
        <div ref="chartRouteRef" class="chart-body"></div>
      </div>

      <!-- 图3：全天密度趋势 -->
      <div class="chart-card chart-wide">
        <div class="card-header">
          <span class="card-title">各时段过境密度趋势</span>
          <span class="card-sub">24小时密度曲线（次/时）</span>
        </div>
        <div ref="chartTrendRef" class="chart-body"></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'

const selectedPeriod = ref('all')
const topN = ref(8)

const chartBarRef = ref(null), chartRouteRef = ref(null), chartTrendRef = ref(null)
let chartBar = null, chartRoute = null, chartTrend = null

// ── 模拟统计数据 ─────────────────────────────────────
const AIRSPACE_DATA = [
  { name: '天河中心枢纽', count: { all: 68, morning: 85, noon: 42, evening: 91 } },
  { name: '白云东路交汇', count: { all: 54, morning: 72, noon: 38, evening: 76 } },
  { name: '荔湾航路交叉', count: { all: 41, morning: 55, noon: 28, evening: 60 } },
  { name: '番禺物流节点', count: { all: 37, morning: 48, noon: 30, evening: 52 } },
  { name: '黄埔东部走廊', count: { all: 29, morning: 38, noon: 22, evening: 44 } },
  { name: '越秀纵向通道', count: { all: 25, morning: 32, noon: 18, evening: 38 } },
  { name: '南沙新区起降', count: { all: 18, morning: 22, noon: 14, evening: 26 } },
  { name: '海珠低密区',   count: { all: 12, morning: 16, noon: 10, evening: 18 } },
]

const ROUTE_DATA = [
  { name: '天河→番禺干线', count: { all: 142, morning: 38, noon: 24, evening: 46 } },
  { name: '白云→荔湾横线', count: { all: 118, morning: 32, noon: 20, evening: 38 } },
  { name: '黄埔→天河东线', count: { all: 96, morning: 28, noon: 16, evening: 32 } },
  { name: '南沙→越秀纵线', count: { all: 84, morning: 24, noon: 14, evening: 28 } },
  { name: '番禺→南沙环线', count: { all: 72, morning: 20, noon: 12, evening: 24 } },
  { name: '荔湾→海珠短线', count: { all: 58, morning: 16, noon: 10, evening: 18 } },
  { name: '天河内部环路',   count: { all: 45, morning: 12, noon: 8, evening: 14 } },
  { name: '黄埔工业支线',   count: { all: 32, morning: 10, noon: 6, evening: 10 } },
]

// 24小时密度趋势（每小时一个值）
const TREND_DATA = {
  hours: Array.from({ length: 24 }, (_, i) => `${String(i).padStart(2, '0')}:00`),
  all:     [2,1,1,1,2,5,12,28,45,38,26,18,16,14,22,30,35,48,55,42,28,18,8,4],
  morning: [0,0,0,0,0,2,8,22,38,32,22,14,12,10,18,24,28,38,42,32,22,14,6,2],
  noon:    [1,1,0,0,1,2,5,12,18,15,10,8,8,7,10,14,16,22,26,20,14,8,4,2],
  evening: [2,1,1,1,2,5,14,32,52,44,30,20,18,16,26,36,42,58,68,52,34,22,10,5],
}

const summary = computed(() => {
  const p = selectedPeriod.value
  const counts = AIRSPACE_DATA.map(d => d.count[p])
  return {
    totalFlights: ROUTE_DATA.reduce((s, d) => s + d.count[p], 0),
    highDensityZones: counts.filter(c => c >= 40).length,
    maxDensity: Math.max(...counts),
    alertZones: counts.filter(c => c >= 60).length,
  }
})

function getAirspaceChartData() {
  const p = selectedPeriod.value
  const sorted = [...AIRSPACE_DATA].sort((a, b) => b.count[p] - a.count[p]).slice(0, topN.value)
  return { names: sorted.map(d => d.name), values: sorted.map(d => d.count[p]) }
}

function getRouteChartData() {
  const p = selectedPeriod.value
  const sorted = [...ROUTE_DATA].sort((a, b) => b.count[p] - a.count[p]).slice(0, topN.value)
  return { names: sorted.map(d => d.name), values: sorted.map(d => d.count[p]) }
}

function renderBarChart() {
  if (!chartBar) chartBar = echarts.init(chartBarRef.value)
  const { names, values } = getAirspaceChartData()
  const maxVal = Math.max(...values)
  chartBar.setOption({
    tooltip: { trigger: 'axis', formatter: '{b}: {c} 次/时' },
    grid: { left: 16, right: 16, top: 24, bottom: 24, containLabel: true },
    xAxis: { type: 'category', data: names, axisLabel: { fontSize: 11, rotate: 15, color: '#6b7280' }, axisLine: { lineStyle: { color: '#e5e7eb' } } },
    yAxis: { type: 'value', name: '次/时', nameTextStyle: { fontSize: 11, color: '#9ca3af' }, axisLine: { show: false }, splitLine: { lineStyle: { color: '#f3f4f6' } } },
    series: [{
      type: 'bar', data: values, barMaxWidth: 40,
      itemStyle: { color: (params) => {
        const v = params.value
        if (v >= maxVal * 0.8) return '#dc2626'
        if (v >= maxVal * 0.5) return '#f59e0b'
        return '#3b82f6'
      }, borderRadius: [4, 4, 0, 0] },
      label: { show: true, position: 'top', fontSize: 11, color: '#374151' },
    }],
  }, true)
}

function renderRouteChart() {
  if (!chartRoute) chartRoute = echarts.init(chartRouteRef.value)
  const { names, values } = getRouteChartData()
  chartRoute.setOption({
    tooltip: { trigger: 'axis', formatter: '{b}: {c} 次/日' },
    grid: { left: 12, right: 60, top: 16, bottom: 16, containLabel: true },
    xAxis: { type: 'value', axisLabel: { fontSize: 11, color: '#6b7280' }, axisLine: { show: false }, splitLine: { lineStyle: { color: '#f3f4f6' } } },
    yAxis: { type: 'category', data: names, axisLabel: { fontSize: 11, color: '#6b7280', width: 100, overflow: 'truncate' }, axisLine: { lineStyle: { color: '#e5e7eb' } } },
    series: [{
      type: 'bar', data: values, barMaxWidth: 24,
      itemStyle: { color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [{ offset: 0, color: '#818cf8' }, { offset: 1, color: '#3b82f6' }]), borderRadius: [0, 4, 4, 0] },
      label: { show: true, position: 'right', fontSize: 11, color: '#374151' },
    }],
  }, true)
}

function renderTrendChart() {
  if (!chartTrend) chartTrend = echarts.init(chartTrendRef.value)
  const p = selectedPeriod.value
  chartTrend.setOption({
    tooltip: { trigger: 'axis', formatter: (params) => `${params[0].axisValue}<br/>${params[0].seriesName}: ${params[0].value} 次/时` },
    legend: { data: ['过境密度'], top: 0, textStyle: { fontSize: 11, color: '#6b7280' } },
    grid: { left: 16, right: 16, top: 28, bottom: 8, containLabel: true },
    xAxis: { type: 'category', data: TREND_DATA.hours, axisLabel: { fontSize: 10, color: '#9ca3af', interval: 2 }, axisLine: { lineStyle: { color: '#e5e7eb' } }, boundaryGap: false },
    yAxis: { type: 'value', name: '次/时', nameTextStyle: { fontSize: 11 }, axisLine: { show: false }, splitLine: { lineStyle: { color: '#f3f4f6' } } },
    visualMap: { show: false, min: 0, max: 70, inRange: { color: ['#3b82f6', '#f59e0b', '#dc2626'] } },
    series: [{
      name: '过境密度', type: 'line', data: TREND_DATA[p],
      smooth: true, symbol: 'circle', symbolSize: 4,
      areaStyle: { opacity: 0.2, color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: '#f59e0b' }, { offset: 1, color: 'rgba(59,130,246,0)' }]) },
      lineStyle: { width: 2 },
      markPoint: {
        data: [
          { type: 'max', name: '最大值', label: { fontSize: 11 } },
        ],
      },
      markLine: {
        data: [{ type: 'average', name: '均值', lineStyle: { color: '#9ca3af', type: 'dashed' } }],
        label: { formatter: '均值:{c}', fontSize: 11 },
      },
    }],
  }, true)
}

function refreshCharts() {
  nextTick(() => { renderBarChart(); renderRouteChart(); renderTrendChart() })
}

function handleResize() {
  chartBar?.resize(); chartRoute?.resize(); chartTrend?.resize()
}

onMounted(() => {
  nextTick(() => { renderBarChart(); renderRouteChart(); renderTrendChart() })
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  chartBar?.dispose(); chartRoute?.dispose(); chartTrend?.dispose()
})
</script>

<style scoped>
.density-stats-page { display: flex; flex-direction: column; height: 100%; overflow: hidden; background: #f9fafb; }
.filter-bar {
  display: flex; align-items: center; gap: 20px; flex-wrap: wrap;
  padding: 10px 16px; background: #fff; border-bottom: 1px solid #e5e7eb; flex-shrink: 0;
}
.filter-group { display: flex; align-items: center; gap: 8px; }
.filter-label { font-size: 13px; color: #374151; white-space: nowrap; }
.summary-chips { display: flex; gap: 12px; margin-left: auto; flex-wrap: wrap; }
.chip {
  font-size: 12px; color: #6b7280; background: #f3f4f6;
  padding: 3px 10px; border-radius: 12px;
}
.chip strong { color: #1e40af; }
.chip.danger strong { color: #dc2626; }

.charts-grid {
  flex: 1; display: grid;
  grid-template-columns: 1fr 1fr;
  grid-template-rows: 1fr 1fr;
  gap: 12px; padding: 12px; overflow: hidden;
}
.chart-card {
  background: #fff; border-radius: 10px; box-shadow: 0 1px 4px rgba(0,0,0,0.06);
  display: flex; flex-direction: column; overflow: hidden;
}
.chart-wide { grid-column: 1 / -1; }
.card-header {
  display: flex; align-items: baseline; gap: 8px;
  padding: 10px 14px 0; flex-shrink: 0;
}
.card-title { font-size: 13px; font-weight: 600; color: #111827; }
.card-sub { font-size: 11px; color: #9ca3af; }
.chart-body { flex: 1; min-height: 0; }
</style>
