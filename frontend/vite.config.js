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
// 点到多边形最近距离（米）——用于栅格障碍判定与绕行段高亮
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

// ════════════════════════════════════════════════════════════════════
// Mock 路径规划：8 方向栅格 A*（航线沿 45° 倍数走向，水平绕开障碍）
//
// 设计要点（回归后端最初的栅格 A* 思路）：
//   · 飞行高度 = 强制飞行限高（hard ceiling），不再是"建议"高度；
//   · 高于限高的高层建筑群 → 栅格不可通行 → A* 水平绕开（45° 折线）；
//   · 低于限高的建筑 → 可通行，无人机在限高高度从上方飞过（不再拔尖）；
//   · 禁飞区（含安全缓冲）→ 永远不可通行，A* 强制绕行。
// ════════════════════════════════════════════════════════════════════

// 最小二叉堆（A* 开放集）
class MinHeap {
  constructor() { this.a = [] }
  get size() { return this.a.length }
  push(node) {
    const a = this.a; a.push(node); let i = a.length - 1
    while (i > 0) { const p = (i - 1) >> 1; if (a[p].f <= a[i].f) break;[a[p], a[i]] = [a[i], a[p]]; i = p }
  }
  pop() {
    const a = this.a, top = a[0], last = a.pop()
    if (a.length) { a[0] = last; let i = 0; const n = a.length
      while (true) { let s = i, l = 2 * i + 1, r = l + 1
        if (l < n && a[l].f < a[s].f) s = l
        if (r < n && a[r].f < a[s].f) s = r
        if (s === i) break;[a[s], a[i]] = [a[i], a[s]]; i = s } }
    return top
  }
}

const NF_MARGIN = 150   // 禁飞区安全缓冲（米）
const BUILD_RATIO = 1.0 // 建筑高度 > 限高 × 此系数 才算挡路（须绕行）

