import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
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
    rollupOptions: {
      output: {
        manualChunks: {
          excalidraw: ['@excalidraw/excalidraw'],
        },
      },
    },
  },
  server: {
    host: 'localhost',
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
      }
    }
  }
})
