/**
 * 禁飞区和限高区 API
 */
import request from './request'

/** 获取所有禁飞区（GeoJSON） */
export function getNoFlyZones() {
  return request.get('/zones/no-fly')
}

/** 获取所有限高区（GeoJSON） */
export function getHeightLimitZones() {
  return request.get('/zones/height-limit')
}

/** 获取区域统计 */
export function getZoneStats() {
  return request.get('/zones/stats')
}

/** 检查点的约束信息 */
export function checkPoint(lng, lat) {
  return request.get('/zones/check-point', { params: { lng, lat } })
}
