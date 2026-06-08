<template>
  <div class="timeline-container">
    <!-- 普通时间轴模式（无选中航线） -->
    <template v-if="!selectedRoute">
      <div class="timeline-header">
        <span class="timeline-current">{{ currentTimeLabel }}</span>
        <span class="timeline-range">{{ timeRange }}</span>
      </div>
      <div class="timeline-slider">
        <el-slider
          v-model="currentIndex"
          :min="0"
          :max="timePoints.length - 1"
          :show-tooltip="false"
          @input="onTimeChange"
        />
      </div>
      <div class="timeline-ticks">
        <span v-for="(time, index) in displayTicks" :key="index" class="tick-label">
          {{ time }}
        </span>
      </div>
    </template>

    <!-- 航线回放模式 -->
    <template v-else>
      <div class="timeline-header">
        <div class="playback-controls">
          <el-button
            :type="playing ? 'danger' : 'primary'"
            size="small"
            circle
            @click="togglePlay"
          >
            <span v-if="playing">⏸</span>
            <span v-else>▶</span>
          </el-button>
          <el-button size="small" circle @click="restartPlayback">
            ⏮
          </el-button>
          <el-dropdown trigger="click" @command="setSpeed">
            <el-button size="small" class="speed-btn">
              {{ playbackSpeed }}x
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item :command="0.5">0.5x</el-dropdown-item>
                <el-dropdown-item :command="1">1x</el-dropdown-item>
                <el-dropdown-item :command="2">2x</el-dropdown-item>
                <el-dropdown-item :command="5">5x</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
        <span class="route-label">{{ selectedRoute.name }}</span>
        <span class="timeline-range">{{ routeTimeRange }}</span>
      </div>
      <div class="timeline-slider">
        <el-slider
          v-model="progressPercent"
          :min="0"
          :max="1000"
          :show-tooltip="false"
          @input="onProgressDrag"
        />
      </div>
      <div class="timeline-ticks">
        <span class="tick-label">{{ routeStartTime }}</span>
        <span class="tick-label tick-center">
          已飞行 {{ elapsedTime }}
        </span>
        <span class="tick-label">{{ routeEndTime }}</span>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onUnmounted, watch } from 'vue'

const props = defineProps({
  selectedRoute: { type: Object, default: null },
  mapRef: { type: Object, default: null },
})

const emit = defineEmits(['time-change'])

// ── 普通时间轴 ──────────────────────────────────

const timePoints = computed(() => {
  const points = []
  for (let hour = 6; hour <= 22; hour++) {
    for (let min = 0; min < 60; min += 30) {
      points.push({
        label: `${hour.toString().padStart(2, '0')}:${min.toString().padStart(2, '0')}`,
        hour,
        minute: min,
        timestamp: new Date().setHours(hour, min, 0, 0),
      })
    }
  }
  return points
})

const displayTicks = computed(() => {
  return timePoints.value.filter((_, i) => i % 4 === 0).map((t) => t.label)
})

const currentIndex = ref(0)
const currentTimeLabel = computed(() => timePoints.value[currentIndex.value]?.label || '06:00')
const timeRange = computed(() => {
  const first = timePoints.value[0]?.label || ''
  const last = timePoints.value[timePoints.value.length - 1]?.label || ''
  return `${first} - ${last}`
})

function onTimeChange() {
  const timePoint = timePoints.value[currentIndex.value]
  emit('time-change', timePoint)
}

// ── 航线回放 ──────────────────────────────────

const progressPercent = ref(0) // 0~1000
const playing = ref(false)
const playbackSpeed = ref(1)
let playTimer = null
let manualDragging = false

const routeStartTime = computed(() => {
  if (!props.selectedRoute) return ''
  const now = new Date()
  return `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`
})

const routeEndTime = computed(() => {
  if (!props.selectedRoute) return ''
  const est = props.selectedRoute.estimated_time || 0
  const mins = Math.ceil(est / 60)
  const now = new Date()
  const end = new Date(now.getTime() + mins * 60000)
  return `${end.getHours().toString().padStart(2, '0')}:${end.getMinutes().toString().padStart(2, '0')}`
})

const routeTimeRange = computed(() => {
  if (!props.selectedRoute) return ''
  const est = props.selectedRoute.estimated_time || 0
  return `预计 ${Math.ceil(est / 60)} 分钟`
})

const elapsedTime = computed(() => {
  if (!props.selectedRoute) return '0:00'
  const est = props.selectedRoute.estimated_time || 0
  const elapsed = (progressPercent.value / 1000) * est
  const mins = Math.floor(elapsed / 60)
  const secs = Math.floor(elapsed % 60)
  return `${mins}:${secs.toString().padStart(2, '0')}`
})

function togglePlay() {
  if (playing.value) {
    pausePlayback()
  } else {
    startPlayback()
  }
}

function startPlayback() {
  playing.value = true

  // 暂停地图上的循环动画
  if (props.mapRef && props.selectedRoute) {
    props.mapRef.pauseDrone(props.selectedRoute.id)
  }

  playTimer = setInterval(() => {
    if (manualDragging) return

    const step = playbackSpeed.value * 2
    progressPercent.value = Math.min(1000, progressPercent.value + step)

    // 更新地图无人机位置
    updateDroneFromProgress()

    if (progressPercent.value >= 1000) {
      pausePlayback()
    }
  }, 50)
}

function pausePlayback() {
  playing.value = false
  if (playTimer) {
    clearInterval(playTimer)
    playTimer = null
  }
}

function restartPlayback() {
  progressPercent.value = 0
  updateDroneFromProgress()
  if (!playing.value) {
    startPlayback()
  }
}

function setSpeed(speed) {
  playbackSpeed.value = speed
}

function onProgressDrag() {
  manualDragging = true
  updateDroneFromProgress()
  // 拖拽结束后恢复
  setTimeout(() => { manualDragging = false }, 100)
}

function updateDroneFromProgress() {
  if (!props.mapRef || !props.selectedRoute) return
  const progress = progressPercent.value / 1000
  props.mapRef.setDronePosition(props.selectedRoute.id, progress)
}

// 当选中航线变化时，重置回放状态
watch(() => props.selectedRoute, (newRoute, oldRoute) => {
  pausePlayback()
  progressPercent.value = 0

  // 如果取消选中，恢复之前的航线循环动画
  if (oldRoute && props.mapRef) {
    props.mapRef.resumeDrone(oldRoute.id)
  }
})

onUnmounted(() => {
  if (playTimer) clearInterval(playTimer)
})
</script>

<style scoped>
.timeline-container {
  background: rgba(255, 255, 255, 0.95);
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 12px 20px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  backdrop-filter: blur(8px);
}

.timeline-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.playback-controls {
  display: flex;
  align-items: center;
  gap: 6px;
}

.speed-btn {
  min-width: 42px;
  font-size: 12px;
}

.route-label {
  font-size: 14px;
  font-weight: 600;
  color: #1f2937;
}

.timeline-current {
  font-size: 18px;
  font-weight: 700;
  color: #1f2937;
  font-variant-numeric: tabular-nums;
}

.timeline-range {
  margin-left: auto;
  font-size: 12px;
  color: #9ca3af;
}

.timeline-ticks {
  display: flex;
  justify-content: space-between;
}

.tick-label {
  font-size: 10px;
  color: #9ca3af;
}

.tick-center {
  font-size: 11px;
  color: #2563eb;
  font-weight: 500;
}
</style>
