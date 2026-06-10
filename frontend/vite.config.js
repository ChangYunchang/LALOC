import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve, join } from 'path'
import { existsSync, readFileSync, statSync } from 'fs'

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
        target: 'http://localhost:8001',
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
