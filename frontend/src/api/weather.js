/**
 * 天气查询 API
 */
import request from './request'

/** 获取实时天气 */
export function getLiveWeather(city = '广州') {
  return request.get('/weather/live', { params: { city } })
}

/** 获取天气预报 */
export function getWeatherForecast(city = '广州') {
  return request.get('/weather/forecast', { params: { city } })
}

/** 检查是否适合飞行 */
export function checkFlyable(city = '广州') {
  return request.get('/weather/flyable', { params: { city } })
}
