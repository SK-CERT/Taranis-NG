import { test, expect } from '@playwright/test'
import { login, navigateToConfig, generateTestName } from '../helpers/test-helpers'

/**
 * User status / approval E2E Tests
 *
 * Covers the account lifecycle introduced with multi-provider auth:
 * pending -> approved -> disabled, the login rejections each state produces,
 * and the last-admin lockout guard.
 */

// See api-seed.js / api-cleanup.js: the E2E stack exposes core on
// E2E_CORE_PORT (default 8090, see docker/.env.e2e). Earlier revisions
// hardcoded 'http://127.0.0.1:8082/...', which the E2E stack does not expose,
// so direct page.request.get(...)/`request.post(${CORE_API}/...)` calls failed
// with ECONNREFUSED while the Vite-proxied GUI flow worked.
const CORE_API = process.env.E2E_CORE_API || `http://127.0.0.1:${process.env.E2E_CORE_PORT || '8090'}/api/v1`

const activePanel = (page) => page.locator('.v-window-item--active')

async function adminHeaders(request) {
    const response = await request.post(`${CORE_API}/auth/login`, { data: { username: 'admin', password: 'admin' } })
    const { access_token: token } = await response.json()
    return { Authorization: `Bearer ${token}` }
}

/** Create a user through the API so the UI test starts from a known state. */
async function createUser(request, { username, password = 'Passw0rd!', status = 'active' }) {
    const headers = await adminHeaders(request)
    await request.post(`${CORE_API}/config/users`, {
        headers,
        data: {
            id: -1,
            username,
            name: username,
            password,
            status,
            organizations: [],
            roles: [],
            permissions: [],
            identities: []
        }
    })
    const listResponse = await request.get(`${CORE_API}/config/users?search=${encodeURIComponent(username)}`, { headers })
    const { items } = await listResponse.json()
    return items.find((item) => item.username === username)
}

async function deleteUser(request, userId) {
    const headers = await adminHeaders(request)
    await request.delete(`${CORE_API}/config/users/${userId}`, { headers })
}

async function setStatus(request, userId, status) {
    const headers = await adminHeaders(request)
    return request.put(`${CORE_API}/config/users/${userId}/status`, { headers, data: { status } })
}

