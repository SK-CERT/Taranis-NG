import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'
import vuetify from 'vite-plugin-vuetify'

// Vitest defaults NODE_ENV to 'test' only when it is not already set, so an
// ambient NODE_ENV=production (some shells and container images export it)
// silently builds Vue in production mode. There `<script setup>` bindings are
// not exposed on the component instance and dev-only warnings are compiled out,
// which fails hundreds of these tests with misleading errors
// ("wrapper.vm.<x> is not a function", real network calls). The suite is only
// ever meaningful in test mode, so pin it before the plugins read it.
process.env.NODE_ENV = 'test'

/**
 * Vitest Unit/Component Test Configuration
 * See https://vitest.dev/config/
 */
export default defineConfig({
    plugins: [vue(), vuetify({ autoImport: true })],
    resolve: {
        alias: {
            '@': fileURLToPath(new URL('./src', import.meta.url))
        }
    },
    test: {
        environment: 'happy-dom',
        exclude: ['**/node_modules/**', '**/dist/**', 'tests/e2e/**'],
        root: fileURLToPath(new URL('./', import.meta.url)),
        setupFiles: ['./tests/setup.js'],
        globals: true,
        css: false,
        server: {
            deps: {
                inline: ['vuetify']
            }
        },
        coverage: {
            provider: 'v8',
            reporter: ['text', 'json', 'html'],
            exclude: ['node_modules/', 'tests/', '*.config.js', 'dist/']
        }
    }
})
