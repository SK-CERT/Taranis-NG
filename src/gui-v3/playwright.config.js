import { defineConfig, devices } from '@playwright/test'

/**
 * Playwright E2E Test Configuration
 * See https://playwright.dev/docs/test-configuration
 */
export default defineConfig({
    testDir: './tests/e2e',

    /* Run tests in files in parallel */
    fullyParallel: true,

    /* Fail the build on CI if you accidentally left test.only in the source code */
    forbidOnly: !!process.env.CI,

    /* Retry on CI only */
    retries: process.env.CI ? 2 : 0,

    /* Single worker everywhere. The suite mutates a single shared backend (create/edit/
       delete of states, associations, orgs, roles, ...); running specs in parallel workers
       makes concurrent writes race and intermittently fail (e.g. a state-entity-type insert
       racing concurrent state-definition writes). CI already ran serially; this makes local
       runs match so results are reproducible. */
    workers: 1,

    /* Reporter to use */
    reporter: [['html'], ['list'], ['json', { outputFile: 'test-results/results.json' }]],

    /* Shared settings for all the projects below */
    use: {
        /* Base URL to use in actions like `await page.goto('/')` */
        baseURL: process.env.BASE_URL || 'http://localhost:4444',

        /* Collect trace when retrying the failed test */
        trace: 'on-first-retry',

        /* Take screenshot on failure */
        screenshot: 'only-on-failure',

        /* Video on failure */
        video: 'on'
    },

    /* Configure projects for major browsers */
    projects: [
        {
            name: 'chromium',
            use: { ...devices['Desktop Chrome'] }
        },

        {
            name: 'firefox',
            use: { ...devices['Desktop Firefox'] }
        },

        {
            name: 'webkit',
            use: { ...devices['Desktop Safari'] }
        }

        /* Test against mobile viewports */
        // {
        //   name: 'Mobile Chrome',
        //   use: { ...devices['Pixel 5'] },
        // },
        // {
        //   name: 'Mobile Safari',
        //   use: { ...devices['iPhone 12'] },
        // },
    ],

    /* Start backend services and frontend dev server before tests */
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
