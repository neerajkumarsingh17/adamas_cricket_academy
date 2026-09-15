import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // Exposes the dev server on the LAN (e.g. http://<your-ip>:5173) so
    // other devices on the same Wi-Fi can reach it, not just localhost.
    host: true,
    proxy: {
      // Dev-only: avoids needing CORS headers from Django. Vite forwards
      // /api/* to the natively-running backend (see LOCAL-SETUP.md).
      "/api": "http://localhost:8000",
    },
  },
})
