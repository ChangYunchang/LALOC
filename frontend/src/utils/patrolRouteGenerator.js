/**
 * 巡逻路线生成工具
 * - generateBoundaryPatrol: 边界巡逻（沿多边形边界飞行）
 * - generateLawnmowerPatrol: 犁地式覆盖巡逻（boustrophedon 蛇形折返）
 *
 * 所有计算在经纬度坐标系下完成，假设区域尺度较小（< 几十公里），
 * 近似使用平面几何（经纬度当作平面坐标）。
 */

// ── 基础几何工具 ────────────────────────────────────────

/** 两点距离（Haversine，米） */
function haversineDistance(a, b) {
  const R = 6371000
  const dLat = ((b.lat - a.lat) * Math.PI) / 180
  const dLng = ((b.lng - a.lng) * Math.PI) / 180
  const lat1 = (a.lat * Math.PI) / 180
  const lat2 = (b.lat * Math.PI) / 180
  const sinDLat2 = Math.sin(dLat / 2)
  const sinDLng2 = Math.sin(dLng / 2)
  const aa = sinDLat2 * sinDLat2 + Math.cos(lat1) * Math.cos(lat2) * sinDLng2 * sinDLng2
  return R * 2 * Math.atan2(Math.sqrt(aa), Math.sqrt(1 - aa))
}

/** 度→米 近似（纬度方向） */
function degToMetersLat(deg) {
  return deg * 111320
}

/** 度→米 近似（经度方向，需传入纬度） */
function degToMetersLng(deg, lat) {
  return deg * 111320 * Math.cos((lat * Math.PI) / 180)
}

/** 米→度 近似（纬度方向） */
function metersToDegLat(m) {
  return m / 111320
}

/** 米→度 近似（经度方向） */
function metersToDegLng(m, lat) {
  return m / (111320 * Math.cos((lat * Math.PI) / 180))
}

// ── 线段交点 ────────────────────────────────────────────

/**
 * 两条线段是否相交（含端点），返回交点或 null
 */
function segmentIntersection(p1, p2, p3, p4) {
  const x1 = p1.lng, y1 = p1.lat
  const x2 = p2.lng, y2 = p2.lat
  const x3 = p3.lng, y3 = p3.lat
  const x4 = p4.lng, y4 = p4.lat

  const denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
  if (Math.abs(denom) < 1e-12) return null // 平行

  const t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
  const u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / denom

  if (t >= 0 && t <= 1 && u >= 0 && u <= 1) {
    return {
      lng: x1 + t * (x2 - x1),
      lat: y1 + t * (y2 - y1),
    }
  }
  return null
}

/**
 * 射线与多边形边的交点计数（Ray Casting）
 * 返回交点的 x 坐标数组（用于判断点是否在多边形内）
 */
function rayCrossings(px, py, polygon) {
  const crossings = []
  for (let i = 0; i < polygon.length; i++) {
    const a = polygon[i]
    const b = polygon[(i + 1) % polygon.length]
    const ay = a.lat, by = b.lat
    // 检查射线 y=py 是否穿过边 ab
    if ((ay > py) !== (by > py)) {
      const ax = a.lng, bx = b.lng
      const ix = ax + ((py - ay) / (by - ay)) * (bx - ax)
      if (ix > px) {
        crossings.push(ix)
      }
    }
  }
  return crossings
}

/** 点是否在多边形内（Ray Casting） */
export function pointInPolygon(point, polygon) {
  const crossings = rayCrossings(point.lng, point.lat, polygon)
  return crossings.length % 2 === 1
}

// ── 线段裁剪到多边形内部 ────────────────────────────────

/**
 * Cohen-Sutherland 风格：将线段裁剪到多边形内部，
 * 返回多边形内部的线段片段数组 [{lng, lat}, {lng, lat}]
 * 简化实现：采样线段，取连续在多边形内的子段
 */
function clipSegmentToPolygon(p1, p2, polygon) {
  const N = 60 // 采样点数
  const samples = []
  for (let i = 0; i <= N; i++) {
    const t = i / N
    samples.push({
      lng: p1.lng + t * (p2.lng - p1.lng),
      lat: p1.lat + t * (p2.lat - p1.lat),
    })
  }

  const segments = []
  let inStarted = false
  let segStart = null

  for (let i = 0; i < samples.length; i++) {
    const inside = pointInPolygon(samples[i], polygon)
    if (inside && !inStarted) {
      inStarted = true
      segStart = samples[i]
    } else if (!inside && inStarted) {
      inStarted = false
      segments.push([segStart, samples[i - 1]])
    }
  }
  if (inStarted) {
    segments.push([segStart, samples[samples.length - 1]])
  }

  return segments
}

// ── 多边形包围盒 ─────────────────────────────────────────

function boundingBox(polygon) {
  let minLng = Infinity, maxLng = -Infinity
  let minLat = Infinity, maxLat = -Infinity
  for (const p of polygon) {
    if (p.lng < minLng) minLng = p.lng
    if (p.lng > maxLng) maxLng = p.lng
    if (p.lat < minLat) minLat = p.lat
    if (p.lat > maxLat) maxLat = p.lat
  }
  return { minLng, maxLng, minLat, maxLat }
}

// ── 旋转点（绕中心） ─────────────────────────────────────

