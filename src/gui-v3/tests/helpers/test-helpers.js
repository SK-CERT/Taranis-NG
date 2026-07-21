/**
 * Test Helper Utilities for E2E Tests
 *
 * Common functions used across multiple test suites
 */

/**
 * Wait for the backend API to be reachable and responsive.
 *
 * The Playwright webServer boots the backend via test-setup.py, but the dev-server
 * `url` check only confirms the frontend is up — the backend login endpoint may still
 * be warming up. This helper polls until the backend responds or times out.
 * @param {import('@playwright/test').Page} page - Playwright page object
 * @param {number} timeoutMs - max time to wait (default 60s)
 */
export async function waitForBackendReady(page, timeoutMs = 60000) {
    const deadline = Date.now() + timeoutMs
    // Poll the /isalive endpoint via page.request (shares the browser context).
    while (Date.now() < deadline) {
        try {
            const res = await page.request.get('/api/v1/isalive')
            if (res.ok()) return
        } catch {
            // backend not yet reachable — keep polling
        }
        await page.waitForTimeout(1000)
    }
    throw new Error(`Backend did not become ready within ${timeoutMs}ms`)
}

/**
 * Login helper - authenticates user and stores credentials
 * @param {import('@playwright/test').Page} page - Playwright page object
 * @param {string} username - Username (default: 'admin')
 * @param {string} password - Password (default: 'admin')
 */
export async function login(page, username = 'admin', password = 'admin') {
    // Ensure the backend is ready before attempting login — the first test in a
    // run can race the just-booted backend (webServer only checks the frontend URL).
    await waitForBackendReady(page)

    await page.goto('/v2/login')
    await page.locator('[data-test="login-username"] input').fill(username)
    await page.locator('[data-test="login-password"] input').fill(password)
    await page.locator('[data-test="login-submit"]').click()

    // Wait for navigation to complete — allow extra time for the initial login
    // (first test after webServer boot may be slower due to cold backend caches).
    await page.waitForURL(/\/v2\/(dashboard)?$/, { timeout: 30000 })
}

/**
 * Logout helper
 * @param {import('@playwright/test').Page} page - Playwright page object
 */
export async function logout(page) {
    // Click user menu
    await page.click('[data-test="user-menu"]')
    await page.click('[data-test="logout-action"]')

    // Verify redirected to login
    await page.waitForURL('/v2/login')
}

/**
 * Navigate to a configuration section.
 *
 * Users, Roles, ACL and Organizations now live as tabs inside the
 * "Access Management" view, so we open /config and click the matching tab.
 * Other sections still have their own sidebar entry.
 * @param {import('@playwright/test').Page} page - Playwright page object
 * @param {string} section - Section name (e.g., 'Roles', 'Organizations')
 */
export async function navigateToConfig(page, section) {
    // Navigate straight to Access Management instead of /config. /config redirects
    // client-side, and that redirect-during-initial-navigation intermittently makes
    // WebKit throw an internal error; going to the resolved route avoids it.
    await page.goto('/v2/config/access-management')

    // Click the matching tab once it renders. Fall back to a sidebar entry for
    // sections that are not Access Management tabs.
    const tab = page.getByRole('tab', { name: section }).first()
    try {
        await tab.waitFor({ state: 'visible', timeout: 5000 })
        await tab.click()
    } catch {
        await page.getByRole('navigation').getByText(section).click()
    }
}

/**
 * Wait for notification to appear with specific text
 * @param {import('@playwright/test').Page} page - Playwright page object
 * @param {string} expectedText - Expected notification text
 * @param {number} timeout - Timeout in milliseconds (default: 5000)
 */
export async function waitForNotification(page, expectedText, timeout = 5000) {
    const notification = page.locator('.v-snackbar')
    await notification.waitFor({ state: 'visible', timeout })
    await notification.locator(`text=${expectedText}`).waitFor({ timeout })
    return notification
}

/**
 * Wait for notification to disappear
 * @param {import('@playwright/test').Page} page - Playwright page object
 * @param {number} timeout - Timeout in milliseconds (default: 5000)
 */
export async function waitForNotificationDismiss(page, timeout = 5000) {
    const notification = page.locator('.v-snackbar')
    await notification.waitFor({ state: 'hidden', timeout })
}

/**
 * Open a dialog by clicking a button
 * @param {import('@playwright/test').Page} page - Playwright page object
 * @param {string} buttonText - Button text to click (default: 'New')
 */
export async function openDialog(page, buttonText = 'New') {
    await page.getByRole('button', { name: buttonText }).click()
    await page.locator('.v-dialog').waitFor({ state: 'visible' })
}

/**
 * Close a dialog by clicking cancel or close button
 * @param {import('@playwright/test').Page} page - Playwright page object
 */
export async function closeDialog(page) {
    // Try close button first (X icon)
    const closeButton = page.locator('.v-dialog button:has(i.mdi-close)')
    if (await closeButton.isVisible()) {
        await closeButton.click()
    } else {
        // Otherwise try Cancel button
        await page.getByRole('button', { name: 'Cancel' }).click()
    }

    await page.locator('.v-dialog').waitFor({ state: 'hidden' })
}

/**
 * Fill form field by name
 * @param {import('@playwright/test').Page} page - Playwright page object
 * @param {string} fieldName - Field name attribute
 * @param {string} value - Value to fill
 */
