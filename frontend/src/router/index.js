/**
 * 路由配置
 */
import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    redirect: '/dashboard',
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: () => import('@/views/Dashboard.vue'),
    meta: { title: '态势大屏' },
  },
  {
    path: '/path-planning',
    name: 'PathPlanning',
    component: () => import('@/views/PathPlanning.vue'),
    meta: { title: '路径规划' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// 路由守卫 - 设置页面标题
router.beforeEach((to, from, next) => {
  document.title = `${to.meta.title || '首页'} - 城市低空物流运营中心`
  next()
})

export default router