function rotatePoint(p, center, angleDeg) {
  const rad = (angleDeg * Math.PI) / 180
  const cosA = Math.cos(rad)
  const sinA = Math.sin(rad)
  const dx = p.lng - center.lng
  const dy = p.lat - center.lat
  return {
    lng: center.lng + dx * cosA - dy * sinA,
    lat: center.lat + dx * sinA + dy * cosA,
  }
}

function rotatePolygon(polygon, center, angleDeg) {
  return polygon.map(p => rotatePoint(p, center, angleDeg))
}

// ── 边界巡逻 ─────────────────────────────────────────────

/**
 * 生成边界巡逻路线
 * @param {Array<{lng: number, lat: number}>} polygonCoords - 多边形顶点（首尾不闭合计，自动闭合）
 * @param {Object} options
 * @param {number} options.minSpacing - 顶点间最小采样间距（米），默认 30
 * @returns {Array<{lng: number, lat: number}>} 巡逻航路点
 */
export function generateBoundaryPatrol(polygonCoords, options = {}) {
  const { minSpacing = 30 } = options
  if (!polygonCoords || polygonCoords.length < 3) return []

  // 闭合多边形
  const closed = [...polygonCoords, polygonCoords[0]]

  // 对边界进行密集采样
  const sampled = []
  for (let i = 0; i < closed.length - 1; i++) {
    const a = closed[i]
    const b = closed[i + 1]
    const dist = haversineDistance(a, b)
    const steps = Math.max(2, Math.ceil(dist / minSpacing))
    for (let s = 0; s < steps; s++) {
      const t = s / steps
      sampled.push({
        lng: a.lng + t * (b.lng - a.lng),
        lat: a.lat + t * (b.lat - a.lat),
      })
    }
  }
  // 闭合最后一个点
  sampled.push({ ...polygonCoords[0] })

  return sampled
}

// ── 犁地式覆盖巡逻 ───────────────────────────────────────

/**
 * 生成犁地式（boustrophedon）覆盖巡逻路线
 * @param {Array<{lng: number, lat: number}>} polygonCoords - 多边形顶点
 * @param {Object} options
 * @param {number} options.stripSpacing - 条带间距（米），默认 100
 * @param {number} options.angle - 条带方向角度（度），0=南北，90=东西，默认 0
 * @param {number} options.margin - 边界缩进（米），默认 10
 * @returns {Array<{lng: number, lat: number}>} 巡逻航路点
 */
export function generateLawnmowerPatrol(polygonCoords, options = {}) {
  const { stripSpacing = 100, angle = 0, margin = 10 } = options
  if (!polygonCoords || polygonCoords.length < 3) return []

  const bbox = boundingBox(polygonCoords)
  const center = {
    lng: (bbox.minLng + bbox.maxLng) / 2,
    lat: (bbox.minLat + bbox.maxLat) / 2,
  }

  // 旋转多边形（使条带对齐 Y 轴）
  const rotated = angle !== 0 ? rotatePolygon(polygonCoords, center, -angle) : polygonCoords
  const rBbox = boundingBox(rotated)

  // 条带间距（转为度）
  const spacingDeg = metersToDegLng(stripSpacing, center.lat)
  const marginDeg = metersToDegLng(margin, center.lat)

  const minLng = rBbox.minLng + marginDeg
  const maxLng = rBbox.maxLng - marginDeg

  if (minLng >= maxLng) return generateBoundaryPatrol(polygonCoords)

  // 生成条带扫描线
  const waypoints = []
  let goingRight = true
  let stripCount = 0

  for (let x = minLng; x <= maxLng; x += spacingDeg) {
    // 水平扫描线从多边形底部到顶部
    const lineStart = { lng: x, lat: rBbox.minLat - 0.001 }
    const lineEnd = { lng: x, lat: rBbox.maxLat + 0.001 }

    const segments = clipSegmentToPolygon(lineStart, lineEnd, rotated)
    if (segments.length === 0) continue

    // 取最长的内部段
    const best = segments.reduce((a, b) => {
      const dA = haversineDistance(a[0], a[1])
      const dB = haversineDistance(b[0], b[1])
      return dA > dB ? a : b
    })

    const start = goingRight ? best[0] : best[1]
    const end = goingRight ? best[1] : best[0]

    waypoints.push({ lng: start.lng, lat: start.lat })
    waypoints.push({ lng: end.lng, lat: end.lat })

    goingRight = !goingRight
    stripCount++
  }

  // 如果有多个条带，连接相邻条带
  const connected = []
  for (let i = 0; i < waypoints.length; i += 2) {
    const a = waypoints[i]
    const b = waypoints[i + 1]
    if (connected.length > 0) {
      // 添加连接段（从上一个条带的终点到当前条带的起点）
      // 直接连接即可，已按交替方向排列
    }
    connected.push(a)
    connected.push(b)
  }

  // 旋转回原始坐标系
  const result = angle !== 0 ? rotatePolygon(connected, center, angle) : connected

  // 去重（相邻点距离 < 1m 合并）
  const deduped = [result[0]]
  for (let i = 1; i < result.length; i++) {
    if (haversineDistance(result[i], deduped[deduped.length - 1]) > 3) {
      deduped.push(result[i])
    }
  }

  return deduped
}
