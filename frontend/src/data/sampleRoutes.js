/**
 * 共享示例航线数据
 *
 * 所有航线均含完整 altitude_profile（爬升/巡航/下降/建筑避让/限高）。
 * 数据来源：按真实起终点坐标，用贝塞尔插值 + 飞行剖面算法预计算后固化。
 *
 * 导出：
 *   SAMPLE_ROUTES  — 供态势大屏 drawRoutes() 渲染（含 route_line / altitude_profile）
 *   DENSITY_ROUTES — 供密度热力分析 / 热点分析使用（保持原始控制点，不重采样）
 */

// ─── 工具函数 ─────────────────────────────────────────────────────────────────

/** 在控制点之间均匀插值，stepsPerSeg = 插值步数 */
function interp(ctrlPts, stepsPerSeg = 8) {
  const out = []
  for (let i = 0; i < ctrlPts.length - 1; i++) {
    const [x1, y1] = ctrlPts[i]
    const [x2, y2] = ctrlPts[i + 1]
    const startK = i === 0 ? 0 : 1
    for (let k = startK; k <= stepsPerSeg; k++) {
      const f = k / stepsPerSeg
      out.push([
        parseFloat((x1 + (x2 - x1) * f).toFixed(6)),
        parseFloat((y1 + (y2 - y1) * f).toFixed(6)),
      ])
    }
  }
  return out
}

/** 计算折线总距离（米） */
function calcDist(pts) {
  let d = 0
  for (let i = 1; i < pts.length; i++) {
    const [x1, y1] = pts[i - 1], [x2, y2] = pts[i]
    const dx = (x2 - x1) * 111320 * Math.cos(y1 * Math.PI / 180)
    const dy = (y2 - y1) * 111320
    d += Math.sqrt(dx * dx + dy * dy)
  }
  return Math.round(d)
}

/**
 * 根据控制点和飞行参数构建完整航线对象
 * @param {object} def
 * @param {number}   def.id
 * @param {string}   def.name
 * @param {string}   def.color
 * @param {number[][]} def.ctrlPts  — 控制点 [[lng,lat],...]
 * @param {number}   def.w          — 密度权重 0~1
 * @param {string}   [def.status]
 * @param {Array}    [def.special]  — 特殊段 [{start,end,phase,alt}]
 *    phase: 'building' 建筑避让（高飞）| 'height_limit' 限高区（低飞）
 */
function buildRoute({ id, name, color, ctrlPts, w, status = 'active', special = [] }) {
  // 巡航高度按权重分级
  const ca = w >= 0.75 ? 150 : w >= 0.55 ? 130 : w >= 0.40 ? 120 : 110

  const allPts = interp(ctrlPts)
  const n = allPts.length
  const ASCENT_R = 0.13   // 前13%爬升
  const DESCENT_R = 0.13  // 后13%下降

  const altitude_profile = allPts.map((_, i) => {
    const t = i / Math.max(n - 1, 1)

    // 爬升段（sin缓入）
    if (t <= ASCENT_R) {
      const a = t / ASCENT_R
      return { index: i, alt: Math.round(20 + (ca - 20) * Math.sin(a * Math.PI / 2)), phase: 'ascent' }
    }
    // 下降段（sin缓出）
    if (t >= 1 - DESCENT_R) {
      const a = (1 - t) / DESCENT_R
      return { index: i, alt: Math.round(20 + (ca - 20) * Math.sin(a * Math.PI / 2)), phase: 'descent' }
    }
    // 特殊段（建筑避让 / 限高区）
    for (const seg of special) {
      if (t >= seg.start && t <= seg.end) {
        return { index: i, alt: seg.alt, phase: seg.phase }
      }
    }
    // 正常巡航
    return { index: i, alt: ca, phase: 'cruise' }
  })

  const totalDist = calcDist(allPts)

  return {
    id,
    name,
    color,
    w,
    pts: allPts,          // 插值后的点，供 drawRoutes 渲染
    status,
    enterprise: '广州低空物流系统',
    responsible_person: '系统预设',
    total_distance: totalDist,
    estimated_time: Math.round(totalDist / 15),   // 均速 15m/s
    route_line: { type: 'LineString', coordinates: allPts },
    altitude_profile,
    waypoints: ctrlPts.map(([lng, lat]) => ({ lng, lat, alt: ca })),
  }
}

