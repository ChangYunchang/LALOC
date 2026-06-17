/**
 * 路由配置
 * 对应 Structure.md 中的 4 个 GIS 核心子系统：
 *   1. 态势大屏子系统
 *   2. 智能航路规划子系统
 *   3. 无人机安全缓冲区分析子系统
 *   4. 低空密度等值线分析子系统
 */
import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', redirect: '/dashboard' },

  // ── 子系统 1：态势大屏 ──────────────────────────
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: () => import('@/views/Dashboard.vue'),
    meta: { title: '态势大屏', subsystem: '态势大屏' },
  },

  // ── 子系统 2：智能航路规划 ─────────────────────
  {
    path: '/path-planning',
    name: 'PathPlanning',
    component: () => import('@/views/PathPlanning.vue'),
    meta: { title: '智能路径规划', subsystem: '航路规划' },
  },
  {
    path: '/emergency-routing',
    name: 'EmergencyRouting',
    component: () => import('@/views/routing/EmergencyRouting.vue'),
    meta: { title: '应急航路规划', subsystem: '航路规划' },
  },

  // ── 子系统 3：无人机安全缓冲区分析 ─────────────
  {
    path: '/safety-buffer/config',
    name: 'SafetyBufferConfig',
    component: () => import('@/views/safety-buffer/SafetyBufferConfig.vue'),
    meta: { title: '安全范围配置', subsystem: '安全缓冲分析' },
  },
  {
    path: '/safety-buffer/overlap',
    name: 'BufferOverlapAnalysis',
    component: () => import('@/views/safety-buffer/BufferOverlapAnalysis.vue'),
    meta: { title: '缓冲区重叠分析', subsystem: '安全缓冲分析' },
  },

  // ── 子系统 4：安全风险热力分析（6.3）+ 低空拥堵识别（6.2）+ 区域密度统计（7.1.3）
  {
    path: '/density/contour',
    name: 'DensityContour',
    component: () => import('@/views/density/DensityContour.vue'),
    meta: { title: '安全风险热力分析', subsystem: '安全热力分析' },
  },
  {
    path: '/density/hotspot',
    name: 'HotspotAnalysis',
    component: () => import('@/views/density/HotspotAnalysis.vue'),
    meta: { title: '低空拥堵识别', subsystem: '安全热力分析' },
  },
  {
    path: '/density/stats',
    name: 'DensityStats',
    component: () => import('@/views/density/DensityStats.vue'),
    meta: { title: '区域密度统计', subsystem: '安全热力分析' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, from, next) => {
  document.title = `${to.meta.title || '首页'} - 城市低空物流运营中心`
  next()
})

export default router
