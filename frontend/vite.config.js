import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve, join } from 'path'
import { existsSync, readFileSync, statSync } from 'fs'

// ── WGS-84 → GCJ-02 坐标转换（Mock 内部 zone 碰撞检测用）──────────────────
// 禁飞区 GeoJSON 存储为 GCJ-02；路径规划的起终点在我们的坐标系中已统一为 WGS-84，
// 因此在做 pointInPoly / distToPoly 前需先将 WGS-84 转换为 GCJ-02。
const _MCK_PI = Math.PI
const _MCK_A  = 6378245.0
const _MCK_EE = 0.00669342162296594323
function _mckOutCN(lng, lat) {
  return lng < 72.004 || lng > 137.8347 || lat < 0.8293 || lat > 55.8271
}
function _mckDLat(lng, lat) {
  let r = -100 + 2*lng + 3*lat + 0.2*lat*lat + 0.1*lng*lat + 0.2*Math.sqrt(Math.abs(lng))
  r += (20*Math.sin(6*lng*_MCK_PI) + 20*Math.sin(2*lng*_MCK_PI)) * 2/3
  r += (20*Math.sin(lat*_MCK_PI)   + 40*Math.sin(lat/3*_MCK_PI)) * 2/3
  r += (160*Math.sin(lat/12*_MCK_PI) + 320*Math.sin(lat*_MCK_PI/30)) * 2/3
  return r
}
function _mckDLng(lng, lat) {
  let r = 300 + lng + 2*lat + 0.1*lng*lng + 0.1*lng*lat + 0.1*Math.sqrt(Math.abs(lng))
  r += (20*Math.sin(6*lng*_MCK_PI) + 20*Math.sin(2*lng*_MCK_PI)) * 2/3
  r += (20*Math.sin(lng*_MCK_PI)   + 40*Math.sin(lng/3*_MCK_PI)) * 2/3
  r += (150*Math.sin(lng/12*_MCK_PI) + 300*Math.sin(lng/30*_MCK_PI)) * 2/3
  return r
}
function wgs2gcjMck(lng, lat) {
  if (_mckOutCN(lng, lat)) return { lng, lat }
  const radLat = lat / 180 * _MCK_PI
  let magic = Math.sin(radLat); magic = 1 - _MCK_EE * magic * magic
  const sq = Math.sqrt(magic)
  const dlat = (_mckDLat(lng - 105, lat - 35) * 180) / ((_MCK_A * (1 - _MCK_EE)) / (magic * sq) * _MCK_PI)
  const dlng = (_mckDLng(lng - 105, lat - 35) * 180) / (_MCK_A / sq * Math.cos(radLat) * _MCK_PI)
  return { lng: lng + dlng, lat: lat + dlat }
}

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

// 把 GeoJSON 限高区解析为多边形数组（附带 maxAlt、name 字段）
function buildHeightLimitPolys(geojson) {
  const polys = []
  for (const f of (geojson.features || [])) {
    const g = f.geometry; if (!g) continue
    const maxAlt = f.properties?.max_altitude ?? 120
    const name   = f.properties?.name || '限高区'
    const rings = g.type === 'Polygon' ? [g.coordinates[0]]
      : g.type === 'MultiPolygon' ? g.coordinates.map(c => c[0]) : []
    for (const ring of rings) {
      const pts = ring.map(c => ({ lng: c[0], lat: c[1] }))
      if (pts.length >= 3) polys.push({ ...polyMeta(pts), maxAlt, name })
    }
  }
  return polys
}
const HEIGHT_LIMIT_POLYS = buildHeightLimitPolys(MOCK_HEIGHT_LIMIT_ZONES)

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

const NF_MARGIN = 150     // 禁飞区安全缓冲（米）
// 仅"非常低"的建筑可从上方飞越；高于此阈值的建筑一律水平绕行（与飞行限高无关）
const BUILD_OVERFLY = 20  // 可越顶的最大建筑高度（米）