export async function fillField(page, fieldName, value) {
    const byName = page.locator(`input[name="${fieldName}"], textarea[name="${fieldName}"]`).first()
    if (await byName.count()) {
        await byName.fill(value)
        return
    }

    // Fallback for Vuetify fields that don't expose stable name attributes.
    const byAriaLabel = page.locator(`input[aria-label*="${fieldName}" i], textarea[aria-label*="${fieldName}" i]`).first()
    if (await byAriaLabel.count()) {
        await byAriaLabel.fill(value)
        return
    }

    // Last resort: fill the first editable field in the active dialog.
    const dialogField = page.locator('.v-dialog:visible input:not([type="hidden"]), .v-dialog:visible textarea').first()
    await dialogField.fill(value)
}

/**
 * Save form in dialog
 * @param {import('@playwright/test').Page} page - Playwright page object
 */
export async function saveDialog(page) {
    await page.getByRole('button', { name: 'Save' }).click()
}

/**
 * Find a row in the active config table by typing its name into the Search box.
 *
 * Why this exists: the config tables are server-side paginated (default 10 per
 * page). When the E2E stack already has seeded rows from earlier runs/specs,
 * a newly-created item lands past page 1 and is invisible to a row locator on
 * page 1 — `expect(row).toBeVisible()` then times out even though the save
 * succeeded. Filtering via the visible Search textbox mirrors real user
 * behavior (you'd search to find your just-created item) and makes the test
 * robust regardless of how many leftover rows the table holds.
 *
 * @param {import('@playwright/test').Page} page - Playwright page object
 * @param {string} name - Exact row name to search for
 * @returns {import('@playwright/test').Locator} The matching row, scoped to the
 *   active panel (Vuetify keeps previous tabs' DOM around).
 */
export async function findRowByName(page, name) {
    // Scope the search box to `.v-window-item--active` so a leftover (closed
    // but not yet unmounted) NewAuthProvider-style dialog — which embeds its
    // own EntitySelectTable with ANOTHER "Search" textbox — does not collide.
    // Vuetify's `<v-dialog v-model="false">` leaves the dialog's DOM in the
    // outgoing transition for a moment; the dialog's Search box is `disabled`
    // but Playwright's `getByRole('textbox', { name })` includes disabled
    // textbox elements in its match set, so without a scope this throws
    // `strict mode violation: ... resolved to 2 elements`.
    //
    // Scoping to `.v-window-item--active` matches only the active Access
    // Management panel's main Search box (the row table it sits above is
    // always inside the active panel). Avoids `getByRole`'s broad match.
    const search = page.locator('.v-window-item--active').getByRole('textbox', { name: 'Search' }).first()
    // Intentionally NO explicit wait here. The search GET the fill() triggers
    // is followed (at every call site) by `expect(row).toBeVisible()` or
    // `expect(row).toHaveCount(0)`, which Playwright AUTO-RETRIES until the row
    // appears / disappears. Auto-retry already syncs on the row-re-render, so
    // an explicit wait would be redundant — and history showed it to be fragile:
    //
    //   - waitForLoadState('networkidle')  → deadlocks (Vite HMR + /sse EventSource
    //     keep the page permanently network-busy; the dev stack is NEVER idle).
    //   - waitForResponse(predicate)       → deadlocks on encoding mismatch:
    //     axios form-encodes query-string spaces as '+', but `decodeURIComponent`
    //     does NOT decode '+' to space (only '%20' decodes), so the predicate
    //     `decodeURIComponent(url).includes('search=E2E SAML_...')` always
    //     rejected the real response that had `search=E2E+SAML_...`.
    //
    // Brief debounce + GET + re-render is well under the default 5 s assertion
    // timeout; auto-retry is the simplest and most robust synchronization here.
    await search.fill(name)
    return page.locator('.v-window-item--active').locator('tbody tr').filter({ hasText: name })
}

/**
 * Delete an item by clicking its delete button
 * @param {import('@playwright/test').Page} page - Playwright page object
 * @param {string} itemIdentifier - Text or locator to identify the item
 */
export async function deleteItem(page, itemIdentifier) {
    // Hover over item to show delete button
    await page.locator(`text=${itemIdentifier}`).hover()

    // Click delete button
    await page.locator(`[aria-label="Delete"]`).click()

    // Confirm deletion
    await page.getByRole('button', { name: 'Delete' }).click()
}

/**
 * Wait for page to load completely
 * @param {import('@playwright/test').Page} page - Playwright page object
 *
 * NOTE: this helper intentionally avoids `waitForLoadState('networkidle')`.
 * The gui-v3 dev stack keeps two long-lived connections permanently open
 * (Vite's HMR WebSocket and the app's /sse EventSource), so the page is NEVER
 * network-idle and `networkidle` hangs to the test timeout. Prefer
 * `waitForResponse(predicate)` for the specific request you are waiting on,
 * or `waitForLoadState('domcontentloaded')` / `waitForSelector(...)`.
 */
export async function waitForPageLoad(page) {
    await page.waitForLoadState('domcontentloaded')
}

/**
 * Check if user has permission by checking if element is visible
 * @param {import('@playwright/test').Page} page - Playwright page object
 * @param {string} selector - Element selector
 */
export async function hasPermission(page, selector) {
    try {
        await page.waitForSelector(selector, { timeout: 2000 })
        return true
    } catch {
        return false
    }
}

/**
 * Create a unique test name with timestamp
 * @param {string} baseName - Base name for the test entity
 */
export function generateTestName(baseName) {
    const timestamp = Date.now()
    return `${baseName}_${timestamp}`
}

/**
 * Take a screenshot for debugging
 * @param {import('@playwright/test').Page} page - Playwright page object
 * @param {string} name - Screenshot name
 */
export async function takeScreenshot(page, name) {
    await page.screenshot({ path: `test-results/screenshots/${name}.png`, fullPage: true })
}
