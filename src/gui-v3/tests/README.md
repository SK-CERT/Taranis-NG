# Vue 3 GUI testing

The Vue 3 test suite combines Vitest component/unit tests with Playwright
browser workflows.

Run commands from `src/gui-v3` after installing the locked dependencies:

```bash
npm ci
```

## Unit and component tests

Vitest uses `happy-dom`, Vue Test Utils, the `@` source alias, and Vuetify
component support. End-to-end files are excluded from the Vitest run.

```bash
# Watch mode
npm test

# One complete run
npm run test:unit

# Interactive Vitest UI
npm run test:ui

# V8 coverage in text, JSON, and HTML formats
npm run test:coverage

# One file
npx vitest run tests/unit/useAuth.spec.js
```

Unit coverage includes stores, API wrappers, authentication and permissions,
route/tab isolation, Assess behavior, My Assets, OSINT bulk operations,
notifications, SSE, attributes, CVSS, dialogs, and shared components.

## End-to-end tests

Install the Playwright browsers once:

```bash
npx playwright install
```

The default Playwright configuration:

- starts a dedicated `taranis-e2e` Docker backend;
- starts the Vue 3 Vite server on `http://localhost:4444`;
- seeds required nodes, sources, product types, and presets;
- runs one worker because the specs share and mutate one backend;
- exercises Chromium, Firefox, and WebKit; and
- records traces on the first retry plus screenshots and video on failure.

The E2E setup removes only the dedicated `taranis-e2e` containers and volumes.
It does not use the normal Taranis NG Compose project or its PostgreSQL volume.

### Execution model

`playwright.config.js` defines a setup project that runs
`tests/e2e/00-config-seed.spec.js`. The Chromium, Firefox, and WebKit projects
depend on that setup project, so the shared backend data is prepared before the
browser workflows begin. The browser projects do not run the seed specification
again.

The configuration starts the backend through `scripts/test-setup.sh` and the
frontend through `npm run dev:remote`. Playwright can reuse an already running
frontend outside CI. Keep the suite at one worker unless its shared backend
state and cleanup model are changed.

```bash
# Complete browser suite
npm run test:e2e

# Chromium-only interactive UI
npm run test:e2e:ui

# Interactive UI bound to 127.0.0.1:9323
npm run test:e2e:ui:remote

# Headed or debug execution
npm run test:e2e:headed
npm run test:e2e:debug

# Open the generated HTML report
npm run test:e2e:report

# One specification
npx playwright test tests/e2e/roles.spec.js
```

Set `BASE_URL` to test an already reachable frontend instead of the default
URL. The automated configuration still manages its declared web servers unless
the corresponding config is changed.

Current browser workflows cover authentication, navigation, 404 handling,
Assess, access management, roles, organizations, collectors, presenters,
workflow states, selected Publish behavior, and My Assets permission and CRUD
paths.

### Continuous integration

`.github/workflows/gui-v3-tests.yml` runs the suite on Chromium and Firefox as
two parallel jobs, after lint and the unit tests pass. Its path filter also
covers `src/core`, `src/collectors`, `src/presenters`, `src/publishers`,
`src/shared`, and `docker`, because the suite drives the real backend.

Three differences from a local run:

- `docker/secrets/*.txt` is gitignored, so the job first copies each committed
  `.txt.example` into place. They are throwaway values; the same file feeds both
  the containers and the seed specification, so the two always agree.
- Every job installs Chromium in addition to its own browser. The setup project
  is pinned to `devices['Desktop Chrome']` and each browser project depends on
  it, so the seed always runs in Chromium. The same applies locally: running
  `npx playwright test --project=firefox` needs Chromium installed too.
- The job runs `scripts/test-setup.sh` as its own step before Playwright starts.
  The `webServer` entry that normally runs that script allows 120 seconds, which
  does not cover a cold `docker compose up --build`. Since that entry sets
  `reuseExistingServer` with an `isalive` probe, Playwright finds the stack
  already running and does not start it a second time.

A failing job prints the backend container logs and uploads the Playwright HTML
report; `test-results/` with its screenshots, videos, and traces is uploaded too.

### Test support modules

The reusable support code is grouped by responsibility:

- `tests/helpers/test-helpers.js` provides common browser actions, including
  login, navigation, dialogs, notifications, deletion, and screenshots.
- `tests/helpers/api-seed.js` creates and removes the API records required by
  browser workflows.
- `tests/helpers/api-cleanup.js` creates the cleanup API context and purges
  state from the dedicated test backend.
- `tests/helpers/mock-api.js` provides configurable API responses and errors for
  unit tests.
- `tests/helpers/mount-helpers.js` mounts components with the standard plugins
  and test i18n instance.
- `tests/helpers/store-helpers.js` creates and resets Pinia state for unit tests.

Use these modules instead of duplicating setup or UI interaction logic in new
specifications. The configuration files and helper sources remain the source of
truth for their exact options and exported functions.

## Generated output

- `coverage/` — Vitest coverage
- `test-results/` — Playwright JSON results and failure artifacts
- `playwright-report/` — Playwright HTML report

These paths are ignored by Git.
