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
            // boot/rebuild the E2E Docker stack. The `url` probe is essential: without it
            // Playwright could RE-RUN test-setup mid-test, whose `down -v` wipes the postgres
            // volume while tests run (the recurring 'Could not connect to X node.' cause). With
            // `url`, Playwright reuses the running stack if isalive responds (see playwright.config.js).
            //
            // scripts/test-setup.py is the cross-platform setup; use `python` on win32
            // (no python3 alias there). See playwright.config.js for the full rationale.
            command: process.platform === 'win32' ? 'python ../../scripts/test-setup.py' : 'python3 ../../scripts/test-setup.py',
            url: `http://127.0.0.1:${process.env.E2E_CORE_PORT || '8090'}/api/v1/isalive`,
            reuseExistingServer: true,
            timeout: 120 * 1000
        },
        {
            // Vite dev server proxies /api and /sse to the E2E core. Use E2E_CORE_PORT
            // (default 8090, see docker/.env.e2e) so the test stack doesn't collide with a
            // production stack's published ports. Override via the real env if needed.
            command: `VITE_DEV_BACKEND_ORIGIN=http://127.0.0.1:${process.env.E2E_CORE_PORT || '8090'} VITE_APP_TARANIS_NG_CORE_API=http://127.0.0.1:${process.env.E2E_CORE_PORT || '8090'}/api/v1 VITE_APP_TARANIS_NG_CORE_SSE=http://127.0.0.1:${process.env.E2E_CORE_PORT || '8090'}/sse npm run dev:remote`,
            url: 'http://localhost:4444',
            reuseExistingServer: false,
            timeout: 120 * 1000
        }
    ]
})