function mockPlanPath(params) {
  const {
    start, end, waypoints = [], drone_speed = 15,
    avoid_buildings = true, avoid_no_fly = true, avoid_height_limit = true,
    cruise_alt = 120,
  } = params
  if (!start || !end) {
    return { is_feasible: false, warnings: ['缺少起终点'], path: [], altitude_profile: [], total_distance: 0, estimated_time: 0 }
  }

  const CEIL = Math.max(Math.min(cruise_alt, 300), 30)  // 用户请求巡航高度
  const doNoFly      = avoid_no_fly !== false
  const doBuild      = avoid_buildings !== false
  const doHeightLim  = avoid_height_limit !== false
  const ctrlPts = [start, ...waypoints, end]

  // ── 0. 起点/途经点/终点落在禁飞区内 → 拒绝规划（任何一点都不行）─
  if (NO_FLY_POLYS.length) {
    const labelOf = (i) => i === 0 ? '起点' : i === ctrlPts.length - 1 ? '终点' : `途经点${i}`
    const blocked_points = []
    ctrlPts.forEach((p, i) => {
      const gcjP = wgs2gcjMck(p.lng, p.lat)
      for (const poly of NO_FLY_POLYS) {
        if (gcjP.lng < poly.minLng || gcjP.lng > poly.maxLng || gcjP.lat < poly.minLat || gcjP.lat > poly.maxLat) continue
        if (pointInPoly(gcjP.lng, gcjP.lat, poly)) {
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
    // 禁飞区 GeoJSON 为 GCJ-02，需将 WGS-84 网格中心转换后再做碰撞检测
    const gcj = wgs2gcjMck(lng, lat)
    let kind = null
    if (doNoFly) {
      for (const poly of NO_FLY_POLYS) {
        if (gcj.lng < poly.minLng - 0.02 || gcj.lng > poly.maxLng + 0.02 ||
            gcj.lat < poly.minLat - 0.02 || gcj.lat > poly.maxLat + 0.02) continue
        if (pointInPoly(gcj.lng, gcj.lat, poly) || distToPoly(gcj.lng, gcj.lat, poly) < NF_MARGIN) { kind = 'no_fly'; break }
      }
    }
    // 建筑：高于"可越顶高度"即视为障碍 → 水平绕行（仅极低矮建筑可越顶）
    if (!kind && doBuild && getBuildingHeight(lng, lat) > BUILD_OVERFLY) kind = 'building'
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

  // 视线串拉（string-pulling）：消除栅格 A* 的 45°/90° 阶梯锯齿。
  // 从当前点尽量直连最远的后续点，只要直线不穿障碍就跳过中间台阶点。
  //
  // 禁飞区检测使用「内部 + 50m 薄缓冲」而非完整 NF_MARGIN（150m）：
  //   · 若使用 0m 缓冲：串拉允许路径贴近区域边缘 → 掠边 → 后续 LOS 全被实体区域阻断
  //     → 阶梯残留 → Chaikin 产生锐角震荡。
  //   · 若使用完整 150m：凸形区域的所有边界点之间的直线都穿入缓冲带 → 串拉完全失效
  //     → 原始阶梯直接交给 Chaikin → 同样产生严重震荡。
  //   · 50m 薄缓冲：阻止贴边捷径，同时允许沿缓冲外沿的合理跳跃，两全其美。
  const LC_NF_MARGIN = 50  // 串拉阶段的最小禁飞区间距（米）
  const lineClear = (a, b) => {
    const d = haversine(a, b)
    const steps = Math.max(1, Math.ceil(d / (cellM * 0.5)))
    for (let s = 1; s < steps; s++) {
      const t = s / steps
      const lng = a.lng + (b.lng - a.lng) * t
      const lat = a.lat + (b.lat - a.lat) * t
      // 建筑障碍：WGS-84 坐标，直接判定
      if (doBuild && getBuildingHeight(lng, lat) > BUILD_OVERFLY) return false
      // 禁飞区：GeoJSON 为 GCJ-02，转换后同时检测内部 + 50m 薄缓冲
      if (doNoFly) {
        const gcjPt = wgs2gcjMck(lng, lat)
        for (const poly of NO_FLY_POLYS) {
          if (gcjPt.lng < poly.minLng - 0.001 || gcjPt.lng > poly.maxLng + 0.001 ||
              gcjPt.lat < poly.minLat - 0.001 || gcjPt.lat > poly.maxLat + 0.001) continue
          if (pointInPoly(gcjPt.lng, gcjPt.lat, poly) || distToPoly(gcjPt.lng, gcjPt.lat, poly) < LC_NF_MARGIN) return false
        }
      }
    }
    return true
  }
  const stringPull = (pts) => {
    if (pts.length <= 2) return pts
    const out = [pts[0]]
    let i = 0
    while (i < pts.length - 1) {
      let j = pts.length - 1
      while (j > i + 1 && !lineClear(pts[i], pts[j])) j--
      out.push(pts[j]); i = j
    }
    return out
  }

  // ── 3. 逐段规划：每段独立 A*+串拉，再按途经点拼接（务必经过每个途经点）─
  //
  // 若起/终点在 NF_MARGIN 缓冲带内（但在区外），其栅格格子会被 blockKind 标为 no_fly，
  // 导致 8 个邻格全被封锁，A* 无法扩展而失败。
  // 解决：BFS 向外找最近的无障碍格作为 A* 的实际出发/到达格，
  // 最终路径首尾仍对齐到精确控制点，不改变用户设定位置。
  function findEscapeCell(cell) {
    if (!blockKind(cell.r, cell.c)) return cell  // 本身就安全
    const queue = [cell]
    const seen = new Set(); seen.add(cell.r * cols + cell.c)
    for (let qi = 0; qi < queue.length; qi++) {
      const { r, c } = queue[qi]
      for (let dr = -1; dr <= 1; dr++) for (let dc = -1; dc <= 1; dc++) {
        if (!dr && !dc) continue
        const nr = r + dr, nc = c + dc
        if (nr < 0 || nc < 0 || nr >= rows || nc >= cols) continue
        const key = nr * cols + nc
        if (seen.has(key)) continue
        seen.add(key)
        if (!blockKind(nr, nc)) return { r: nr, c: nc }  // 找到安全格
        queue.push({ r: nr, c: nc })
      }
    }
    return cell  // 无法逃脱（整个网格都被封锁，极端情形）
  }

  const warnings = []
  let isFeasible = true
  let poly = []
  for (let s = 0; s < ctrlPts.length - 1; s++) {
    const safeS = findEscapeCell(toCell(ctrlPts[s]))
    const safeE = findEscapeCell(toCell(ctrlPts[s + 1]))
    const seg = astarSeg(safeS, safeE)
    let segPts
    if (!seg) {
      isFeasible = false
      warnings.push(`路径段 ${s + 1} 无法绕过障碍（可能被禁飞区完全封闭）`)
      segPts = [ctrlPts[s], ctrlPts[s + 1]]
    } else {
      segPts = seg.map(({ r, c }) => cellCenter(r, c))
      // 段首尾对齐精确控制点（起点/途经点/终点），串拉仅在本段内进行 → 途经点必经
      segPts[0] = { lng: ctrlPts[s].lng, lat: ctrlPts[s].lat }
      segPts[segPts.length - 1] = { lng: ctrlPts[s + 1].lng, lat: ctrlPts[s + 1].lat }
      segPts = stringPull(segPts)
    }
    if (poly.length) segPts = segPts.slice(1)  // 去重接缝（途经点保留在上一段末尾）
    poly = poly.concat(segPts)
  }

  // ── 4. Chaikin 切角柔滑：把 45° 折线变成圆润曲线（不会过冲，杜绝锐角毛刺）─
  // Chaikin 角切割：曲线恒在控制折线凸包内，不会像样条那样在急转处过冲产生尖刺。
  // A* 走廊本身已留足余量（禁飞区 150m、建筑高斯核心），轻微切角不会切入障碍。
  const chaikin = (pts, iters) => {
    let p = pts
    for (let it = 0; it < iters; it++) {
      if (p.length < 3) break
      const out = [p[0]]
      for (let i = 0; i < p.length - 1; i++) {
        const a = p[i], b = p[i + 1]
        out.push({ lng: a.lng * 0.75 + b.lng * 0.25, lat: a.lat * 0.75 + b.lat * 0.25 })
        out.push({ lng: a.lng * 0.25 + b.lng * 0.75, lat: a.lat * 0.25 + b.lat * 0.75 })
      }
      out.push(p[p.length - 1])
      p = out
    }
    return p
  }
  // 按弧长均匀重采样（高度斜坡与配色需要近似等距点）
  const SAMPLE_M = Math.max(36, cellM)
  const resampleM = (pts, S) => {
    if (pts.length < 2) return pts.slice()
    const out = [pts[0]]
    let d = S
    for (let i = 1; i < pts.length; i++) {
      const a = pts[i - 1], b = pts[i]
      const segLen = haversine(a, b)
      if (segLen < 1e-9) continue
      while (d <= segLen) {
        const t = d / segLen
        out.push({ lng: a.lng + (b.lng - a.lng) * t, lat: a.lat + (b.lat - a.lat) * t })
        d += S
      }
      d -= segLen
    }
    out.push(pts[pts.length - 1])
    return out
  }
  let dense = resampleM(chaikin(poly, 5), SAMPLE_M)
  dense[0] = { lng: start.lng, lat: start.lat }
  dense[dense.length - 1] = { lng: end.lng, lat: end.lat }

  // 兜底：Chaikin 平滑后角点可能贴近甚至进入禁飞区边界。
  // 建筑：继续用栅格判定 + 邻点中点方向推离（建筑无精确几何）。
  // 禁飞区：改用实际多边形几何（pointInPoly / distToPoly）：
  //   · 栅格格子中心可能落在区域外 → 漏判；
  //   · 旧的"邻点中点"方向对绕角路径可能指向区域内部 → 越推越深。
  //   正确方向：从质心指向当前点（内部和边缘点均指向外侧）。
  const snapDense = dense.map(p => ({ ...p }))
  const POST_CLEAR_M = 30  // 平滑后要求的最小禁飞区物理间距（米）
  for (let i = 1; i < dense.length - 1; i++) {
    let p = dense[i]
    const ml = mPerDegLng(p.lat)

    // ① 建筑推离（栅格判定，邻点中点方向）
    if (doBuild && blockKind(toCell(p).r, toCell(p).c) === 'building') {
      const prev = snapDense[i - 1], next = snapDense[i + 1]
      let nx = p.lng - (prev.lng + next.lng) / 2, ny = p.lat - (prev.lat + next.lat) / 2
      const L = Math.hypot(nx * ml, ny * MPD) || 1
      nx = (nx * ml) / L; ny = (ny * MPD) / L
      for (let s = 1; s <= 6 && blockKind(toCell(p).r, toCell(p).c) === 'building'; s++) {
        p = { lng: p.lng + nx * (cellM * 0.5) / ml, lat: p.lat + ny * (cellM * 0.5) / MPD }
      }
    }

    // ② 禁飞区推离（实际多边形几何，最多迭代 10 次）
    if (doNoFly && NO_FLY_POLYS.length) {
      let gcjP = wgs2gcjMck(p.lng, p.lat)
      for (let attempt = 0; attempt < 10; attempt++) {
        let badPoly = null
        for (const poly of NO_FLY_POLYS) {
          if (gcjP.lng < poly.minLng - 0.005 || gcjP.lng > poly.maxLng + 0.005 ||
              gcjP.lat < poly.minLat - 0.005 || gcjP.lat > poly.maxLat + 0.005) continue
          if (pointInPoly(gcjP.lng, gcjP.lat, poly) ||
              distToPoly(gcjP.lng, gcjP.lat, poly) < POST_CLEAR_M) { badPoly = poly; break }
        }
        if (!badPoly) break
        // 推力方向：从质心指向当前点（内部和边缘点均向外推）
        let nx = gcjP.lng - badPoly.cx, ny = gcjP.lat - badPoly.cy
        const L = Math.hypot(nx * ml, ny * MPD) || 1
        nx = (nx * ml) / L; ny = (ny * MPD) / L
        p = { lng: p.lng + nx * 30 / ml, lat: p.lat + ny * 30 / MPD }
        gcjP = wgs2gcjMck(p.lng, p.lat)
      }
    }

    dense[i] = p
  }
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
      // 限高区：在区域内时将高度压低至 maxAlt（路径点 WGS-84 → GCJ-02 后与区域比较）
      if (doHeightLim && HEIGHT_LIMIT_POLYS.length) {
        const gcjP = wgs2gcjMck(p.lng, p.lat)
        for (const o of HEIGHT_LIMIT_POLYS) {
          if (gcjP.lng < o.minLng || gcjP.lng > o.maxLng || gcjP.lat < o.minLat || gcjP.lat > o.maxLat) continue
          if (pointInPoly(gcjP.lng, gcjP.lat, o)) {
            alt   = Math.min(alt, o.maxAlt)
            phase = 'height_limit'
            break
          }
        }
      }
      // 贴近禁飞区缓冲 → 红色绕行段（路径点为 WGS-84，需转 GCJ-02 后与区域比较）
      if (phase === 'cruise' && doNoFly) {
        const gcjP = wgs2gcjMck(p.lng, p.lat)
        for (const o of NO_FLY_POLYS) {
          if (gcjP.lng < o.minLng - 0.02 || gcjP.lng > o.maxLng + 0.02 || gcjP.lat < o.minLat - 0.02 || gcjP.lat > o.maxLat + 0.02) continue
          if (distToPoly(gcjP.lng, gcjP.lat, o) < NF_MARGIN * 1.8) { phase = 'no_fly'; nearNoFly = true; break }
        }
      }
      // 正在贴着建筑群绕行 → 紫色段（航线本身已避开建筑格，故检测附近是否有建筑）
      if (phase === 'cruise' && doBuild) {
        const off = 110 / mPerDegLng(p.lat), offY = 110 / MPD
        const near = Math.max(
          getBuildingHeight(p.lng + off, p.lat), getBuildingHeight(p.lng - off, p.lat),
          getBuildingHeight(p.lng, p.lat + offY), getBuildingHeight(p.lng, p.lat - offY),
        )
        if (near > BUILD_OVERFLY) { phase = 'building'; nearBuilding = true }
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

  // 限高区提示：找出路径经过的所有限高区，若用户设置高度超出限高则提醒
  if (doHeightLim && HEIGHT_LIMIT_POLYS.length) {
    const hitZones = new Map()  // name → maxAlt（去重）
    for (const pp of dense) {
      const gcjP = wgs2gcjMck(pp.lng, pp.lat)
      for (const o of HEIGHT_LIMIT_POLYS) {
        if (gcjP.lng < o.minLng || gcjP.lng > o.maxLng || gcjP.lat < o.minLat || gcjP.lat > o.maxLat) continue
        if (pointInPoly(gcjP.lng, gcjP.lat, o) && CEIL > o.maxAlt) {
          if (!hitZones.has(o.name) || hitZones.get(o.name) > o.maxAlt) hitZones.set(o.name, o.maxAlt)
        }
      }
    }
    for (const [name, maxAlt] of hitZones) {
      warnings.push(`航线经过限高区「${name}」，最大飞行高度限制为 ${maxAlt}m（您设置的巡航高度 ${CEIL}m 已自动压低）`)
    }
  }

  if (nearNoFly) warnings.push('已水平绕行禁飞区（保持安全缓冲距离）')
  if (nearBuilding) warnings.push(`已水平绕行建筑群（仅 ${BUILD_OVERFLY}m 以下矮建筑越顶飞越，巡航限高 ${CEIL}m）`)
  if (CEIL > 200) warnings.push(`飞行限高 ${CEIL}m，请确认已获得空域授权`)

  return { is_feasible: isFeasible, total_distance, estimated_time, warnings, path, altitude_profile }
}

// Vite 插件：拦截 /api 请求返回 Mock 数据（无需后端）
function mockApiPlugin() {
  const MOCK_MAP = {
    'GET /api/weather/live': MOCK_WEATHER,
    // 以下已对接真实后端数据库，不再使用 mock，请求透传至后端
    // 'GET /api/zones/no-fly': MOCK_NO_FLY_ZONES,
    // 'GET /api/zones/height-limit': MOCK_HEIGHT_LIMIT_ZONES,
    // 'GET /api/zones/stats': MOCK_ZONE_STATS,
    // 'GET /api/routes/': MOCK_ROUTES,
    // 'GET /api/routes': MOCK_ROUTES,
    // 'GET /api/zones/check-point': { in_no_fly_zone: false, height_limits: [] },
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
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
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
