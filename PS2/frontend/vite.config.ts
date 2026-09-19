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
      // Offline tile caching is parked on licensing grounds, so a cached map can never
      // draw a basemap. Precaching its 1 MB chunk would cost her mobile data to store
      // something offline can't use; let it load from the network when the map is opened.
      // The 24 KiB font is precached deliberately: offline is exactly when she opens the
      // saved journey, and a departure time that reflows when the font arrives is worse
      // than one that never had to.
      injectManifest: {
        globPatterns: ['**/*.{js,css,html,woff2}'],
        globIgnores: ['**/RouteMap-*.js', '**/RouteMap-*.css', '**/maplibre-gl-worker-*.js'],
      },
      // Production builds get a registration script injected automatically, but dev builds
      // do not: without this the worker never installs on :5173, navigator.serviceWorker.ready
      // stays pending, and push reminders cannot be exercised outside a preview build.
      devOptions: { enabled: true, type: 'module', navigateFallback: 'index.html' },
      manifest: {
        name: 'Wobble Journey Companion',
        short_name: 'Wobble',
        description: 'Journey guidance for hospital appointments.',
        theme_color: '#0d6048',
        background_color: '#f4f5f0',
        display: 'standalone',
        icons: [{ src: '/icons/wobble.svg', sizes: 'any', type: 'image/svg+xml', purpose: 'any' }],
      },
    }),
  ],
  // MapLibre starts its worker with { type: 'module' }, so the bundled worker must be ESM.
  worker: { format: 'es' },
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:8000',
      '/openapi.json': 'http://127.0.0.1:8000',
    },
  },
  // `vite preview` does not inherit server.proxy, so a production build served locally
  // could not reach the API at all. Verifying a build is the whole point of preview.
  preview: {
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
