import { defineConfig, devices } from '@playwright/test'

/**
 * Playwright UI Mode Configuration
 * Minimal config with only Chromium for interactive UI testing
 */
export default defineConfig({
    testDir: './tests/e2e',
    forbidOnly: !!process.env.CI,
    retries: process.env.CI ? 2 : 0,
    workers: 1,
    reporter: [['html'], ['list'], ['json', { outputFile: 'test-results/results.json' }]],

    use: {
        baseURL: process.env.BASE_URL || 'http://localhost:4444',
        trace: 'on-first-retry',
        screenshot: 'only-on-failure',
        video: 'on'
    },

    projects: [
        {
            name: 'chromium',
            use: { ...devices['Desktop Chrome'] }
        }
    ],

    webServer: [
        {
            command: 'bash ../../scripts/test-setup.sh',
            reuseExistingServer: true,
            timeout: 120 * 1000
        },
        {
            command:
                'VITE_DEV_BACKEND_ORIGIN=http://127.0.0.1:8082 VITE_APP_TARANIS_NG_CORE_API=http://127.0.0.1:8082/api/v1 VITE_APP_TARANIS_NG_CORE_SSE=http://127.0.0.1:8082/sse npm run dev:remote',
            url: 'http://localhost:4444',
            reuseExistingServer: false,
            timeout: 120 * 1000
        }
    ]
})
