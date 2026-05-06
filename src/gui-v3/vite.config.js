import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import vuetify from 'vite-plugin-vuetify'
import { fileURLToPath, URL } from 'node:url'

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const dockerEnvDir = fileURLToPath(new URL('../../docker', import.meta.url))
  const env = {
    ...loadEnv(mode, dockerEnvDir, ''),
    ...loadEnv(mode, process.cwd(), '')
  }

  const devPort = Number(env.VITE_PORT || env.PORT || 4444)
  const backendOrigin = env.VITE_DEV_BACKEND_ORIGIN || env.TARANIS_NG_HTTPS_URI || 'http://127.0.0.1:8082'
  const apiBaseUrl = env.VITE_APP_TARANIS_NG_CORE_API || `${backendOrigin}/api/v1`
  const sseBaseUrl = env.VITE_APP_TARANIS_NG_CORE_SSE || `${backendOrigin}/sse`

  const getProxyTarget = (url) => {
    try {
      return new URL(url).origin
    } catch {
      return url
    }
  }

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
      port: devPort,
      proxy: {
        // Proxy API calls during development
        '/api': {
          target: getProxyTarget(apiBaseUrl),
          rewrite: (path) => path,
          changeOrigin: true,
          secure: false
        },
        '/sse': {
          target: getProxyTarget(sseBaseUrl),
          changeOrigin: true,
          secure: false
        }
      }
    },
    define:
      mode === 'development'
        ? {}
        : {
            // Embed placeholder strings so 30-envsubst-on-javascript.sh can do
            // runtime substitution in Docker. Not used during `npm run dev`.
            'import.meta.env.VITE_APP_TARANIS_NG_URL': JSON.stringify(env.VITE_APP_TARANIS_NG_URL || '$VITE_APP_TARANIS_NG_URL'),
            'import.meta.env.VITE_APP_TARANIS_NG_CORE_API': JSON.stringify(
              env.VITE_APP_TARANIS_NG_CORE_API || '$VITE_APP_TARANIS_NG_CORE_API'
            ),
            'import.meta.env.VITE_APP_TARANIS_NG_CORE_SSE': JSON.stringify(
              env.VITE_APP_TARANIS_NG_CORE_SSE || '$VITE_APP_TARANIS_NG_CORE_SSE'
            ),
            'import.meta.env.VITE_APP_TARANIS_NG_LOCALE': JSON.stringify(env.VITE_APP_TARANIS_NG_LOCALE || '$VITE_APP_TARANIS_NG_LOCALE'),
            'import.meta.env.VITE_APP_VERSION': JSON.stringify(env.VITE_APP_VERSION || '3.0.0-beta')
          }
  }
})
