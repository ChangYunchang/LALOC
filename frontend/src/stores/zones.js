/**
 * 区域数据状态管理
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getNoFlyZones, getHeightLimitZones, getZoneStats } from '@/api/zones'

export const useZoneStore = defineStore('zones', () => {
  const noFlyZones = ref(null)     // GeoJSON
  const heightLimitZones = ref(null) // GeoJSON
  const stats = ref({ no_fly_zones_count: 0, height_limit_zones_count: 0 })
  const loading = ref(false)

  async function fetchNoFlyZones() {
    loading.value = true
    try {
      noFlyZones.value = await getNoFlyZones()
    } catch (e) {
      console.error('获取禁飞区失败:', e)
    } finally {
      loading.value = false
    }
  }

  async function fetchHeightLimitZones() {
    loading.value = true
    try {
      heightLimitZones.value = await getHeightLimitZones()
    } catch (e) {
      console.error('获取限高区失败:', e)
    } finally {
      loading.value = false
    }
  }

  async function fetchStats() {
    try {
      stats.value = await getZoneStats()
    } catch (e) {
      console.error('获取统计信息失败:', e)
    }
  }

  async function fetchAll() {
    await Promise.all([fetchNoFlyZones(), fetchHeightLimitZones(), fetchStats()])
  }

  return {
    noFlyZones,
    heightLimitZones,
    stats,
    loading,
    fetchNoFlyZones,
    fetchHeightLimitZones,
    fetchStats,
    fetchAll,
  }
})
