<template>
  <div class="app-container">
    <!-- 顶部导航栏 -->
    <header class="app-header">
      <div class="header-left">
        <span class="logo">🚁</span>
        <h1 class="app-title">城市低空物流运营中心</h1>
      </div>
      <nav class="header-nav">
        <router-link to="/dashboard" class="nav-link" active-class="active">
          <el-icon><Monitor /></el-icon>
          态势大屏
        </router-link>
        <router-link to="/path-planning" class="nav-link" active-class="active">
          <el-icon><MapLocation /></el-icon>
          路径规划
        </router-link>
      </nav>
      <div class="header-right">
        <span class="current-time">{{ currentTime }}</span>
      </div>
    </header>

    <!-- 主内容区 -->
    <main class="app-main">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { Monitor, MapLocation } from '@element-plus/icons-vue'

const currentTime = ref('')
let timer = null

function updateTime() {
  const now = new Date()
  currentTime.value = now.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

onMounted(() => {
  updateTime()
  timer = setInterval(updateTime, 1000)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<style scoped>
.app-container {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--bg-primary);
}

.app-header {
  height: 52px;
  background: #ffffff;
  border-bottom: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  padding: 0 24px;
  z-index: 1000;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.logo {
  font-size: 22px;
}

.app-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

.header-nav {
  display: flex;
  gap: 4px;
  margin-left: 48px;
}

.nav-link {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 16px;
  border-radius: 6px;
  color: var(--text-secondary);
  text-decoration: none;
  font-size: 14px;
  transition: all 0.2s;
}

.nav-link:hover {
  color: var(--text-primary);
  background: #f3f4f6;
}

.nav-link.active {
  color: var(--accent-blue);
  background: #eff6ff;
  font-weight: 500;
}

.header-right {
  margin-left: auto;
}

.current-time {
  font-size: 13px;
  color: var(--text-secondary);
  font-variant-numeric: tabular-nums;
}

.app-main {
  flex: 1;
  overflow: hidden;
}
</style>
