import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Dev proxy: the UI runs on :5173 and forwards API calls to FastAPI on :8000,
// so the draftagent_session cookie is same-origin in dev too.
const backend = 'http://localhost:8000'
const apiPaths = ['/auth', '/threads', '/style', '/runs', '/health']

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: Object.fromEntries(
      apiPaths.map((path) => [path, { target: backend, changeOrigin: true }]),
    ),
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
})
