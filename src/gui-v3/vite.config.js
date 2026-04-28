import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import vuetify from 'vite-plugin-vuetify'
import { fileURLToPath, URL } from 'node:url'

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')

  return {
    plugins: [
      vue(),
      vuetify({
        autoImport: true,
        styles: {
          configFile: 'src/assets/settings.scss'
        }
      })
    ],
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url))
      }
    },
    base: '/v2/',
    build: {
      outDir: 'dist',
      assetsDir: 'assets',
      sourcemap: false
    },
    server: {
      port: 8080,
      proxy: {
        // Proxy API calls during development
        '/api': {
          target: env.VUE_APP_TARANIS_NG_CORE_API || env.VITE_APP_TARANIS_NG_CORE_API || 'http://127.0.0.1:8082',
          rewrite: (path) => path,
          changeOrigin: true
        },
        '/sse': {
          target: env.VUE_APP_TARANIS_NG_CORE_SSE || env.VITE_APP_TARANIS_NG_CORE_SSE || 'http://127.0.0.1:8082',
          changeOrigin: true
        }
      }
    },
    define: {
      // Make environment variables available at build time
      'process.env.VUE_APP_TARANIS_NG_URL': JSON.stringify(env.VUE_APP_TARANIS_NG_URL || '$VUE_APP_TARANIS_NG_URL'),
      'process.env.VUE_APP_TARANIS_NG_CORE_API': JSON.stringify(env.VUE_APP_TARANIS_NG_CORE_API || '$VUE_APP_TARANIS_NG_CORE_API'),
      'process.env.VUE_APP_TARANIS_NG_CORE_SSE': JSON.stringify(env.VUE_APP_TARANIS_NG_CORE_SSE || '$VUE_APP_TARANIS_NG_CORE_SSE'),
      'process.env.VUE_APP_TARANIS_NG_LOCALE': JSON.stringify(env.VUE_APP_TARANIS_NG_LOCALE || '$VUE_APP_TARANIS_NG_LOCALE'),
      'process.env.VUE_APP_VERSION': JSON.stringify('3.0.0-beta')
    }
  }
})
