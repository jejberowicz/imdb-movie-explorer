import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

// In development, /api goes to the Flask API, as nginx does in Docker: front and API share the origin.
const apiTarget = process.env.VITE_API_PROXY ?? 'http://localhost:8000'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': { target: apiTarget, changeOrigin: true, rewrite: (path) => path.replace(/^\/api/, '') },
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    restoreMocks: true,
  },
})
