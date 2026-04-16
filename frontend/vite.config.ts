import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, '.', '');
  const backendUrl = env.VITE_API_BASE_URL || 'http://localhost:8000';

  return {
    plugins: [react()],
    define: {
      'process.env': {},
    },
    optimizeDeps: {
      include: ['@excalidraw/excalidraw'],
    },
    build: {
      chunkSizeWarningLimit: 2000,
      cssMinify: true,
      cssCodeSplit: true,
      rollupOptions: {
        output: {
          manualChunks: {
            'react-vendor': ['react', 'react-dom', 'react-router-dom'],
            excalidraw: ['@excalidraw/excalidraw'],
            yjs: ['yjs', 'y-websocket'],
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
        },
      },
    },
    test: {
      environment: 'jsdom',
      globals: true,
      include: ['src/**/*.test.ts', 'src/**/*.test.tsx'],
    },
  };
});
