/**
 * Test Helper Utilities for E2E Tests
 *
 * Common functions used across multiple test suites
 */

/**
 * Wait for the backend API to be reachable and responsive.
 *
 * The Playwright webServer boots the backend via test-setup.sh, but the dev-server
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
    // Pair the click with the request it has to produce. Waiting only on the URL turns a login
    // that was refused, or lost to a dev-server reload, into an opaque 30s "waiting for
    // navigation" with the form still filled on screen and the status code never seen.
    const [response] = await Promise.all([
        page.waitForResponse((res) => res.url().includes('/auth/login') && res.request().method() === 'POST'),
        page.locator('[data-test="login-submit"]').click()
    ])
    if (!response.ok()) {
        throw new Error(`Login for ${username} returned HTTP ${response.status()}`)
    }

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
 *
 * Scoped to the visible dialog, not the page. A page-wide "Save" also matches any
 * Save button on the view behind the overlay, which is a strict-mode violation the
 * moment one exists — and until then it can silently click the wrong one.
 *
 * @param {import('@playwright/test').Page} page - Playwright page object
 */
export async function saveDialog(page) {
    await page.locator('.v-dialog:visible').getByRole('button', { name: 'Save' }).click()
}

/**
 * The rendered content panel of a tabbed config view (Access Management, …).
 *
 * These views used to keep every tab mounted inside a `<v-window>` and this scope
 * was `.v-window-item--active`. They now render exactly one panel via
 * `<component :is>` (see AccessManagementView.vue), so that class no longer exists
 * anywhere in the page and every locator built on it silently matched nothing.
 *
 * `.v-main` is the equivalent scope: it holds the tab bar plus the single live
 * panel, and — crucially — it excludes dialogs. Vuetify teleports every overlay
 * into a `.v-overlay-container` appended to `document.body` (see
 * vuetify/composables/teleport), so a dialog's own EntitySelectTable "Search" box
 * or data table can never collide with the panel's.
 *
 * @param {import('@playwright/test').Page} page - Playwright page object
 * @returns {import('@playwright/test').Locator} The page-content scope
 */
export function activePanel(page) {
    return page.locator('.v-main')
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
 *   page content (see activePanel).
 */
export async function findRowByName(page, name) {
    // Scope the search box to the page content so a leftover (closed but not yet
    // unmounted) NewAuthProvider-style dialog — which embeds its own
    // EntitySelectTable with ANOTHER "Search" textbox — does not collide.
    // Vuetify's `<v-dialog v-model="false">` leaves the dialog's DOM in the
    // outgoing transition for a moment; the dialog's Search box is `disabled`
    // but Playwright's `getByRole('textbox', { name })` includes disabled
    // textbox elements in its match set, so without a scope this throws
    // `strict mode violation: ... resolved to 2 elements`.
    const search = activePanel(page).getByRole('textbox', { name: 'Search' }).first()
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
    return activePanel(page).locator('tbody tr').filter({ hasText: name })
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
 * Fill every still-empty dynamic module parameter inside an open config dialog.
 *
 * Collector/presenter/publisher/bot parameters are declared in
 * `src/shared/shared/config_*.py` via `param_type`, which has NO `required`
 * flag — so the backend never sends one. `dynamicParameterRules` therefore
 * treats every generated field as optional, and empty parameters no longer
 * block Save.
 *
 * This helper is consequently no longer needed to get past validation. It is
 * kept because specs still use it to put a deterministic value into fields they
 * do not assert on, rather than leaving them empty. The default value is `none`,
 * which the collectors read as "no proxy" (see BaseCollector.get_parsed_proxy)
 * and is harmless elsewhere.
 *
 * @param {import('@playwright/test').Locator} dialog - The open dialog locator
 * @param {string} value - Value to type into each empty parameter field
 */
export async function fillRequiredParameters(dialog, value = 'none') {
    // The parameter fields live in the `<div>` that holds the "Parameters" heading.
    // Ancestors come first in DOM order, so `.last()` is the innermost qualifying div —
    // the parameters block itself, not the surrounding card/form. Scoping matters: the
    // same dialogs embed EntitySelectTable "Search" boxes, and filling one of those
    // would filter the table the spec then selects from.
    //
    // The second filter is not redundant: NewProductType wraps its heading in a flex row
    // (heading + help button) that holds no field, so matching on the heading alone would
    // settle on that row and quietly fill nothing.
    //
    // Both `has:` locators are built from the PAGE, not from `dialog`: Playwright re-queries
    // them relative to each candidate <div>, so a dialog-rooted locator (`.v-dialog… >>
    // heading`) matches nothing and the filter silently yields 0.
    const page = dialog.page()
    const section = dialog
        .locator('div')
        .filter({ has: page.getByRole('heading', { name: 'Parameters' }) })
        .filter({ has: page.locator('input') })
        .last()
    if ((await section.count()) === 0) return

    const inputs = section.locator('input')
    for (let i = 0; i < (await inputs.count()); i++) {
        const input = inputs.nth(i)
        if ((await input.inputValue()) === '') {
            await input.fill(value)
        }
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
