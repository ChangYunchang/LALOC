<template>
  <div class="timeline-container">
    <div class="timeline-header">
      <el-button
        :type="playing ? 'danger' : 'primary'"
        size="small"
        @click="togglePlay"
      >
        {{ playing ? '⏸ 暂停' : '▶ 播放' }}
      </el-button>
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
      <span
        v-for="(time, index) in displayTicks"
        :key="index"
        class="tick-label"
      >
        {{ time }}
      </span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onUnmounted } from 'vue'

const emit = defineEmits(['time-change'])

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
  return timePoints.value
    .filter((_, i) => i % 4 === 0)
    .map((t) => t.label)
})

const currentIndex = ref(0)
const playing = ref(false)
let playTimer = null

const currentTimeLabel = computed(() => {
  return timePoints.value[currentIndex.value]?.label || '06:00'
})

const timeRange = computed(() => {
  const first = timePoints.value[0]?.label || ''
  const last = timePoints.value[timePoints.value.length - 1]?.label || ''
  return `${first} - ${last}`
})

function onTimeChange() {
  const timePoint = timePoints.value[currentIndex.value]
  emit('time-change', timePoint)
}

function togglePlay() {
  playing.value = !playing.value
  if (playing.value) {
    playTimer = setInterval(() => {
      if (currentIndex.value < timePoints.value.length - 1) {
        currentIndex.value++
        onTimeChange()
      } else {
        currentIndex.value = 0
        playing.value = false
        clearInterval(playTimer)
      }
    }, 500)
  } else {
    if (playTimer) clearInterval(playTimer)
  }
}

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
</style>
