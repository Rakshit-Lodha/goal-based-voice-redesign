import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
//
// Local development: Vite on :5173, FastAPI on :8000.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      "/health": "http://localhost:8000",
      "/api": "http://localhost:8000",
      "/offer": {
        target: "http://localhost:8000",
        rewrite: () => "/api/offer",
      },
    },
  },
})
