import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve, join } from 'path'
import { existsSync, readFileSync, statSync } from 'fs'

// ── Mock API 数据（无需启动后端即可预览）─────────────────────────────────────
const MOCK_WEATHER = {
  city: '广州', temperature: '28', humidity: '72',
  wind_direction: '东南', wind_power: '3', weather: '多云',
  report_time: new Date().toISOString().replace('T', ' ').slice(0, 19), cached: false,
}

// 真实禁飞区/限高区数据（从 data/*.shp 转换而来，存放在 public/geo/）
const GEO_DIR = resolve(__dirname, 'public/geo')
const MOCK_NO_FLY_ZONES = existsSync(join(GEO_DIR, 'nofly_zones.geojson'))
  ? JSON.parse(readFileSync(join(GEO_DIR, 'nofly_zones.geojson'), 'utf-8'))
  : { type: 'FeatureCollection', features: [] }
const MOCK_HEIGHT_LIMIT_ZONES = existsSync(join(GEO_DIR, 'height_limit_zones.geojson'))
  ? JSON.parse(readFileSync(join(GEO_DIR, 'height_limit_zones.geojson'), 'utf-8'))
  : { type: 'FeatureCollection', features: [] }

const MOCK_ZONE_STATS = {
  no_fly_zones_count: MOCK_NO_FLY_ZONES.features.length,
  height_limit_zones_count: MOCK_HEIGHT_LIMIT_ZONES.features.length,
}

const MOCK_ROUTES = [
  { id: 1, name: '天河→番禺干线', status: 'active', total_distance: 18.5, estimated_time: 22,
    waypoints: [{ lng: 113.3245, lat: 23.1201, alt: 120 }, { lng: 113.3100, lat: 23.0800, alt: 120 }, { lng: 113.2994, lat: 23.0500, alt: 100 }],
    route_line: { type: 'LineString', coordinates: [[113.3245,23.1201],[113.3100,23.0800],[113.2994,23.0500]] },
    created_at: new Date().toISOString() },
  { id: 2, name: '白云→荔湾横线', status: 'active', total_distance: 12.3, estimated_time: 15,
    waypoints: [{ lng: 113.2994, lat: 23.1540, alt: 100 }, { lng: 113.2800, lat: 23.1380, alt: 100 }, { lng: 113.2500, lat: 23.1050, alt: 100 }],
    route_line: { type: 'LineString', coordinates: [[113.2994,23.1540],[113.2800,23.1380],[113.2500,23.1050]] },
    created_at: new Date().toISOString() },
  { id: 3, name: '黄埔→天河东线', status: 'standby', total_distance: 15.8, estimated_time: 19,
    waypoints: [{ lng: 113.4500, lat: 23.1100, alt: 120 }, { lng: 113.3900, lat: 23.1200, alt: 120 }, { lng: 113.3400, lat: 23.1201, alt: 120 }],
    route_line: { type: 'LineString', coordinates: [[113.4500,23.1100],[113.3900,23.1200],[113.3400,23.1201]] },
    created_at: new Date().toISOString() },
]

// 工具：读取 POST body
function readBody(req) {
  return new Promise((resolve) => {
    let body = ''
    req.on('data', chunk => { body += chunk.toString() })
    req.on('end', () => { try { resolve(JSON.parse(body)) } catch { resolve({}) } })
  })
}

// 工具：Haversine 距离（米）
function haversine(a, b) {
  const R = 6371000
  const dLat = (b.lat - a.lat) * Math.PI / 180
  const dLng = (b.lng - a.lng) * Math.PI / 180
  const s = Math.sin(dLat / 2) ** 2 + Math.cos(a.lat * Math.PI / 180) * Math.cos(b.lat * Math.PI / 180) * Math.sin(dLng / 2) ** 2
  return R * 2 * Math.atan2(Math.sqrt(s), Math.sqrt(1 - s))
}

