import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
//
// Redesign worktree config. Pinned to :5174 (strictPort) so we never collide
// with the main demo on :5173. Backend lives on :8001 — start it with
// `PORT=8001 python server.py`. Main repo's vite.config.ts is unchanged.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5174,
    strictPort: true,
    proxy: {
      "/api": "http://localhost:8001",
      "/offer": {
        target: "http://localhost:8001",
        rewrite: () => "/api/offer",
      },
    },
  },
})
