import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: true, // Allow external connections (0.0.0.0)
    port: 5173,
    strictPort: true,
    // Allow any *.lhr.life domain (localhost.run tunnels)
    allowedHosts: ['.lhr.life', '.localhost.run', '.ngrok-free.app']
  }
})
