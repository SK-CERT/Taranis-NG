import { test, expect } from '@playwright/test'
import { login, navigateToConfig, generateTestName, activePanel } from '../helpers/test-helpers'

/**
 * API key management E2E tests
 *
 * The admin tab in Access Management creates keys for any user, the User settings tab
 * creates one's own. A key is shown once, acts with its owner's (or the picked)
 * permissions, can be paused, and only works from the addresses its allowlist names.
 */

// Core is published on E2E_CORE_PORT (see docker/.env.e2e); requests go there directly.
const CORE_API = process.env.E2E_CORE_API || `http://127.0.0.1:${process.env.E2E_CORE_PORT || '8090'}/api/v1`
// Needs ASSESS_ACCESS, which the test user has.
const PERMITTED = `${CORE_API}/assess/osint-source-groups`
// Needs CONFIG_USER_ACCESS, which the test user lacks.
const FORBIDDEN = `${CORE_API}/config/users`

async function adminHeaders(request) {
    const response = await request.post(`${CORE_API}/auth/login`, { data: { username: 'admin', password: 'admin' } })
    const { access_token: token } = await response.json()
    return { Authorization: `Bearer ${token}` }
}

/** A user with nothing but direct Assess and Analyze access. */
async function createUser(request, username) {
    const headers = await adminHeaders(request)
    await request.post(`${CORE_API}/config/users`, {
        headers,
        data: {
            id: -1,
            username,
            name: username,
            password: 'Passw0rd!',
            status: 'active',
            organizations: [],
            roles: [],
            permissions: [{ id: 'ASSESS_ACCESS' }, { id: 'ANALYZE_ACCESS' }],
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

const withKey = (key) => ({ headers: { Authorization: `ApiKey ${key}` } })

// The confirmation, not the User settings dialog it may open on top of.
const confirmDelete = (page) =>
    page.getByRole('dialog').filter({ hasText: 'Delete the API key' }).getByRole('button', { name: 'Delete', exact: true }).click()

const uniqueName = (base) => generateTestName(base).toLowerCase().replace(/\s+/g, '-')

test.describe('API key management', () => {
    test('an admin creates a limited key for a user, who can then use exactly that', async ({ page, request }) => {
        const username = uniqueName('e2e-apikey-owner')
        const keyName = uniqueName('e2e-key')
        const user = await createUser(request, username)

        try {
            await login(page)
            await navigateToConfig(page, 'API keys')

            await activePanel(page).locator('[data-test="api-keys-add"]').click()
            const dialog = page.locator('[data-test="api-key-dialog"]')
            await expect(dialog).toBeVisible()

            await dialog.locator('[data-test="api-key-owner"] input').fill(username)
            await page.locator('.v-overlay__content .v-list-item').filter({ hasText: username }).first().click()
            await dialog.locator('[data-test="api-key-name"] input').fill(keyName)
            await dialog.getByRole('radio', { name: 'Only selected permissions' }).check()
            const assessRow = dialog.locator('tbody tr').filter({ hasText: 'Assess access' })
            await expect(assessRow).toBeVisible()
            await assessRow.locator('input[type="checkbox"]').check()
            await dialog.getByRole('button', { name: 'Save' }).click()

            const reveal = page.locator('[data-test="api-key-reveal"]')
            await expect(reveal).toBeVisible()
            const plaintext = await reveal.locator('[data-test="api-key-plaintext"] input').inputValue()
            expect(plaintext).toMatch(/^tnk_[A-Za-z0-9_-]{43}$/)
            await expect(reveal.locator('[data-test="api-key-example"]')).toContainText(`ApiKey ${plaintext}`)
            await reveal.locator('[data-test="api-key-reveal-done"]').click()
            await expect(reveal).toBeHidden()

            // The table shows only how the key begins
            await activePanel(page).getByRole('textbox', { name: 'Search' }).fill(keyName)
            const row = activePanel(page).locator('[data-test="api-key-row"]').filter({ hasText: keyName })
            await expect(row).toBeVisible()
            await expect(row).toContainText(plaintext.slice(0, 12))
            await expect(row).not.toContainText(plaintext)
            await expect(row.locator('[data-test="api-key-scope"]')).toContainText('Limited (1)')

            // Limited to Assess: allowed there, refused for what the user cannot do anyway
            expect((await request.get(PERMITTED, withKey(plaintext))).status()).toBe(200)
            expect((await request.get(FORBIDDEN, withKey(plaintext))).status()).toBe(401)

            // A key can never manage keys, whatever it may do
            expect((await request.get(`${CORE_API}/config/api-keys`, withKey(plaintext))).status()).toBe(401)

            // Paused: refused; resumed: works again
            await row.locator('[data-test="api-key-disable"]').click()
            await expect(row.locator('[data-test="api-key-enable"]')).toBeVisible()
            expect((await request.get(PERMITTED, withKey(plaintext))).status()).toBe(401)
            await row.locator('[data-test="api-key-enable"]').click()
            await expect(row.locator('[data-test="api-key-disable"]')).toBeVisible()
            expect((await request.get(PERMITTED, withKey(plaintext))).status()).toBe(200)

            // Used once: the table says so
            await page.reload()
            await activePanel(page).getByRole('textbox', { name: 'Search' }).fill(keyName)
            await expect(row).not.toContainText('Never used')

            // Deleted: gone for good
            await row.locator('[data-test="api-key-delete"]').click()
            await confirmDelete(page)
            await expect(row).toHaveCount(0)
            expect((await request.get(PERMITTED, withKey(plaintext))).status()).toBe(401)
        } finally {
            await deleteUser(request, user.id)
        }
    })

    test('a key works only from the public addresses its allowlist names', async ({ request }) => {
        const username = uniqueName('e2e-apikey-ips')
        const user = await createUser(request, username)
        const headers = await adminHeaders(request)
        const post = (name, allowedIps) =>
            request.post(`${CORE_API}/config/api-keys`, {
                headers,
                data: { user_id: user.id, name: uniqueName(name), allowed_ips: allowedIps }
            })

        try {
            const listResponse = await request.get(`${CORE_API}/config/api-keys`, { headers })
            expect(listResponse.ok()).toBeTruthy()
            const { client_ip: clientIp, client_ip_public: clientIpPublic } = await listResponse.json()
            expect(clientIp).toBeTruthy()

            // A public range the test runner is not in
            const elsewhere = await post('e2e-key-elsewhere', ['185.10.20.0/24'])
            expect(elsewhere.status()).toBe(201)
            expect((await request.get(PERMITTED, withKey((await elsewhere.json()).key))).status()).toBe(401)

            // The runner's own address works when it is public; a private one cannot be listed at all
            const here = await post('e2e-key-here', [clientIp])
            if (clientIpPublic) {
                expect(here.status()).toBe(201)
                expect((await request.get(PERMITTED, withKey((await here.json()).key))).status()).toBe(200)
            } else {
                expect(here.status()).toBe(400)
                expect((await here.json()).error).toContain('is not a public IP address or range')
            }

            for (const special of ['10.0.0.0/8', '192.168.1.10', '255.255.255.255', '127.0.0.1', 'fe80::1', '2001:db8::/32']) {
                const refused = await post('e2e-key-special', [special])
                expect(refused.status(), special).toBe(400)
                expect((await refused.json()).error, special).toContain('is not a public IP address or range')
            }

            const invalid = await post('e2e-key-invalid', ['example.com'])
            expect(invalid.status()).toBe(400)
            expect((await invalid.json()).error).toContain('is not an IP address or CIDR range')
        } finally {
            // Deleting the user deletes their keys.
            await deleteUser(request, user.id)
        }
    })

    test('an admin manages their own keys in User settings', async ({ page, request }) => {
        const keyName = uniqueName('e2e-own-key')

        await login(page)
        await page.click('[data-test="user-menu"]')
        await page.getByText('Settings', { exact: false }).first().click()
        const settings = page.locator('.v-dialog:visible').first()
        await settings.locator('[data-test="user-settings-api-keys-tab"]').click()

        await settings.locator('[data-test="api-keys-add"]').click()
        const dialog = page.locator('[data-test="api-key-dialog"]')
        await dialog.locator('[data-test="api-key-name"] input').fill(keyName)
        await dialog.getByRole('button', { name: 'Save' }).click()

        const reveal = page.locator('[data-test="api-key-reveal"]')
        const plaintext = await reveal.locator('[data-test="api-key-plaintext"] input').inputValue()
        await reveal.locator('[data-test="api-key-reveal-done"]').click()

        expect((await request.get(PERMITTED, withKey(plaintext))).status()).toBe(200)

        const row = settings.locator('[data-test="api-key-row"]').filter({ hasText: keyName })
        await expect(row).toBeVisible()
        await row.locator('[data-test="api-key-delete"]').click()
        await confirmDelete(page)
        await expect(row).toHaveCount(0)
        expect((await request.get(PERMITTED, withKey(plaintext))).status()).toBe(401)
    })

    test('without MY_API_KEYS_MANAGE there is no API keys tab in User settings', async ({ page, request }) => {
        const username = uniqueName('e2e-apikey-none')
        const user = await createUser(request, username)

        try {
            await login(page, username, 'Passw0rd!')
            await page.click('[data-test="user-menu"]')
            await page.getByText('Settings', { exact: false }).first().click()
            const settings = page.locator('.v-dialog:visible').first()
            await expect(settings.getByRole('tab', { name: /security/i })).toBeVisible()
            await expect(settings.locator('[data-test="user-settings-api-keys-tab"]')).toHaveCount(0)

            // ... and the endpoint refuses them too
            const loginResponse = await request.post(`${CORE_API}/auth/login`, { data: { username, password: 'Passw0rd!' } })
            const { access_token: token } = await loginResponse.json()
            const own = await request.get(`${CORE_API}/users/my-api-keys`, { headers: { Authorization: `Bearer ${token}` } })
            expect(own.status()).toBe(401)
        } finally {
            await deleteUser(request, user.id)
        }
    })
})
