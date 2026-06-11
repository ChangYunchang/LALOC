/**
 * 路由配置
 * 按子系统分组，每个子系统对应多个功能页面
 */
import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    redirect: '/dashboard',
  },
  // 1. 综合态势监控子系统
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: () => import('@/views/Dashboard.vue'),
    meta: { title: '态势大屏', subsystem: '综合态势监控' },
  },
  {
    path: '/enterprise-monitor',
    name: 'EnterpriseMonitor',
    component: () => import('@/views/monitoring/EnterpriseMonitor.vue'),
    meta: { title: '企业运行监管', subsystem: '综合态势监控' },
  },
  // 2. 空域管理子系统
  {
    path: '/airspace/zones',
    name: 'AirspaceZones',
    component: () => import('@/views/airspace/ZoneManagement.vue'),
    meta: { title: '空域规则管理', subsystem: '空域管理' },
  },
  {
    path: '/airspace/query',
    name: 'AirspaceQuery',
    component: () => import('@/views/airspace/SpaceQuery.vue'),
    meta: { title: '空域空间查询', subsystem: '空域管理' },
  },
  {
    path: '/airspace/compliance',
    name: 'AirspaceCompliance',
    component: () => import('@/views/airspace/ComplianceCheck.vue'),
    meta: { title: '航线合规审查', subsystem: '空域管理' },
  },
  {
    path: '/airspace/stats',
    name: 'AirspaceStats',
    component: () => import('@/views/airspace/AirspaceStats.vue'),
    meta: { title: '空域资源统计', subsystem: '空域管理' },
  },
  // 3. 智能航路规划子系统
  {
    path: '/path-planning',
    name: 'PathPlanning',
    component: () => import('@/views/PathPlanning.vue'),
    meta: { title: '路径规划', subsystem: '智能航路规划' },
  },
  {
    path: '/emergency-routing',
    name: 'EmergencyRouting',
    component: () => import('@/views/routing/EmergencyRouting.vue'),
    meta: { title: '应急航路规划', subsystem: '智能航路规划' },
  },
  // 4. 气象保障子系统
  {
    path: '/weather',
    name: 'WeatherDashboard',
    component: () => import('@/views/weather/WeatherDashboard.vue'),
    meta: { title: '气象监测', subsystem: '气象保障' },
  },
  {
    path: '/weather/forecast',
    name: 'WeatherForecast',
    component: () => import('@/views/weather/WeatherForecast.vue'),
    meta: { title: '气象预报查询', subsystem: '气象保障' },
  },
  {
    path: '/weather/alerts',
    name: 'WeatherAlerts',
    component: () => import('@/views/weather/WeatherAlerts.vue'),
    meta: { title: '气象风险预警', subsystem: '气象保障' },
  },
  // 5. 物流运营管理子系统
  {
    path: '/logistics/orders',
    name: 'LogisticsOrders',
    component: () => import('@/views/logistics/OrderManagement.vue'),
    meta: { title: '配送订单管理', subsystem: '物流运营管理' },
  },
  {
    path: '/logistics/tasks',
    name: 'LogisticsTasks',
    component: () => import('@/views/logistics/TaskManagement.vue'),
    meta: { title: '配送任务管理', subsystem: '物流运营管理' },
  },
  {
    path: '/logistics/stations',
    name: 'LogisticsStations',
    component: () => import('@/views/logistics/StationManagement.vue'),
    meta: { title: '配送站管理', subsystem: '物流运营管理' },
  },
  {
    path: '/logistics/drones',
    name: 'LogisticsDrones',
    component: () => import('@/views/logistics/DroneManagement.vue'),
    meta: { title: '无人机资源管理', subsystem: '物流运营管理' },
  },
  {
    path: '/logistics/scheduling',
    name: 'LogisticsScheduling',
    component: () => import('@/views/logistics/TaskScheduling.vue'),
    meta: { title: '无人机任务调度', subsystem: '物流运营管理' },
  },
  // 6. 安全监管子系统
  {
    path: '/safety/conflict',
    name: 'SafetyConflict',
    component: () => import('@/views/safety/ConflictDetection.vue'),
    meta: { title: '航线冲突检测', subsystem: '安全监管' },
  },
  {
    path: '/safety/congestion',
    name: 'SafetyCongestion',
    component: () => import('@/views/safety/CongestionMonitor.vue'),
    meta: { title: '低空拥堵识别', subsystem: '安全监管' },
  },
  {
    path: '/safety/risk-heatmap',
    name: 'SafetyRiskHeatmap',
    component: () => import('@/views/safety/RiskHeatmap.vue'),
    meta: { title: '安全风险热力分析', subsystem: '安全监管' },
  },
  {
    path: '/safety/events',
    name: 'SafetyEvents',
    component: () => import('@/views/safety/EventManagement.vue'),
    meta: { title: '异常事件管理', subsystem: '安全监管' },
  },
  {
    path: '/safety/records',
    name: 'SafetyRecords',
    component: () => import('@/views/safety/SafetyRecords.vue'),
    meta: { title: '安全监管台账', subsystem: '安全监管' },
  },
  // 7. 统计决策子系统
  {
    path: '/statistics/city',
    name: 'StatsCity',
    component: () => import('@/views/statistics/CityStats.vue'),
    meta: { title: '城市运行统计', subsystem: '统计决策' },
  },
  {
    path: '/statistics/enterprise',
    name: 'StatsEnterprise',
    component: () => import('@/views/statistics/EnterpriseAnalysis.vue'),
    meta: { title: '企业运营效率分析', subsystem: '统计决策' },
  },
  {
    path: '/statistics/service',
    name: 'StatsService',
    component: () => import('@/views/statistics/ServiceQuality.vue'),
    meta: { title: '配送服务质量分析', subsystem: '统计决策' },
  },
  {
    path: '/statistics/cost',
    name: 'StatsCost',
    component: () => import('@/views/statistics/CostAnalysis.vue'),
    meta: { title: '能耗成本分析', subsystem: '统计决策' },
  },
  {
    path: '/statistics/layout',
    name: 'StatsLayout',
    component: () => import('@/views/statistics/StationLayout.vue'),
    meta: { title: '配送站布局分析', subsystem: '统计决策' },
  },
  // 8. 数据资源管理子系统
  {
    path: '/data/gis-layers',
    name: 'DataGISLayers',
    component: () => import('@/views/data/GISLayerManagement.vue'),
    meta: { title: 'GIS图层管理', subsystem: '数据资源管理' },
  },
  {
    path: '/data/buildings',
    name: 'DataBuildings',
    component: () => import('@/views/data/BuildingDataManagement.vue'),
    meta: { title: '三维建筑数据管理', subsystem: '数据资源管理' },
  },
  {
    path: '/data/external-sources',
    name: 'DataExternalSources',
    component: () => import('@/views/data/ExternalSourceManagement.vue'),
    meta: { title: '外部数据源管理', subsystem: '数据资源管理' },
  },
  {
    path: '/data/quality-check',
    name: 'DataQualityCheck',
    component: () => import('@/views/data/DataQualityCheck.vue'),
    meta: { title: '数据更新质检', subsystem: '数据资源管理' },
  },
  // 9. 系统管理子系统
  {
    path: '/system/users',
    name: 'SystemUsers',
    component: () => import('@/views/system/UserManagement.vue'),
    meta: { title: '用户管理', subsystem: '系统管理' },
  },
  {
    path: '/system/roles',
    name: 'SystemRoles',
    component: () => import('@/views/system/RoleManagement.vue'),
    meta: { title: '角色权限管理', subsystem: '系统管理' },
  },
  {
    path: '/system/enterprises',
    name: 'SystemEnterprises',
    component: () => import('@/views/system/EnterpriseManagement.vue'),
    meta: { title: '企业信息管理', subsystem: '系统管理' },
  },
  {
    path: '/system/params',
    name: 'SystemParams',
    component: () => import('@/views/system/SystemParams.vue'),
    meta: { title: '系统参数配置', subsystem: '系统管理' },
  },
  {
    path: '/system/logs',
    name: 'SystemLogs',
    component: () => import('@/views/system/AuditLog.vue'),
    meta: { title: '日志审计', subsystem: '系统管理' },
  },
  {
    path: '/system/service-status',
    name: 'SystemServiceStatus',
    component: () => import('@/views/system/ServiceStatus.vue'),
    meta: { title: '服务状态监测', subsystem: '系统管理' },
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
