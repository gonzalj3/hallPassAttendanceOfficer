import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Dev: proxy backend routes to localhost:8000. Prod: Netlify proxies
// the same paths to Railway via netlify.toml. Frontend code uses
// relative URLs only.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3100,
    proxy: {
      '/api': { target: 'http://localhost:8000', changeOrigin: true },
      '/auth': { target: 'http://localhost:8000', changeOrigin: true },
      '/v1': { target: 'http://localhost:8000', changeOrigin: true, ws: true },
    },
  },
})
