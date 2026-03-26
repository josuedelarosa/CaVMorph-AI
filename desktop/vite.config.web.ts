/**
 * Vite config for the **web** build target.
 *
 * Usage:  npm run build:web
 *
 * Outputs to `dist-web/` so it doesn't collide with the Tauri build's `dist/`.
 * The built files are served by the FastAPI backend (PHENOAI_STATIC_DIR).
 */
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  // Sub-path deployment: nginx serves the app at /phenoai-web/.
  // Setting base here makes Vite prefix all asset URLs with /phenoai-web/
  // and sets import.meta.env.BASE_URL to '/phenoai-web/' at runtime.
  base: '/phenoai-web/',
  define: {
    // Ensure __TAURI__ is NOT defined so isTauri evaluates to false
    // (Tauri plugin injects it automatically; in web build it won't exist)
  },
  server: {
    port: 5174,
    host: '127.0.0.1',
    proxy: {
      // Forward API calls to the local FastAPI dev server
      '/health':         'http://127.0.0.1:8008',
      '/model':          'http://127.0.0.1:8008',
      '/infer':          'http://127.0.0.1:8008',
      '/export':         'http://127.0.0.1:8008',
      '/upload':         'http://127.0.0.1:8008',
      '/files':          'http://127.0.0.1:8008',
    },
  },
  build: {
    target: 'esnext',
    outDir: 'dist-web',
    emptyOutDir: true,
  },
})
