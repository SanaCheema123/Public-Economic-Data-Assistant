declare const process: { env: Record<string, string | undefined> }
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': { target: process.env.VITE_BACKEND_PROXY || 'http://127.0.0.1:8000', changeOrigin: true },
      '/health': { target: process.env.VITE_BACKEND_PROXY || 'http://127.0.0.1:8000', changeOrigin: true }
    }
  },
  build: { sourcemap: false, target: 'es2022' },
  test: { environment: 'jsdom', setupFiles: './src/test/setup.ts', css: true }
})
