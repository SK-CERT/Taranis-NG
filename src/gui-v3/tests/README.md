# Testing Guide - Taranis-NG Vue 3 GUI

**Last Updated:** April 28, 2026

## Overview

The Vue3 GUI test suite lives under `src/gui-v3/tests/` and currently covers:

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
├── e2e/
│   ├── navigation.spec.js
│   ├── organizations.spec.js
│   └── roles.spec.js
├── fixtures/
│   └── data.json
├── helpers/
│   ├── mock-api.js
│   ├── mount-helpers.js
│   ├── store-helpers.js
│   └── test-helpers.js
├── unit/
│   ├── ActionButton.spec.js
│   ├── analyze.api.spec.js
│   ├── api-service.spec.js
│   ├── App.spec.js
│   ├── assess.store.spec.js
│   ├── AttributeComponents.spec.js
│   ├── AttributeContainer.spec.js
│   ├── auth.store.spec.js
│   ├── BaseToolbarFilter.spec.js
│   ├── CalculatorCVSS.spec.js
│   ├── config.store.spec.js
│   ├── ContentDataSSE.spec.js
│   ├── cvss-utils.spec.js
│   ├── DeleteConfirmationDialog.spec.js
│   ├── NewReportItemSSE.spec.js
│   ├── NotificationSnackbar.spec.js
│   ├── useAttributes.spec.js
│   ├── useAuth.spec.js
│   └── useSSE.spec.js
└── README.md
```

## What Is Currently Covered

### E2E Coverage

Current Playwright specs cover:

- **Navigation and routing**
- **Organizations CRUD flow**
- **Roles CRUD flow**

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
- uses Chromium, Firefox, and WebKit
- writes HTML and JSON reports
- captures screenshots on failure
- captures video on failure
- enables traces on first retry
- starts two web servers before tests:
  - `bash ../../scripts/test-setup.sh`
  - `npm run dev:remote`

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
