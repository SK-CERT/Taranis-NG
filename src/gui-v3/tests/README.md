# Testing Guide - Taranis-NG Vue 3 GUI

**Last Updated:** July 18, 2026

## Overview

The Vue3 GUI test suite lives under `src/gui-v3/tests/` and covers:

- **E2E tests** with Playwright for end-to-end workflows and routing
- **Unit tests** with Vitest for stores, composables, services, utilities, and selected components
- **Component tests** with Vitest + Vue Test Utils

## Tooling

### Unit / Component Tests

- **Runner:** Vitest
- **Vue support:** `@vue/test-utils`
- **Environment:** `happy-dom`
- **Config:** `vitest.config.js`

### E2E Tests

- **Runner:** Playwright
- **Configs:** `playwright.config.js`, `playwright.ui.config.js`
- **Browsers:** Chromium, Firefox, WebKit
- **Default base URL:** `http://localhost:4444`

## Quick Start

### Install dependencies

```bash
npm install
```

### Install Playwright browsers

```bash
npx playwright install
```

## Test Commands

All commands below are defined in `package.json`.

```bash
# Vitest watch mode
npm test

# Run all unit/component tests once
npm run test:unit

# Open Vitest UI
npm run test:ui

# Run unit/component tests with coverage
npm run test:coverage

# Run Playwright E2E suite
npm run test:e2e

# Run Playwright UI mode
npm run test:e2e:ui

# Run Playwright UI mode bound to localhost only
npm run test:e2e:ui:remote

# Run headed E2E tests
npm run test:e2e:headed

# Run E2E tests in debug mode
npm run test:e2e:debug

# Open the Playwright HTML report
npm run test:e2e:report
```

## Current Test Structure

```text
tests/
├── e2e/                          ← Playwright (cross-browser, end-to-end)
│   ├── 00-config-seed.spec.js    ← the `setup` project: seeds nodes + product type + publisher preset
│   ├── auth.spec.js               ← login / logout / session / redirect-to-login
│   ├── navigation.spec.js         ← cross-cutting sidebar & deep-link routing
│   ├── not-found.spec.js          ← 404 catch-all
│   ├── access-management-shell.spec.js ← Access Management shell (tab strip, deep-links, shared dialog toolbar)
│   ├── roles.spec.js              ← Roles tab CRUD
│   ├── organizations.spec.js      ← Organizations tab CRUD
│   ├── user-status.spec.js        ← Users tab: account status lifecycle via API + login-rejection
│   ├── auth-providers.spec.js     ← Login Methods tab CRUD + slug contract + SAML SP metadata contract
│   ├── security-settings.spec.js  ← Security tab: WebAuthn relying-party settings
│   ├── mfa-enrollment.spec.js     ← self-service MFA (TOTP + passkey) — serial, shares admin's state
│   ├── collectors.spec.js         ← Collectors view (OSINT Sources / Groups / Nodes)
│   ├── presenters.spec.js         ← Presenters view (Product Types / Nodes)
│   ├── publish.spec.js             ← Publish view: confirmation + incomplete-reports confirmation
│   ├── states.spec.js             ← Workflow view → States tab
│   ├── state-workflow.spec.js     ← Workflow view → State Workflow tab (entity-type associations)
│   ├── assess.spec.js             ← Assess view (news-items toolbar)
│   └── assess-badges.spec.js      ← Assess view (badges)
├── fixtures/
│   └── data.json
├── helpers/
│   ├── api-cleanup.js     ← `purgeStatesBestEffort`, `purgeSeedEntitiesBestEffort`
│   ├── api-seed.js         ← `createApiContext`, `createNewsItem`, `createReportItem`, ...
│   ├── mock-api.js
│   ├── mount-helpers.js
│   ├── store-helpers.js
│   └── test-helpers.js     ← `login`, `navigateToConfig`, `openDialog`, `saveDialog`, `generateTestName`, `findRowByName`, ...
├── unit/
│   ├── ... (Vitest specs)
└── README.md
```

### E2E naming convention

The folder mirrors the router's top-level layout — **one spec file per router view**
(`/v2/<view>`), named after the view. Access Management is the one exception
because it packs multiple richly-contentful tabs into one view; there it's
**one file per tab, plus a `-shell` file for the tab strip**. The dedicated
`setup` project is prefixed `00-` so the Playwright `testMatch` / sort order
keeps it first.

A developer who knows the GUI should be able to predict the spec filename
without grepping. When adding a test: find its router view, add to (or create)
the matching spec. For an Access Management tab, add to the per-tab spec (or
create one mirroring `roles.spec.js`); for cross-tab behaviour of the tab strip
itself, add to `access-management-shell.spec.js`.