function mockPlanPath(params) {
  const {
    start, end, waypoints = [], drone_speed = 15,
    avoid_buildings = true, avoid_no_fly = true, suggested_alt = 120,
  } = params
  if (!start || !end) {
    return { is_feasible: false, warnings: ['缺少起终点'], path: [], altitude_profile: [], total_distance: 0, estimated_time: 0 }
  }

  const CEIL = Math.max(Math.min(suggested_alt, 300), 30)  // 强制飞行限高
  const doNoFly = avoid_no_fly !== false
  const doBuild = avoid_buildings !== false
  const ctrlPts = [start, ...waypoints, end]

  // ── 0. 起点/途经点/终点落在禁飞区内 → 拒绝规划（任何一点都不行）─
  if (NO_FLY_POLYS.length) {
    const labelOf = (i) => i === 0 ? '起点' : i === ctrlPts.length - 1 ? '终点' : `途经点${i}`
    const blocked_points = []
    ctrlPts.forEach((p, i) => {
      for (const poly of NO_FLY_POLYS) {
        if (p.lng < poly.minLng || p.lng > poly.maxLng || p.lat < poly.minLat || p.lat > poly.maxLat) continue
        if (pointInPoly(p.lng, p.lat, poly)) {
          blocked_points.push({ index: i, label: labelOf(i), lng: p.lng, lat: p.lat })
          break
        }
      }
    })
    if (blocked_points.length) {
      const names = blocked_points.map(b => b.label).join('、')
      return {
        is_feasible: false,
        blocked_in_no_fly: true,
        blocked_points,
        warnings: [`${names} 位于禁飞区内，无法规划航线，请重新选择点位`],
        path: [], altitude_profile: [], total_distance: 0, estimated_time: 0,
      }
    }
  }

  // ── 1. 构建栅格 ─────────────────────────────────────────
  let minLng = Infinity, maxLng = -Infinity, minLat = Infinity, maxLat = -Infinity
  for (const p of ctrlPts) {
    minLng = Math.min(minLng, p.lng); maxLng = Math.max(maxLng, p.lng)
    minLat = Math.min(minLat, p.lat); maxLat = Math.max(maxLat, p.lat)
  }
  const buf = 0.03  // 约 3km 搜索缓冲，给绕行留出空间
  minLng -= buf; maxLng += buf; minLat -= buf; maxLat += buf
  const latMid = (minLat + maxLat) / 2
  const mLng = mPerDegLng(latMid)
  const wM = (maxLng - minLng) * mLng, hM = (maxLat - minLat) * MPD
  // 目标 ~220 格/边，精度 30~140m（建筑间隙可穿行又不至于太慢）
  const cellM = Math.max(30, Math.min(140, Math.max(wM, hM) / 220))
  const cellLat = cellM / MPD
  const cellLng = cellM / mLng
  const rows = Math.max(2, Math.ceil((maxLat - minLat) / cellLat))
  const cols = Math.max(2, Math.ceil((maxLng - minLng) / cellLng))

  const cellCenter = (r, c) => ({ lng: minLng + (c + 0.5) * cellLng, lat: minLat + (r + 0.5) * cellLat })
  const toCell = (p) => ({
    r: Math.max(0, Math.min(rows - 1, Math.floor((p.lat - minLat) / cellLat))),
    c: Math.max(0, Math.min(cols - 1, Math.floor((p.lng - minLng) / cellLng))),
  })

  // 障碍判定（带缓存）：返回 'no_fly' | 'building' | null
  const blockCache = new Map()
  function blockKind(r, c) {
    const key = r * cols + c
    const cached = blockCache.get(key)
    if (cached !== undefined) return cached
    const { lng, lat } = cellCenter(r, c)
    let kind = null
    if (doNoFly) {
      for (const poly of NO_FLY_POLYS) {
        if (lng < poly.minLng - 0.02 || lng > poly.maxLng + 0.02 ||
            lat < poly.minLat - 0.02 || lat > poly.maxLat + 0.02) continue
        if (pointInPoly(lng, lat, poly) || distToPoly(lng, lat, poly) < NF_MARGIN) { kind = 'no_fly'; break }
      }
    }
    if (!kind && doBuild && getBuildingHeight(lng, lat) > CEIL * BUILD_RATIO) kind = 'building'
    blockCache.set(key, kind)
    return kind
  }

  // ── 2. 单段 8 方向 A* ──────────────────────────────────
  function astarSeg(sCell, gCell) {
    const gKey = gCell.r * cols + gCell.c
    const octile = (r, c) => {
      const dr = Math.abs(r - gCell.r), dc = Math.abs(c - gCell.c)
      return cellM * (Math.max(dr, dc) + (Math.SQRT2 - 1) * Math.min(dr, dc))
    }
    const open = new MinHeap()
    const gScore = new Map(), parent = new Map()
    const sKey = sCell.r * cols + sCell.c
    gScore.set(sKey, 0)
    open.push({ r: sCell.r, c: sCell.c, f: octile(sCell.r, sCell.c) })
    const closed = new Set()
    let guard = 0, maxGuard = rows * cols
    while (open.size && guard++ < maxGuard) {
      const cur = open.pop()
      const cKey = cur.r * cols + cur.c
      if (cKey === gKey) {           // 回溯
        const cells = []; let k = cKey
        while (k !== undefined) { cells.push({ r: Math.floor(k / cols), c: k % cols }); k = parent.get(k) }
        cells.reverse(); return cells
      }
      if (closed.has(cKey)) continue
      closed.add(cKey)
      const gCur = gScore.get(cKey)
      for (let dr = -1; dr <= 1; dr++) for (let dc = -1; dc <= 1; dc++) {
        if (!dr && !dc) continue
        const nr = cur.r + dr, nc = cur.c + dc
        if (nr < 0 || nc < 0 || nr >= rows || nc >= cols) continue
        const nKey = nr * cols + nc
        if (closed.has(nKey)) continue
        // 起终格永远允许，其余格按障碍判定
        if (nKey !== gKey && blockKind(nr, nc)) continue
        if (dr && dc) {  // 防斜穿障碍角
          if (blockKind(cur.r, nc) || blockKind(nr, cur.c)) continue
        }
        const step = (dr && dc) ? cellM * Math.SQRT2 : cellM
        const ng = gCur + step
        if (ng < (gScore.get(nKey) ?? Infinity)) {
          gScore.set(nKey, ng); parent.set(nKey, cKey)
          open.push({ r: nr, c: nc, f: ng + octile(nr, nc) })
        }
      }
    }
    return null  // 不可达
  }

  // ── 3. 逐段规划并拼接 ──────────────────────────────────
  const warnings = []
  let isFeasible = true
  let routeCells = []  // [{r,c}]
  for (let s = 0; s < ctrlPts.length - 1; s++) {
    const seg = astarSeg(toCell(ctrlPts[s]), toCell(ctrlPts[s + 1]))
    if (!seg) {
      isFeasible = false
      warnings.push(`路径段 ${s + 1} 无法绕过障碍（可能被禁飞区封闭）`)
      routeCells.push(toCell(ctrlPts[s]), toCell(ctrlPts[s + 1]))
      continue
    }
    if (routeCells.length && seg.length) seg.shift()  // 去重接缝
    routeCells = routeCells.concat(seg)
  }

  // 栅格中心 → 经纬度；首尾对齐精确起终点
  let poly = routeCells.map(({ r, c }) => cellCenter(r, c))
  if (poly.length) { poly[0] = { lng: start.lng, lat: start.lat }; poly[poly.length - 1] = { lng: end.lng, lat: end.lat } }

  // 共线点合并（保留干净的 45° 折线）
  const simplified = []
  for (let i = 0; i < poly.length; i++) {
    if (i === 0 || i === poly.length - 1) { simplified.push(poly[i]); continue }
    const a = poly[i - 1], b = poly[i], cc = poly[i + 1]
    const cross = (b.lng - a.lng) * (cc.lat - a.lat) - (b.lat - a.lat) * (cc.lng - a.lng)
    if (Math.abs(cross) > 1e-9) simplified.push(b)
  }
  poly = simplified.length >= 2 ? simplified : poly

  // ── 4. Catmull-Rom 样条柔滑：把 45° 折线变成视觉曲线 ─────────
  // 每段按弧长细分采样数，弧线更圆润；样条采样点若回落进障碍格则向外推出
  const SAMPLE_M = Math.max(36, cellM)
  const ext = [poly[0], ...poly, poly[poly.length - 1]]
  let dense = []
  for (let i = 1; i < ext.length - 2; i++) {
    const p0 = ext[i - 1], p1 = ext[i], p2 = ext[i + 1], p3 = ext[i + 2]
    const steps = Math.max(2, Math.round(haversine(p1, p2) / SAMPLE_M))
    for (let k = 0; k < steps; k++) {
      const t = k / steps
      dense.push({
        lng: catmullRom(p0.lng, p1.lng, p2.lng, p3.lng, t),
        lat: catmullRom(p0.lat, p1.lat, p2.lat, p3.lat, t),
      })
    }
  }
  dense.push({ lng: end.lng, lat: end.lat })
  dense[0] = { lng: start.lng, lat: start.lat }

  // 柔滑可能把弧线"剪"进障碍格 → 逐点推回最近的可通行格（硬约束）
  const pushOutOfBlocked = (p) => {
    const cell = toCell(p)
    if (!blockKind(cell.r, cell.c)) return p
    for (let rad = 1; rad <= 6; rad++) {
      let best = null, bestD = Infinity
      for (let dr = -rad; dr <= rad; dr++) for (let dc = -rad; dc <= rad; dc++) {
        if (Math.max(Math.abs(dr), Math.abs(dc)) !== rad) continue
        const nr = cell.r + dr, nc = cell.c + dc
        if (nr < 0 || nc < 0 || nr >= rows || nc >= cols) continue
        if (blockKind(nr, nc)) continue
        const cc = cellCenter(nr, nc)
        const d = (cc.lng - p.lng) ** 2 + (cc.lat - p.lat) ** 2
        if (d < bestD) { bestD = d; best = cc }
      }
      if (best) return best
    }
    return p
  }
  for (let i = 1; i < dense.length - 1; i++) dense[i] = pushOutOfBlocked(dense[i])
  const n = dense.length

  // ── 5. 高度剖面 + 相位配色 ─────────────────────────────
  const ASCENT_R = 0.1, DESCENT_R = 0.1
  let nearNoFly = false, nearBuilding = false
  const profile = dense.map((p, i) => {
    const t = i / Math.max(n - 1, 1)
    let alt, phase
    if (t < ASCENT_R) { alt = 20 + (CEIL - 20) * (t / ASCENT_R); phase = 'ascent' }
    else if (t > 1 - DESCENT_R) { alt = 20 + (CEIL - 20) * ((1 - t) / DESCENT_R); phase = 'descent' }
    else { alt = CEIL; phase = 'cruise' }

    if (phase === 'cruise') {
      // 贴近禁飞区缓冲 → 红色绕行段
      if (doNoFly) {
        for (const o of NO_FLY_POLYS) {
          if (p.lng < o.minLng - 0.02 || p.lng > o.maxLng + 0.02 || p.lat < o.minLat - 0.02 || p.lat > o.maxLat + 0.02) continue
          if (distToPoly(p.lng, p.lat, o) < NF_MARGIN * 1.8) { phase = 'no_fly'; nearNoFly = true; break }
        }
      }
      // 紧贴/飞越高层建筑 → 紫色段
      if (phase === 'cruise' && doBuild) {
        const bh = getBuildingHeight(p.lng, p.lat)
        if (bh > CEIL * 0.55) { phase = 'building'; nearBuilding = true }
      }
    }
    return { alt: Math.round(alt), phase }
  })

  const path = dense.map((p, idx) => ({ lng: p.lng, lat: p.lat, alt: profile[idx].alt, index: idx }))
  const altitude_profile = profile.map((r, idx) => ({ index: idx, alt: r.alt, phase: r.phase }))

  // ── 6. 统计与提示 ──────────────────────────────────────
  let total_distance = 0
  for (let i = 0; i < dense.length - 1; i++) total_distance += haversine(dense[i], dense[i + 1])
  total_distance = Math.round(total_distance)
  const estimated_time = Math.round(total_distance / (drone_speed * 1000 / 3600))

  if (nearNoFly) warnings.push('已水平绕行禁飞区（保持安全缓冲距离）')
  if (nearBuilding) warnings.push(`已水平绕行高于限高的高层建筑群（强制飞行限高 ${CEIL}m）`)
  if (CEIL > 200) warnings.push(`飞行限高 ${CEIL}m，请确认已获得空域授权`)

  return { is_feasible: isFeasible, total_distance, estimated_time, warnings, path, altitude_profile }
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