test.describe('User status and approval', () => {
    test('a pending user cannot log in and is told to wait for approval', async ({ page, request }) => {
        const username = generateTestName('e2e-pending').toLowerCase().replace(/\s+/g, '-')
        const user = await createUser(request, { username, status: 'pending' })

        await page.goto('/v2/login')
        await page.locator('[data-test="login-username"] input').fill(username)
        await page.locator('[data-test="login-password"] input').fill('Passw0rd!')
        await page.locator('[data-test="login-submit"]').click()

        await expect(page.locator('[data-test="login-error"]')).toContainText('awaiting administrator approval')
        await expect(page).toHaveURL(/\/v2\/login/)

        await deleteUser(request, user.id)
    })

    test('an admin approves a pending user, who can then log in', async ({ page, request }) => {
        const username = generateTestName('e2e-approve').toLowerCase().replace(/\s+/g, '-')
        const user = await createUser(request, { username, status: 'pending' })

        await login(page)
        await navigateToConfig(page, 'Users')

        // Narrow the table to the pending user
        await activePanel(page).getByRole('textbox', { name: 'Search' }).fill(username)
        const row = activePanel(page).locator('tbody tr').filter({ hasText: username })
        await expect(row).toBeVisible()
        await expect(row).toContainText('Pending approval')

        await row.getByRole('button', { name: 'Approve' }).click()
        await expect(row).toContainText('Active')

        // The approved account can now authenticate
        const loginResponse = await request.post(`${CORE_API}/auth/login`, { data: { username, password: 'Passw0rd!' } })
        expect(loginResponse.ok()).toBeTruthy()

        await deleteUser(request, user.id)
    })

    test('a disabled user is refused at login and loses their session', async ({ page, request }) => {
        const username = generateTestName('e2e-disable').toLowerCase().replace(/\s+/g, '-')
        const user = await createUser(request, { username, status: 'active' })

        // The user is logged in and holds a valid token
        const loginResponse = await request.post(`${CORE_API}/auth/login`, { data: { username, password: 'Passw0rd!' } })
        const { access_token: userToken } = await loginResponse.json()
        const refreshOk = await request.get(`${CORE_API}/auth/refresh`, { headers: { Authorization: `Bearer ${userToken}` } })
        expect(refreshOk.ok()).toBeTruthy()

        await setStatus(request, user.id, 'disabled')

        // The already-issued token stops working immediately
        const refreshAfter = await request.get(`${CORE_API}/auth/refresh`, { headers: { Authorization: `Bearer ${userToken}` } })
        expect(refreshAfter.status()).toBe(401)

        // ... and a fresh login is refused with the disabled message
        await page.goto('/v2/login')
        await page.locator('[data-test="login-username"] input').fill(username)
        await page.locator('[data-test="login-password"] input').fill('Passw0rd!')
        await page.locator('[data-test="login-submit"]').click()
        await expect(page.locator('[data-test="login-error"]')).toContainText('account is disabled')

        await deleteUser(request, user.id)
    })

    test('the status filter narrows the user list', async ({ page, request }) => {
        const username = generateTestName('e2e-filter').toLowerCase().replace(/\s+/g, '-')
        const user = await createUser(request, { username, status: 'pending' })

        await login(page)
        await navigateToConfig(page, 'Users')

        const statusFilter = activePanel(page).getByRole('combobox').filter({ hasText: 'Status' }).first()
        await statusFilter.click()
        await page.locator('.v-overlay__content .v-list-item').filter({ hasText: 'Pending approval' }).first().click()

        // admin (active) is filtered out, the pending user remains
        await expect(activePanel(page).locator('tbody tr').filter({ hasText: username })).toBeVisible()
        await expect(activePanel(page).locator('tbody tr').filter({ hasText: 'admin' })).toHaveCount(0)

        await deleteUser(request, user.id)
    })

    test('refuses to disable the last active administrator', async ({ request }) => {
        const headers = await adminHeaders(request)
        const listResponse = await request.get(`${CORE_API}/config/users?search=admin`, { headers })
        const { items } = await listResponse.json()
        const admin = items.find((item) => item.username === 'admin')

        const response = await setStatus(request, admin.id, 'disabled')

        expect(response.status()).toBe(400)
        expect(await response.text()).toContain('last active')

        // and the admin is still able to log in
        const stillWorks = await request.post(`${CORE_API}/auth/login`, { data: { username: 'admin', password: 'admin' } })
        expect(stillWorks.ok()).toBeTruthy()
    })
})

test.describe('Security self-service', () => {
    test('offers TOTP enrollment and passkey management in the user settings', async ({ page }) => {
        await login(page)

        await page.click('[data-test="user-menu"]')
        await page.getByText('Settings', { exact: false }).first().click()

        const dialog = page.locator('.v-dialog:visible')
        await expect(dialog).toBeVisible()
        await dialog.getByRole('tab', { name: /security/i }).click()

        // TOTP card: not enrolled yet, so enrollment is offered
        await expect(dialog).toContainText('Authenticator app')
        await expect(dialog.getByRole('button', { name: 'Enable' })).toBeVisible()

        // Passkeys card: none registered yet
        await expect(dialog).toContainText('Passkeys')
        await expect(dialog).toContainText('No passkeys registered')
    })

    test('starts a TOTP enrollment and shows a QR code', async ({ page }) => {
        await login(page)

        await page.click('[data-test="user-menu"]')
        await page.getByText('Settings', { exact: false }).first().click()
        const dialog = page.locator('.v-dialog:visible')
        await dialog.getByRole('tab', { name: /security/i }).click()

        await dialog.getByRole('button', { name: 'Enable' }).click()

        await expect(dialog.locator('img[alt="TOTP QR code"]')).toBeVisible()
        await expect(dialog.getByRole('button', { name: 'Activate' })).toBeVisible()
    })
})
