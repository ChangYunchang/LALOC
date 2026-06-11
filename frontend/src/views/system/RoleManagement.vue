<!--
  9.2 角色权限管理
-->
<template>
  <PageLayout title="角色权限管理" subtitle="定义平台用户角色及其功能菜单访问权限">
    <el-row :gutter="20">
      <el-col :span="8">
        <el-card header="角色列表">
          <el-menu v-model:default-active="activeRole" @select="selectRole">
            <el-menu-item v-for="r in roles" :key="r.key" :index="r.key">
              <el-tag :type="r.type" size="small" style="margin-right:8px">{{ r.label }}</el-tag>
              {{ r.desc }}
            </el-menu-item>
          </el-menu>
        </el-card>
      </el-col>
      <el-col :span="16">
        <el-card :header="`「${currentRole?.label}」可访问模块`">
          <el-tree
            :data="menuTree" :props="{ children: 'children', label: 'label' }"
            show-checkbox node-key="key"
            :default-checked-keys="currentRole?.menus || []"
            @check="handleCheck"
            style="max-height:480px; overflow-y:auto"
          />
          <div style="margin-top:16px">
            <el-button type="primary" @click="savePermissions">保存权限配置</el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </PageLayout>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import PageLayout from '@/components/PageLayout.vue'

const activeRole = ref('admin')
const roles = [
  { key: 'admin', label: '管理员', type: 'danger', desc: '系统最高权限', menus: ['all'] },
  { key: 'supervisor', label: '监管员', type: 'warning', desc: '监管和查看权限', menus: ['monitor', 'airspace', 'safety', 'statistics'] },
  { key: 'operator', label: '操作员', type: 'primary', desc: '日常操作权限', menus: ['monitor', 'logistics', 'weather'] },
  { key: 'enterprise', label: '企业用户', type: 'success', desc: '企业业务权限', menus: ['logistics_orders', 'logistics_tasks'] },
]
const currentRole = ref(roles[0])
const menuTree = [
  { key: 'monitor', label: '综合态势监控', children: [{ key: 'dashboard', label: '态势大屏' }, { key: 'enterprise_monitor', label: '企业运行监管' }] },
  { key: 'airspace', label: '空域管理', children: [{ key: 'airspace_zones', label: '空域规则管理' }, { key: 'airspace_query', label: '空域空间查询' }, { key: 'airspace_compliance', label: '航线合规审查' }] },
  { key: 'routing', label: '航路规划', children: [{ key: 'path_planning', label: '路径规划' }, { key: 'emergency_routing', label: '应急航路' }] },
  { key: 'weather', label: '气象保障', children: [{ key: 'weather_monitor', label: '实时气象' }, { key: 'weather_forecast', label: '气象预报' }] },
  { key: 'logistics', label: '物流运营', children: [{ key: 'logistics_orders', label: '配送订单' }, { key: 'logistics_tasks', label: '配送任务' }, { key: 'logistics_stations', label: '配送站管理' }, { key: 'logistics_drones', label: '无人机管理' }] },
  { key: 'safety', label: '安全监管', children: [{ key: 'safety_conflict', label: '冲突检测' }, { key: 'safety_events', label: '异常事件' }, { key: 'safety_records', label: '监管台账' }] },
  { key: 'statistics', label: '统计决策', children: [{ key: 'stats_city', label: '城市运行统计' }, { key: 'stats_enterprise', label: '企业效率分析' }] },
  { key: 'system', label: '系统管理', children: [{ key: 'system_users', label: '用户管理' }, { key: 'system_params', label: '参数配置' }, { key: 'system_logs', label: '日志审计' }] },
]

function selectRole(key) { currentRole.value = roles.find(r => r.key === key) }
function handleCheck() {}
function savePermissions() { ElMessage.success('权限配置已保存（演示模式）') }
</script>
