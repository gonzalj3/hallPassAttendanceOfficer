import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// In dev (npm run dev), proxy /api, /auth, /v1 to the local FastAPI
// process. In prod the build serves static assets and Netlify's
// [[redirects]] in netlify.toml proxy the same paths to Railway. The
// frontend code always uses relative URLs -- no env var anywhere.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': { target: 'http://localhost:8000', changeOrigin: true },
      '/auth': { target: 'http://localhost:8000', changeOrigin: true },
      '/v1': { target: 'http://localhost:8000', changeOrigin: true, ws: true },
    },
  },
})
