/**
 * 航线管理 API
 */
import request from './request'

/** 获取所有航线 */
export function getAllRoutes() {
  return request.get('/routes/')
}

/** 获取航线详情 */
export function getRoute(id) {
  return request.get(`/routes/${id}`)
}

/** 创建航线 */
export function createRoute(data) {
  return request.post('/routes/', data)
}
