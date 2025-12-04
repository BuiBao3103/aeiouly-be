import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, '.', '')
  // VITE_API_URL can be: http://localhost:8000/api/v1
  // Proxy target needs base URL only: http://localhost:8000
  const apiUrl = env.VITE_API_URL || 'http://localhost:8000/api/v1'
  // Remove /api/v1 or /api from the end to get base URL
  const target = apiUrl.replace(/\/api\/v1$/, '').replace(/\/api$/, '') || 'http://localhost:8000'

  return {
  plugins: [react()],
    server: {
      proxy: {
        '/api/v1': {
          target,
          changeOrigin: true,
        },
        '/online/ws': {
          target,
          ws: true,
          changeOrigin: true,
        },
      },
    },
  }
})
