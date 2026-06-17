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

// Mock 路径规划：在起终点之间插值生成航线
function mockPlanPath(params) {
  const { start, end, waypoints = [], drone_speed = 15 } = params
  if (!start || !end) {
    return { is_feasible: false, warnings: ['缺少起终点'], path: [], altitude_profile: [], total_distance: 0, estimated_time: 0 }
  }
  // 合并所有控制点
  const ctrl = [start, ...waypoints, end]
  // 在每段之间插 4 个中间点，让曲线更平滑
  const rawPath = []
  const N = 4
  for (let i = 0; i < ctrl.length - 1; i++) {
    const a = ctrl[i], b = ctrl[i + 1]
    for (let k = 0; k < N; k++) {
      const t = k / N
      rawPath.push({ lng: a.lng + (b.lng - a.lng) * t, lat: a.lat + (b.lat - a.lat) * t })
    }
  }
  rawPath.push({ lng: end.lng, lat: end.lat })

  // 高度剖面：起飞段 15% 爬升, 巡航 70%, 降落 15%
  const CRUISE_ALT = 180
  const n = rawPath.length
  const altitude_profile = rawPath.map((_, i) => {
    const t = i / (n - 1)
    let alt, phase
    if (t < 0.15) { alt = 15 + (CRUISE_ALT - 15) * (t / 0.15); phase = 'ascent' }
    else if (t > 0.85) { alt = 15 + (CRUISE_ALT - 15) * ((1 - t) / 0.15); phase = 'descent' }
    else { alt = CRUISE_ALT; phase = 'cruise' }
    return { index: i, alt: Math.round(alt), phase }
  })

  const path = rawPath.map((p, i) => ({ lng: p.lng, lat: p.lat, alt: altitude_profile[i].alt }))

  // 计算总距离（含绕行系数 1.1）
  let total_distance = 0
  for (let i = 0; i < ctrl.length - 1; i++) total_distance += haversine(ctrl[i], ctrl[i + 1])
  total_distance = Math.round(total_distance * 1.1)

  const estimated_time = Math.round(total_distance / (drone_speed * 1000 / 3600))

  return { is_feasible: true, total_distance, estimated_time, warnings: [], path, altitude_profile }
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
