import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['apple-touch-icon.png', 'pwa-192.png', 'pwa-512.png'],
      manifest: {
        name: 'Jewish Coaching — BSD',
        short_name: 'BSD Coach',
        description: 'Jewish Coaching with the BSD method',
        theme_color: '#2E3A56',
        background_color: '#F0F1F3',
        display: 'standalone',
        orientation: 'portrait-primary',
        scope: '/',
        start_url: '/',
        icons: [
          { src: '/pwa-192.png', sizes: '192x192', type: 'image/png', purpose: 'any' },
          { src: '/pwa-512.png', sizes: '512x512', type: 'image/png', purpose: 'any' },
          { src: '/pwa-512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
        ],
      },
      workbox: {
        globPatterns: ['**/*.{js,css,html,ico,png,svg,woff2}'],
      },
      devOptions: {
        enabled: false,
      },
    }),
  ],
  server: {
    host: true, // Allow external connections (0.0.0.0)
    port: 5173,
    strictPort: true,
    // Allow any *.lhr.life domain (localhost.run tunnels)
    allowedHosts: ['.lhr.life', '.localhost.run', '.ngrok-free.app']
  }
})
