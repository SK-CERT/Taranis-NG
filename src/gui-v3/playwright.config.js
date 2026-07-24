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
        // Setup project: seeds the E2E environment (collectors/presenters/publishers nodes,
        // manual OSINT source, product type, publisher preset) before any other test runs.
        {
            name: 'setup',
            testMatch: /00-config-seed\.spec\.js/,
            use: { ...devices['Desktop Chrome'] }
        },

        {
            name: 'chromium',
            dependencies: ['setup'],
            // The seed spec (00-config-seed) is the setup project's job; it must NOT re-run
            // here — a second run would hit the UniqueViolation (nodes already created) and
            // needlessly purge+recreate seeded data the other specs rely on.
            testIgnore: /00-config-seed\.spec\.js/,
            use: { ...devices['Desktop Chrome'] }
        },

        {
            name: 'firefox',
            dependencies: ['setup'],
            testIgnore: /00-config-seed\.spec\.js/,
            use: { ...devices['Desktop Firefox'] }
        },

        {
            name: 'webkit',
            dependencies: ['setup'],
            testIgnore: /00-config-seed\.spec\.js/,
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
            // boot/rebuild the E2E Docker stack. The `url` probe is essential: without it
            // Playwright can't tell the stack is already up, so when the earlier process
            // that ran test-setup has exited it RE-RUNS test-setup. test-setup starts
            // with `down -v`, which would wipe the postgres volume WHILE tests are running —
            // that mid-test teardown was the real cause of the recurring 'Could not connect to
            // X node.' failures (the POST hit a half-rebuilt backend → 400/500). With `url`,
            // Playwright checks isalive: if 200, it reuses the running stack and never re-runs
            // setup; only if isalive is unreachable does it run setup. reuseExistingServer:true
            // then behaves as documented across repeated VS Code 'Run Tests' clicks.
            //
            // scripts/test-setup.py is the cross-platform (Windows/macOS/Linux) setup; it
            // does the same down -v → up --build → wait-for-readiness sequence the original
            // bash test-setup.sh did, with no shell dependency. See it for the rationale
            // behind the two-stage (host-port + core-DNS) readiness probe on
            // collectors/presenters/publishers (the DNS-lag gap that caused the misleading
            // 'Could not connect to X node.' 500s).
            // Use `python` on win32 (no python3 alias there).
            //
            // timeout: 2 min locally is plenty (warm Docker cache, fast local disks). CI needs
            // much longer: GitHub's ubuntu-latest runner has no Docker layer cache, so the
            // Dockerfile.core build (Python uv/pip installs across 8 RUN steps) runs cold and
            // routinely exceeds 2 min before isalive responds. Give CI 10 min to cover the
            // worst-case cold build + service-readiness wait; reuseExistingServer:true means
            // only the first job in a matrix pays it.
            command: process.platform === 'win32' ? 'python ../../scripts/test-setup.py' : 'python3 ../../scripts/test-setup.py',
            url: `http://127.0.0.1:${process.env.E2E_CORE_PORT || '8090'}/api/v1/isalive`,
            reuseExistingServer: true,
            timeout: process.env.CI ? 600_000 : 120_000
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