// ── Catmull-Rom 一维插值 ─────────────────────────────────
function catmullRom(p0, p1, p2, p3, t) {
  const t2 = t * t, t3 = t2 * t
  return 0.5 * (
    2 * p1 + (-p0 + p2) * t +
    (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 +
    (-p0 + 3 * p1 - 3 * p2 + p3) * t3
  )
}

// ── 广州城区建筑密度模型（简化 Gaussian 热力） ──────────────
// 每条记录：经度中心、纬度中心、影响半径(m)、最大建筑高度(m)
const GZ_BUILDINGS = [
  { cx: 113.3243, cy: 23.1204, r: 1100, maxH: 280 }, // 珠江新城/广州IFC
  { cx: 113.3480, cy: 23.1420, r: 700,  maxH: 175 }, // 天河北商圈
  { cx: 113.2750, cy: 23.1310, r: 850,  maxH: 115 }, // 越秀东山口
  { cx: 113.3090, cy: 23.0870, r: 750,  maxH: 140 }, // 海珠区万达
  { cx: 113.2630, cy: 23.1530, r: 650,  maxH: 120 }, // 白云广场
  { cx: 113.3610, cy: 22.9380, r: 600,  maxH: 95  }, // 番禺万达广场
  { cx: 113.3150, cy: 23.1050, r: 500,  maxH: 110 }, // 琶洲会展区
  { cx: 113.2400, cy: 23.1180, r: 550,  maxH: 100 }, // 荔湾区
]

function getBuildingHeight(lng, lat) {
  let maxH = 0
  for (const z of GZ_BUILDINGS) {
    const dx = (lng - z.cx) * 111320 * Math.cos(z.cy * Math.PI / 180)
    const dy = (lat - z.cy) * 111320
    const dist = Math.sqrt(dx * dx + dy * dy)
    if (dist < z.r) {
      maxH = Math.max(maxH, z.maxH * (1 - dist / z.r))
    }
  }
  return maxH
}

// ── 几何工具：禁飞区/障碍多边形水平绕行 ──────────────────────
const MPD = 111320  // 每纬度米数
function mPerDegLng(lat) { return 111320 * Math.cos(lat * Math.PI / 180) }

// 计算多边形包围盒 + 质心
function polyMeta(pts) {
  let minLng = Infinity, maxLng = -Infinity, minLat = Infinity, maxLat = -Infinity, cx = 0, cy = 0
  for (const p of pts) {
    minLng = Math.min(minLng, p.lng); maxLng = Math.max(maxLng, p.lng)
    minLat = Math.min(minLat, p.lat); maxLat = Math.max(maxLat, p.lat)
    cx += p.lng; cy += p.lat
  }
  return { pts, minLng, maxLng, minLat, maxLat, cx: cx / pts.length, cy: cy / pts.length }
}
// 把 GeoJSON 禁飞区解析为多边形（外环）数组
function buildNoFlyPolys(geojson) {
  const polys = []
  for (const f of (geojson.features || [])) {
    const g = f.geometry; if (!g) continue
    const rings = g.type === 'Polygon' ? [g.coordinates[0]]
      : g.type === 'MultiPolygon' ? g.coordinates.map(c => c[0]) : []
    for (const ring of rings) {
      const pts = ring.map(c => ({ lng: c[0], lat: c[1] }))
      if (pts.length >= 3) polys.push(polyMeta(pts))
    }
  }
  return polys
}
const NO_FLY_POLYS = buildNoFlyPolys(MOCK_NO_FLY_ZONES)

// 点在多边形内（射线法）
function pointInPoly(lng, lat, poly) {
  const p = poly.pts; let inside = false
  for (let i = 0, j = p.length - 1; i < p.length; j = i++) {
    const xi = p[i].lng, yi = p[i].lat, xj = p[j].lng, yj = p[j].lat
    if (((yi > lat) !== (yj > lat)) && (lng < (xj - xi) * (lat - yi) / (yj - yi) + xi)) inside = !inside
  }
  return inside
}
// 线段相交判定
function ccw(a, b, c) { return (b.lng - a.lng) * (c.lat - a.lat) - (b.lat - a.lat) * (c.lng - a.lng) }
function segIntersect(a, b, c, d) {
  const d1 = ccw(c, d, a), d2 = ccw(c, d, b), d3 = ccw(a, b, c), d4 = ccw(a, b, d)
  return ((d1 > 0) !== (d2 > 0)) && ((d3 > 0) !== (d4 > 0))
}
// 线段是否穿过多边形（端点在内 或 与任一边相交）
function segHitsPoly(a, b, poly) {
  if (Math.max(a.lng, b.lng) < poly.minLng || Math.min(a.lng, b.lng) > poly.maxLng ||
      Math.max(a.lat, b.lat) < poly.minLat || Math.min(a.lat, b.lat) > poly.maxLat) return false
  if (pointInPoly(a.lng, a.lat, poly) || pointInPoly(b.lng, b.lat, poly)) return true
  const p = poly.pts
  for (let i = 0, j = p.length - 1; i < p.length; j = i++) {
    if (segIntersect(a, b, p[j], p[i])) return true
  }
  return false
}
// 凸包（Andrew monotone chain）
function convexHull(points) {
  const pts = points.slice().sort((a, b) => a.lng - b.lng || a.lat - b.lat)
  if (pts.length < 3) return pts
  const cr = (o, a, b) => (a.lng - o.lng) * (b.lat - o.lat) - (a.lat - o.lat) * (b.lng - o.lng)
  const lo = []
  for (const p of pts) { while (lo.length >= 2 && cr(lo[lo.length - 2], lo[lo.length - 1], p) <= 0) lo.pop(); lo.push(p) }
  const up = []
  for (let i = pts.length - 1; i >= 0; i--) { const p = pts[i]; while (up.length >= 2 && cr(up[up.length - 2], up[up.length - 1], p) <= 0) up.pop(); up.push(p) }
  lo.pop(); up.pop()
  return lo.concat(up)
}
// 凸包按质心向外扩张 marginM 米（安全缓冲）
function bufferHull(hull, marginM) {
  let cx = 0, cy = 0; for (const p of hull) { cx += p.lng; cy += p.lat } cx /= hull.length; cy /= hull.length
  return hull.map(p => {
    const ml = mPerDegLng(p.lat)
    const dx = (p.lng - cx) * ml, dy = (p.lat - cy) * MPD
    const d = Math.hypot(dx, dy) || 1
    return { lng: p.lng + (dx / d) * marginM / ml, lat: p.lat + (dy / d) * marginM / MPD }
  })
}
// 在缓冲凸包的某一侧绕行：返回该侧顶点（按沿 AB 投影排序）
function detourSide(A, B, hull, side) {
  const ml = mPerDegLng((A.lat + B.lat) / 2)
  const abx = (B.lng - A.lng) * ml, aby = (B.lat - A.lat) * MPD
  const L = Math.hypot(abx, aby) || 1
  const ux = abx / L, uy = aby / L
  const px = -uy, py = ux  // 左侧法向
  const sel = []
  for (const v of hull) {
    const vx = (v.lng - A.lng) * ml, vy = (v.lat - A.lat) * MPD
    const perp = vx * px + vy * py
    if (side > 0 ? perp > 0 : perp < 0) sel.push({ v, along: vx * ux + vy * uy })
  }
  if (!sel.length) return null
  sel.sort((a, b) => a.along - b.along)
  return sel.map(o => o.v)
}
// 障碍绕行主流程：迭代地为每段插入绕行顶点，直到无穿越或达上限
function avoidObstacles(ctrl, polys, marginM, maxInsert = 80) {
  if (!polys.length) return { ctrl, count: 0 }
  let path = ctrl.slice()
  let guard = 0, count = 0, i = 0
  while (i < path.length - 1 && guard < maxInsert) {
    const A = path[i], B = path[i + 1]
    let hit = null
    for (const poly of polys) { if (segHitsPoly(A, B, poly)) { hit = poly; break } }
    if (!hit) { i++; continue }
    guard++
    const hull = bufferHull(convexHull(hit.pts), marginM)
    const left = detourSide(A, B, hull, +1)
    const right = detourSide(A, B, hull, -1)
    const cand = []
    if (left) cand.push([A, ...left, B])
    if (right) cand.push([A, ...right, B])
    if (!cand.length) { i++; continue }
    const plen = (a) => { let s = 0; for (let k = 0; k < a.length - 1; k++) s += haversine(a[k], a[k + 1]); return s }
    cand.sort((a, b) => plen(a) - plen(b))
    path.splice(i, 2, ...cand[0])  // 用 A...绕行点...B 取代原 A,B
    count++
    // 不前进 i：复检新子段（可能仍穿过其它禁飞区）
  }
  return { ctrl: path, count }
}
// 把孤立点推到多边形外侧（样条过冲修正）
function pushOutOfPoly(pt, poly, stepM) {
  let p = pt
  const ml = mPerDegLng(poly.cy)
  for (let it = 0; it < 8 && pointInPoly(p.lng, p.lat, poly); it++) {
    const dx = (p.lng - poly.cx) * ml, dy = (p.lat - poly.cy) * MPD
    const d = Math.hypot(dx, dy) || 1
    p = { lng: p.lng + (dx / d) * stepM / ml, lat: p.lat + (dy / d) * stepM / MPD }
  }
  return p
}
// 把高层建筑群（高斯模型）转成阻挡核心八边形，用于统一的水平绕行
function buildingObstacles(cruiseAlt) {
  const obs = []
  const RATIO = 0.85  // 建筑高度 > 巡航 85% 才算挡路（更低的从上方飞过）
  for (const z of GZ_BUILDINGS) {
    if (z.maxH <= cruiseAlt * RATIO) continue
    const blockR = z.r * (1 - (cruiseAlt * RATIO) / z.maxH)
    if (blockR < 60) continue
    const pts = []
    for (let k = 0; k < 8; k++) {
      const a = k / 8 * 2 * Math.PI
      pts.push({ lng: z.cx + Math.cos(a) * blockR / mPerDegLng(z.cy), lat: z.cy + Math.sin(a) * blockR / MPD })
    }
    obs.push(polyMeta(pts))
  }
  return obs
}
// 点到多边形最近距离（米）——用于绕行段高亮判定
function distToPoly(lng, lat, poly) {
  let best = Infinity
  const ml = mPerDegLng(lat)
  const p = poly.pts
  for (let i = 0, j = p.length - 1; i < p.length; j = i++) {
    const ax = (p[j].lng - lng) * ml, ay = (p[j].lat - lat) * MPD
    const bx = (p[i].lng - lng) * ml, by = (p[i].lat - lat) * MPD
    const dx = bx - ax, dy = by - ay
    const t = Math.max(0, Math.min(1, -(ax * dx + ay * dy) / (dx * dx + dy * dy || 1)))
    best = Math.min(best, Math.hypot(ax + t * dx, ay + t * dy))
  }
  return best
}

// ── Mock 路径规划：Catmull-Rom 曲线 + 建筑避让 + 精细化检验 ─
function mockPlanPath(params) {
  const {
    start, end, waypoints = [], drone_speed = 15,
    avoid_buildings = true, avoid_no_fly = true, suggested_alt = 120,
  } = params
  if (!start || !end) {
    return { is_feasible: false, warnings: ['缺少起终点'], path: [], altitude_profile: [], total_distance: 0, estimated_time: 0 }
  }

  const CRUISE_ALT = Math.max(Math.min(suggested_alt, 300), 30)
  const ASCENT_R = 0.12, DESCENT_R = 0.12

  // ── 0. 障碍绕行：禁飞区多边形 + 高层建筑核心，统一凸包水平绕行 ─
  let ctrl = [start, ...waypoints, end]
  const usedObstacles = []   // { poly, margin, kind } —— 用于绕行段高亮与样条修正
  let noFlyDetours = 0, buildingDetours = 0

  if (avoid_no_fly !== false && NO_FLY_POLYS.length) {
    const r = avoidObstacles(ctrl, NO_FLY_POLYS, 180, 100)  // 禁飞区缓冲 180m
    ctrl = r.ctrl; noFlyDetours = r.count
    for (const poly of NO_FLY_POLYS) usedObstacles.push({ poly, margin: 180, kind: 'no_fly' })
  }
  if (avoid_buildings !== false) {
    const bObs = buildingObstacles(CRUISE_ALT)
    const r = avoidObstacles(ctrl, bObs, 80, 100)  // 建筑缓冲 80m
    ctrl = r.ctrl; buildingDetours = r.count
    for (const poly of bObs) usedObstacles.push({ poly, margin: 80, kind: 'building' })
  }

  // ── 1. Catmull-Rom 样条 ─
  const STEPS = 16
  const ext = [ctrl[0], ...ctrl, ctrl[ctrl.length - 1]]
  const spline = []
  for (let i = 1; i < ext.length - 2; i++) {
    const p0 = ext[i - 1], p1 = ext[i], p2 = ext[i + 1], p3 = ext[i + 2]
    for (let k = 0; k < STEPS; k++) {
      const t = k / STEPS
      spline.push({
        lng: catmullRom(p0.lng, p1.lng, p2.lng, p3.lng, t),
        lat: catmullRom(p0.lat, p1.lat, p2.lat, p3.lat, t),
      })
    }
  }
  spline.push({ lng: end.lng, lat: end.lat })
  spline[0] = { lng: start.lng, lat: start.lat }
  const n = spline.length

  // 样条平滑可能把弧线"剪"回禁飞区内 → 逐点外推修正（硬约束）
  if (avoid_no_fly !== false) {
    for (let i = 1; i < n - 1; i++) {
      for (const o of usedObstacles) {
        if (o.kind === 'no_fly' && pointInPoly(spline[i].lng, spline[i].lat, o.poly)) {
          spline[i] = pushOutOfPoly(spline[i], o.poly, o.margin + 40)
        }
      }
    }
  }

  // ── 2. 高度剖面：起降斜坡 + 巡航；低矮建筑从上方小幅抬升飞过 ─
  const rawAlt = spline.map((p, i) => {
    const t = i / Math.max(n - 1, 1)
    let alt, phase
    if (t < ASCENT_R) { alt = 20 + (CRUISE_ALT - 20) * (t / ASCENT_R); phase = 'ascent' }
    else if (t > 1 - DESCENT_R) { alt = 20 + (CRUISE_ALT - 20) * ((1 - t) / DESCENT_R); phase = 'descent' }
    else { alt = CRUISE_ALT; phase = 'cruise' }

    // 巡航段：靠近被绕行的障碍 → 高亮（红=禁飞绕行 / 紫=建筑绕行）
    if (phase === 'cruise') {
      for (const o of usedObstacles) {
        if (distToPoly(p.lng, p.lat, o.poly) < o.margin * 1.6) {
          phase = o.kind === 'no_fly' ? 'no_fly' : 'building'
          break
        }
      }
    }

    // 低矮建筑（未触发水平绕行）从上方小幅抬升飞过
    if (avoid_buildings !== false && (phase === 'cruise')) {
      const bh = getBuildingHeight(p.lng, p.lat)
      const needed = bh * 1.25 + 25
      if (bh > 0 && alt < needed) alt = needed
    }
    return { alt: Math.round(alt), phase }
  })

  // ── 3. 高度平滑：膨胀消除孤立尖点 + 均值平滑（杜绝针尖）─
  const altArr = rawAlt.map(r => r.alt)
  const dil = altArr.map((_, i) => {
    let m = altArr[i]
    for (let k = -2; k <= 2; k++) { const j = i + k; if (j >= 0 && j < n) m = Math.max(m, altArr[j]) }
    return m
  })
  const sm = dil.map((_, i) => {
    let s = 0, c = 0
    for (let k = -2; k <= 2; k++) { const j = i + k; if (j >= 0 && j < n) { s += dil[j]; c++ } }
    return Math.round(s / c)
  })
  // 起降段保留原始斜坡
  for (let i = 0; i < n; i++) {
    if (rawAlt[i].phase === 'ascent' || rawAlt[i].phase === 'descent') sm[i] = rawAlt[i].alt
  }

  const path = spline.map((p, idx) => ({ lng: p.lng, lat: p.lat, alt: sm[idx], index: idx }))
  const altitude_profile = spline.map((p, idx) => ({ index: idx, alt: sm[idx], phase: rawAlt[idx].phase }))

  // ── 4. 统计 ─
  let total_distance = 0
  for (let i = 0; i < ctrl.length - 1; i++) total_distance += haversine(ctrl[i], ctrl[i + 1])
  total_distance = Math.round(total_distance * 1.05)
  const estimated_time = Math.round(total_distance / (drone_speed * 1000 / 3600))

  const warnings = []
  if (noFlyDetours > 0) warnings.push(`已水平绕行 ${noFlyDetours} 处禁飞区（保持安全缓冲距离）`)
  if (buildingDetours > 0) warnings.push(`已水平绕行 ${buildingDetours} 处高层建筑群（保持建议高度 ${CRUISE_ALT}m）`)
  const maxAlt = Math.max(...altitude_profile.map(p => p.alt))
  if (maxAlt > 200) warnings.push(`最高飞行高度 ${maxAlt}m，请确认已获得空域授权`)

  return { is_feasible: true, total_distance, estimated_time, warnings, path, altitude_profile }
}

// Vite 插件：拦截 /api 请求返回 Mock 数据（无需后端）
function mockApiPlugin() {
  const MOCK_MAP = {
    'GET /api/weather/live': MOCK_WEATHER,
    'GET /api/zones/no-fly': MOCK_NO_FLY_ZONES,
    'GET /api/zones/height-limit': MOCK_HEIGHT_LIMIT_ZONES,
    'GET /api/zones/stats': MOCK_ZONE_STATS,
    'GET /api/routes/': MOCK_ROUTES,
    'GET /api/routes': MOCK_ROUTES,
    'GET /api/zones/check-point': { in_no_fly_zone: false, height_limits: [] },
  }
  return {
    name: 'mock-api',
    configureServer(server) {
      server.middlewares.use('/api', async (req, res, next) => {
        const urlPath = req.url?.split('?')[0] || ''
        const key = `${req.method} /api${urlPath}`

        // CORS 预检
        if (req.method === 'OPTIONS') {
          res.setHeader('Access-Control-Allow-Origin', '*')
          res.setHeader('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS')
          res.setHeader('Access-Control-Allow-Headers', 'Content-Type,Authorization')
          res.statusCode = 204; res.end(); return
        }

        // 静态 GET mock
        const data = MOCK_MAP[key]
        if (data !== undefined) {
          res.setHeader('Content-Type', 'application/json')
          res.setHeader('Access-Control-Allow-Origin', '*')
          res.statusCode = 200
          res.end(JSON.stringify(data))
          return
        }

        // POST /api/pathfinding/plan
        if (req.method === 'POST' && urlPath === '/pathfinding/plan') {
          const body = await readBody(req)
          const result = mockPlanPath(body)
          res.setHeader('Content-Type', 'application/json')
          res.setHeader('Access-Control-Allow-Origin', '*')
          res.statusCode = 200
          res.end(JSON.stringify(result))
          return
        }

        next()
      })
    },
  }
}

const CESIUM_DIR = resolve(__dirname, 'node_modules/cesium/Build/Cesium')

// 插件：在 dev 模式直接 serve Cesium 静态资源，build 时复制到 dist
function cesiumServe() {
  return {
    name: 'cesium-serve',
    configureServer(server) {
      // Dev: serve cesium static files from node_modules
      server.middlewares.use('/cesium', (req, res, next) => {
        const url = new URL(req.url, 'http://localhost')
        const filePath = join(CESIUM_DIR, url.pathname)
        if (!existsSync(filePath) || statSync(filePath).isDirectory()) {
          return next()
        }
        try {
          const content = readFileSync(filePath)
          const ext = url.pathname.split('.').pop()
          const mimeTypes = {
            js: 'application/javascript',
            css: 'text/css',
            png: 'image/png',
            svg: 'image/svg+xml',
            wasm: 'application/wasm',
          }
          res.setHeader('Content-Type', mimeTypes[ext] || 'application/octet-stream')
          res.setHeader('Cache-Control', 'public, max-age=3600')
          res.end(content)
        } catch {
          next()
        }
      })
    },
    // Build: 写入 index.html 时不注入 cesium 全局脚本
    transformIndexHtml: {
      order: 'post',
      handler(html) {
        // 移除任何 cesium 全局脚本引用（防止 vite-plugin-cesium 或其他注入）
        return html
      },
    },
  }
}

export default defineConfig({
  plugins: [
    vue(),
    cesiumServe(),
    mockApiPlugin(),
  ],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  server: {
    port: 5173,
    host: '0.0.0.0',
  },
  build: {
    rollupOptions: {
      // Cesium 有 export 兼容问题，构建时外部化
      external: ['cesium', '@cesium/engine', '@cesium/widgets'],
      output: {
        globals: {
          cesium: 'Cesium',
        },
      },
    },
  },
  optimizeDeps: {
    exclude: ['cesium'],
  },
})
