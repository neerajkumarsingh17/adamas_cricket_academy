import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // Dev-only: avoids needing CORS headers from Django. Vite forwards
      // /api/* to the natively-running backend (see LOCAL-SETUP.md).
      "/api": "http://localhost:8000",
    },
  },
})
