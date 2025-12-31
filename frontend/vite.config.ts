import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  // 加载环境变量
  const env = loadEnv(mode, '.', '')

  // 获取后端地址
  const backendUrl = env.VITE_API_BASE_URL || 'http://localhost:8000'

  return {
    plugins: [react()],
    define: {
      // Excalidraw 需要这些全局定义
      'process.env': {},
    },
    optimizeDeps: {
      // 预构建 Excalidraw 依赖
      include: ['@excalidraw/excalidraw'],
    },
    build: {
      // 增加 chunk 大小警告阈值（Excalidraw 较大）
      chunkSizeWarningLimit: 2000,
      cssMinify: true,      // CSS 压缩
      cssCodeSplit: true,   // CSS 代码分割
      rollupOptions: {
        output: {
          manualChunks: {
            'react-vendor': ['react', 'react-dom', 'react-router-dom'],
            'excalidraw': ['@excalidraw/excalidraw'],
            'yjs': ['yjs', 'y-websocket'],
          },
        },
      },
    },
    css: {
      devSourcemap: true,
    },
    server: {
      host: 'localhost',
      port: 5173,
      proxy: {
        '/api': {
          target: backendUrl,
          changeOrigin: true,
        },
        '/ws': {
          target: backendUrl.replace('http', 'ws'),
          ws: true,
        }
      }
    }
  }
})
