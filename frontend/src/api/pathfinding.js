/**
 * 路径规划 API
 */
import request from './request'

/** 智能路径规划 */
export function planPath(params) {
  return request.post('/pathfinding/plan', params)
}
