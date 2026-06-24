<template>
  <div class="app-container">
    <!-- 顶部导航栏 -->
    <header class="app-header">
      <div class="header-left">
        <span class="logo">🚁</span>
        <h1 class="app-title">城市低空物流运营中心</h1>
      </div>

      <nav class="header-nav">
        <!-- 态势监控 -->
        <router-link to="/dashboard" class="nav-link" active-class="active">
          <el-icon><Monitor /></el-icon>
          态势大屏
        </router-link>

        <!-- 安全缓冲分析（单页，直接链接）-->
        <router-link to="/safety-buffer/analysis" class="nav-link" active-class="active">
          <el-icon><Lock /></el-icon>
          安全缓冲分析
        </router-link>

        <!-- 下拉菜单：多子页面的子系统 -->
        <div
          v-for="menu in dropdownMenus"
          :key="menu.label"
          class="nav-dropdown"
          :class="{ active: isMenuActive(menu) }"
          @mouseenter="openMenu(menu.label)"
          @mouseleave="closeMenu"
        >
          <span class="nav-dropdown-trigger">
            <el-icon><component :is="iconMap[menu.icon]" /></el-icon>
            {{ menu.label }}
            <el-icon class="arrow"><ArrowDown /></el-icon>
          </span>
          <div v-if="activeMenu === menu.label" class="dropdown-panel">
            <router-link
              v-for="item in menu.children"
              :key="item.path"
              :to="item.path"
              class="dropdown-item"
              active-class="active"
              @click="closeMenu"
            >
              {{ item.label }}
            </router-link>
          </div>
        </div>
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
import { useRoute } from 'vue-router'
import {
  Monitor, MapLocation, ArrowDown, Lock, TrendCharts,
} from '@element-plus/icons-vue'

const route = useRoute()
const currentTime = ref('')
const activeMenu = ref(null)
let timer = null
let closeTimer = null

const iconMap = { MapLocation, Lock, TrendCharts }

/**
 * 顶部导航下拉菜单配置
 * 严格对应 Structure.md 中的 4 个 GIS 子系统：
 *   1. 态势大屏（直接链接）
 *   2. 智能航路规划（下拉）
 *   3. 无人机安全缓冲区分析（下拉）
 *   4. 低空密度等值线分析（下拉）
 */
const dropdownMenus = [
  {
    label: '航路规划',
    icon: 'MapLocation',
    paths: ['/path-planning', '/emergency-routing'],
    children: [
      { path: '/path-planning', label: '智能路径规划' },
      { path: '/emergency-routing', label: '应急航路规划' },
    ],
  },
  {
    label: '安全热力分析',
    icon: 'TrendCharts',
    paths: ['/density'],
    children: [
      { path: '/density/contour', label: '安全风险热力分析' },
      { path: '/density/hotspot', label: '低空拥堵识别' },
      { path: '/density/stats', label: '区域密度统计' },
    ],
  },
]

function isMenuActive(menu) {
  return menu.paths.some(p => route.path.startsWith(p))
}

function openMenu(label) {
  if (closeTimer) {
    clearTimeout(closeTimer)
    closeTimer = null
  }
  activeMenu.value = label
}

function closeMenu() {
  closeTimer = setTimeout(() => {
    activeMenu.value = null
  }, 150)
}

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
  if (closeTimer) clearTimeout(closeTimer)
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
  padding: 0 16px;
  z-index: 1000;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  flex-shrink: 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.logo {
  font-size: 22px;
}

.app-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  white-space: nowrap;
}

.header-nav {
  display: flex;
  align-items: center;
  gap: 2px;
  margin-left: 24px;
  flex: 1;
  overflow: visible;
}

/* 普通导航链接 */
.nav-link {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 5px 12px;
  border-radius: 6px;
  color: var(--text-secondary);
  text-decoration: none;
  font-size: 13px;
  white-space: nowrap;
  transition: all 0.2s;
  cursor: pointer;
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

/* 下拉菜单容器 */
.nav-dropdown {
  position: relative;
}

.nav-dropdown-trigger {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 5px 12px;
  border-radius: 6px;
  color: var(--text-secondary);
  font-size: 13px;
  white-space: nowrap;
  cursor: pointer;
  transition: all 0.2s;
  user-select: none;
}

.nav-dropdown-trigger:hover,
.nav-dropdown.active .nav-dropdown-trigger {
  color: var(--accent-blue);
  background: #eff6ff;
}

.nav-dropdown.active .nav-dropdown-trigger {
  font-weight: 500;
}

.arrow {
  font-size: 11px;
  transition: transform 0.2s;
}

/* 下拉面板 */
.dropdown-panel {
  position: absolute;
  top: calc(100% + 6px);
  left: 0;
  min-width: 140px;
  background: #ffffff;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  padding: 4px 0;
  z-index: 2000;
}

.dropdown-item {
  display: block;
  padding: 8px 16px;
  color: var(--text-secondary);
  text-decoration: none;
  font-size: 13px;
  white-space: nowrap;
  transition: all 0.15s;
}

.dropdown-item:hover {
  color: var(--text-primary);
  background: #f9fafb;
}

.dropdown-item.active {
  color: var(--accent-blue);
  background: #eff6ff;
  font-weight: 500;
}

.header-right {
  margin-left: auto;
  flex-shrink: 0;
}

.current-time {
  font-size: 13px;
  color: var(--text-secondary);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.app-main {
  flex: 1;
  overflow: hidden;
}
</style>