Known coverage gaps (router views with **no dedicated e2e spec**): Analyze,
Publishers, Remote, Bots, Reports (Report Types + Attributes), Settings, Word
Lists, Data Providers. Add these as new siblings of the existing per-view
specs — see the comparable `collectors.spec.js` / `presenters.spec.js`
templates (shell + dialog + CRUD + unsaved-changes guard).

## What Is Currently Covered

### E2E Coverage

Current Playwright specs cover:

- **Authentication:** login / logout / session persistence / protected-route redirect
- **Navigation & routing:** sidebar, deep-link tabs, browser back/forward, 404
- **Access Management:** the tab strip (`access-management-shell.spec.js`) plus per-tab
  specs for Roles, Organizations, Login Methods identity providers (OIDC/SAML/LDAP
  CRUD + write-only secrets + delete warning + slug contract + SAML SP metadata
  contract), Security (WebAuthn relying-party settings), and Users (account status
  lifecycle + last-admin lockout guard)
- **Self-service MFA:** TOTP enroll/disable and passkey registration via a virtual
  authenticator (serial; shares the admin's TOTP/passkey state across tests)
- **Collectors / Presenters:** card-grid tab strip, dialog toolbar, CRUD, unsaved-changes guard
- **Workflow:** States tab CRUD, State Workflow tab (entity-type associations)
- **Assess:** news-items toolbar + filter chips + multi-select; badges
- **Publish:** publish-confirmation dialog and incomplete-reports confirmation (`publish.spec.js`)
- **Setup:** `00-config-seed.spec.js` seeds nodes + product type + publisher preset
  for the publish specs (runs as the `setup` project before all others)

### Unit / Component Coverage

Current Vitest coverage includes:

- **Stores:** auth, assess, config
- **Composables:** useAuth, useAttributes, useSSE
- **API/service layer:** analyze API, api_service
- **App-level behavior:** `App.vue`, SSE-related behavior
- **Shared UI components:** `ActionButton`, `BaseToolbarFilter`, `NotificationSnackbar`, `DeleteConfirmationDialog`
- **Attribute system:** `AttributeContainer`, `AttributeComponents`
- **Utilities:** CVSS helpers

## Configuration Notes

### Vitest

`vitest.config.js` currently uses:

- `happy-dom`
- alias `@ -> ./src`
- exclusion of `tests/e2e/**`
- V8 coverage reporters: `text`, `json`, `html`

### Playwright

`playwright.config.js` currently:

- runs tests from `./tests/e2e`
- uses Chromium, Firefox, and WebKit (each depends on the `setup` project)
- writes HTML and JSON reports
- captures screenshots on failure
- captures video on failure
- enables traces on first retry
- runs a single worker (`workers: 1`) because the suite mutates one shared
  backend (states, orgs, roles, ...) — parallel workers race concurrent writes
- starts two web servers before tests:
    - **backend stack:** `python3 ../../scripts/test-setup.py` (`python` on Windows) —
      the cross-platform setup script. It tears down any previous E2E stack + its
      postgres volume, seeds missing `docker/secrets/*.txt` from their `.example`,
      starts postgres/redis/core/collectors/presenters/publishers, and waits for
      readiness on both the host port AND via the core container's Docker DNS resolution.
    - **frontend dev server:** `npm run dev:remote` (Vite on `http://localhost:4444`)

`playwright.ui.config.js` is the lighter UI-mode variant and runs Chromium only.

## Helper Utilities

`tests/helpers/test-helpers.js` currently provides helpers such as:

- `login(page, username, password)`
- `logout(page)`
- `navigateToConfig(page, section)`
- `waitForNotification(page, expectedText, timeout)`
- `waitForNotificationDismiss(page, timeout)`
- `openDialog(page, buttonText)`
- `closeDialog(page)`
- `fillField(page, fieldName, value)`
- `saveDialog(page)`
- `deleteItem(page, itemIdentifier)`
- `waitForPageLoad(page)`
- `hasPermission(page, selector)`
- `generateTestName(baseName)`
- `takeScreenshot(page, name)`

## Running a Single Test File

### Vitest

```bash
npx vitest tests/unit/useAuth.spec.js
```

### Playwright

```bash
npx playwright test tests/e2e/roles.spec.js
```

## Test Output

Generated output directories/files:

- `coverage/` — Vitest coverage output
- `test-results/` — Playwright screenshots, videos, traces, and JSON output
- Playwright HTML report — opened with `npm run test:e2e:report`

## Notes

- This document describes the current test suite layout and commands, not target coverage goals.
- If you add a new test file or helper, update this README in the same change.
