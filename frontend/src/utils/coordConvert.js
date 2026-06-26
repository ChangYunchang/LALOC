/**
 * WGS-84 ↔ GCJ-02 坐标转换工具
 *
 * GCJ-02（国测局坐标系）是中国境内地图服务（高德、腾讯等）使用的加密坐标系，
 * 与 WGS-84（GPS / Cesium / PostGIS 标准）相差约 200-500 米。
 *
 * 本工具供 Amap2DView 在输入/输出时做坐标系桥接，
 * 保证系统内部及后端始终使用 WGS-84。
 */

const PI = Math.PI
const A = 6378245.0          // 克拉索夫斯基椭球体长半轴（米）
const EE = 0.00669342162296594323  // 第一偏心率平方

function _outOfChina(lng, lat) {
  return lng < 72.004 || lng > 137.8347 || lat < 0.8293 || lat > 55.8271
}

function _dLat(lng, lat) {
  let r = -100.0 + 2.0*lng + 3.0*lat + 0.2*lat*lat + 0.1*lng*lat + 0.2*Math.sqrt(Math.abs(lng))
  r += (20.0*Math.sin(6.0*lng*PI) + 20.0*Math.sin(2.0*lng*PI)) * 2.0/3.0
  r += (20.0*Math.sin(lat*PI)     + 40.0*Math.sin(lat/3.0*PI)) * 2.0/3.0
  r += (160.0*Math.sin(lat/12.0*PI) + 320.0*Math.sin(lat*PI/30.0)) * 2.0/3.0
  return r
}

function _dLng(lng, lat) {
  let r = 300.0 + lng + 2.0*lat + 0.1*lng*lng + 0.1*lng*lat + 0.1*Math.sqrt(Math.abs(lng))
  r += (20.0*Math.sin(6.0*lng*PI) + 20.0*Math.sin(2.0*lng*PI)) * 2.0/3.0
  r += (20.0*Math.sin(lng*PI)     + 40.0*Math.sin(lng/3.0*PI)) * 2.0/3.0
  r += (150.0*Math.sin(lng/12.0*PI) + 300.0*Math.sin(lng/30.0*PI)) * 2.0/3.0
  return r
}

/**
 * WGS-84 → GCJ-02
 * @param {number} lng  WGS-84 经度
 * @param {number} lat  WGS-84 纬度
 * @returns {{ lng: number, lat: number }}  GCJ-02 坐标
 */
export function wgs2gcj(lng, lat) {
  if (_outOfChina(lng, lat)) return { lng, lat }
  const radLat = lat / 180.0 * PI
  let magic = Math.sin(radLat)
  magic = 1 - EE * magic * magic
  const sqrtMagic = Math.sqrt(magic)
  const dlat = (_dLat(lng - 105.0, lat - 35.0) * 180.0) / ((A * (1 - EE)) / (magic * sqrtMagic) * PI)
  const dlng = (_dLng(lng - 105.0, lat - 35.0) * 180.0) / (A / sqrtMagic * Math.cos(radLat) * PI)
  return { lng: lng + dlng, lat: lat + dlat }
}

/**
 * GCJ-02 → WGS-84（迭代逼近，精度 < 1 米）
 * @param {number} lng  GCJ-02 经度
 * @param {number} lat  GCJ-02 纬度
 * @returns {{ lng: number, lat: number }}  WGS-84 坐标
 */
export function gcj2wgs(lng, lat) {
  if (_outOfChina(lng, lat)) return { lng, lat }
  const gcj = wgs2gcj(lng, lat)
  return { lng: lng - (gcj.lng - lng), lat: lat - (gcj.lat - lat) }
}