// ─── 9 条广州示例航线定义 ────────────────────────────────────────────────────
// 颜色、权重、特殊段均与 DensityContour 热力分析保持一致

const ROUTE_DEFS = [
  {
    id: 1, name: '番禺→天河干线', color: '#3b82f6', w: 0.82, status: 'active',
    ctrlPts: [[113.2671,23.0900],[113.2900,23.0980],[113.3100,23.1050],[113.3245,23.1201]],
    // 中段穿越天河高密度建筑群，抬升到 190m 越顶
    special: [{ start: 0.37, end: 0.57, phase: 'building', alt: 190 }],
  },
  {
    id: 2, name: '白云→天河横线', color: '#8b5cf6', w: 0.60, status: 'active',
    ctrlPts: [[113.2994,23.1540],[113.3100,23.1380],[113.3245,23.1201],[113.3400,23.1050]],
    // 珠江新城附近存在限高区，压至 80m 飞行
    special: [{ start: 0.30, end: 0.52, phase: 'height_limit', alt: 80 }],
  },
  {
    id: 3, name: '黄埔→白云线', color: '#10b981', w: 0.50, status: 'active',
    ctrlPts: [[113.3580,23.1050],[113.3400,23.1201],[113.3245,23.1201],[113.3100,23.1050]],
  },
  {
    id: 4, name: '南沙→黄埔线', color: '#f59e0b', w: 0.32, status: 'planned',
    ctrlPts: [[113.3900,23.1380],[113.3700,23.1300],[113.3580,23.1050],[113.3400,23.0900]],
  },
  {
    id: 5, name: '荔湾→天河线', color: '#ec4899', w: 0.48, status: 'active',
    ctrlPts: [[113.2671,23.1380],[113.2800,23.1250],[113.3100,23.1201],[113.3245,23.1050]],
    // 起飞后进入历史城区限高带，需压至 70m
    special: [{ start: 0.15, end: 0.36, phase: 'height_limit', alt: 70 }],
  },
  {
    id: 6, name: '越秀纵向线', color: '#06b6d4', w: 0.75, status: 'active',
    ctrlPts: [[113.3100,23.0750],[113.3100,23.1050],[113.3100,23.1380],[113.3100,23.1600]],
    // 越秀中段高层建筑密集，抬升 200m
    special: [{ start: 0.39, end: 0.59, phase: 'building', alt: 200 }],
  },
  {
    id: 7, name: '白云横向线', color: '#f97316', w: 0.38, status: 'planned',
    ctrlPts: [[113.2500,23.1050],[113.2671,23.1050],[113.2994,23.1050],[113.3245,23.1050]],
  },
  {
    id: 8, name: '天河→黄埔线', color: '#64748b', w: 0.27, status: 'planned',
    ctrlPts: [[113.3245,23.1201],[113.3400,23.1380],[113.3580,23.1500],[113.3800,23.1600]],
  },
  {
    id: 9, name: '番禺→天河南线', color: '#dc2626', w: 0.44, status: 'active',
    ctrlPts: [[113.2994,23.0750],[113.3100,23.0900],[113.3245,23.1050],[113.3400,23.1201]],
  },
]

// ─── 导出 ─────────────────────────────────────────────────────────────────────

/** 态势大屏 / drawRoutes 用：包含插值路径 + 完整高度剖面 */
export const SAMPLE_ROUTES = ROUTE_DEFS.map(buildRoute)

/**
 * 密度热力分析 / 热点分析用：保留原始控制点（不重采样），避免热力过采样
 * id 为 0~8（与现有 HotspotAnalysis routeIds 对应）
 */
export const DENSITY_ROUTES = ROUTE_DEFS.map(({ name, color, w, ctrlPts }, i) => ({
  id: i,
  name,
  color,
  w,
  pts: ctrlPts,
}))
