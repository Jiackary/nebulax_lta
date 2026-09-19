import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'
import { VitePWA } from 'vite-plugin-pwa'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      strategies: 'injectManifest',
      srcDir: 'src',
      filename: 'sw.ts',
      registerType: 'prompt',
      // Production builds get a registration script injected automatically, but dev builds
      // do not: without this the worker never installs on :5173, navigator.serviceWorker.ready
      // stays pending, and push reminders cannot be exercised outside a preview build.
      devOptions: { enabled: true, type: 'module', navigateFallback: 'index.html' },
      manifest: {
        name: 'Nusa Journey Companion',
        short_name: 'Nusa',
        description: 'Journey guidance for hospital appointments.',
        theme_color: '#145a42',
        background_color: '#f6f7f4',
        display: 'standalone',
        icons: [{ src: '/icons/nusa.svg', sizes: 'any', type: 'image/svg+xml', purpose: 'any' }],
      },
    }),
  ],
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:8000',
      '/openapi.json': 'http://127.0.0.1:8000',
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    globals: true,
    css: true,
    exclude: ['e2e/**', 'node_modules/**'],
  },
})
