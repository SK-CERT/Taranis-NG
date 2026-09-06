import { test, expect } from '@playwright/test'
import { login } from '../helpers/test-helpers'
import { createApiContext } from '../helpers/api-cleanup'

/**
 * The user list answers "who can get in, as what, and are they still using it": roles and last
 * login are columns, and a disabled account is dimmed rather than carrying a status chip - the
 * same treatment a disabled OSINT source gets.
 *
 * Last login is the account's own stamp. UserAuthIdentity has one too, but it is written only on
 * the external-provider path, so it stays empty for every local password account.
 */

const USERS_URL = '/v2/config/access-management'
const CORE_API = process.env.E2E_CORE_API || `http://127.0.0.1:${process.env.E2E_CORE_PORT || '8090'}/api/v1`
const PREFIX = 'e2e-usertable'
const PASSWORD = 'Sup3rS3cret!23'

async function api(playwright) {
    return createApiContext(playwright)
}

async function purge(playwright) {
    let ctx
    try {
        ctx = await api(playwright)
        const headers = { Authorization: `Bearer ${ctx.token}` }
        const { items = [] } = await (await ctx.request.get(`${CORE_API}/config/users?search=`, { headers })).json()
        for (const user of items.filter((u) => u.username.startsWith(PREFIX))) {
            await ctx.request.delete(`${CORE_API}/config/users/${user.id}`, { headers })
        }
    } catch {
        // Best effort: never fail the suite on cleanup.
    } finally {
        await ctx?.request.dispose()
    }
}

async function createUser(request, token, username, { status = 'active', signIn = false } = {}) {
    const headers = { Authorization: `Bearer ${token}` }
    // Never the Admin role: another spec asserts that the last active administrator cannot be
    // disabled, and a throwaway administrator here would make that guard let the real admin
    // through - locking the account the rest of the suite logs in with.
    const { items: roles = [] } = await (await request.get(`${CORE_API}/config/roles?search=`, { headers })).json()
    const role = roles.find((r) => r.name !== 'Admin')
    await request.post(`${CORE_API}/config/users`, {
        headers,
        data: {
            id: -1,
            username,
            name: `Probe ${username}`,
            password: PASSWORD,
            require_mfa: false,
            organizations: [],
            roles: role ? [{ id: role.id }] : [],
            permissions: []
        }
    })
    const { items = [] } = await (await request.get(`${CORE_API}/config/users?search=${username}`, { headers })).json()
    const user = items.find((u) => u.username === username)
    if (signIn) {
        await request.post(`${CORE_API}/auth/login`, { data: { username, password: PASSWORD } })
    }
    if (status !== 'active') {
        await request.put(`${CORE_API}/config/users/${user.id}/status`, { headers, data: { status } })
    }
    return user
}

/** The non-admin role the probes are created with, so the Roles column can be asserted. */
async function roleForProbes(playwright) {
    const ctx = await createApiContext(playwright)
    try {
        const { items = [] } = await (
            await ctx.request.get(`${CORE_API}/config/roles?search=`, { headers: { Authorization: `Bearer ${ctx.token}` } })
        ).json()
        return items.find((r) => r.name !== 'Admin')?.name ?? null
    } finally {
        await ctx.request.dispose()
    }
}

/** The row for one username, located by its bolded username cell. */
function rowFor(page, username) {
    return page
        .locator('.auto-paged tbody tr')
        .filter({ has: page.locator('td strong').filter({ hasText: new RegExp(`^${username}$`) }) })
        .first()
}

test.describe('Access management - user list', () => {
    test.beforeAll(async ({ playwright }) => {
        await purge(playwright)
    })

    test.afterAll(async ({ playwright }) => {
        await purge(playwright)
    })

    test.beforeEach(async ({ page }) => {
        await login(page)
        await page.goto(USERS_URL)
        await page.getByRole('tab', { name: 'Users' }).click()
        await page.waitForSelector('.auto-paged tbody tr td strong')
    })

    test('shows roles and last login, and no status column', async ({ page, playwright }) => {
        const ctx = await api(playwright)
        const signedIn = `${PREFIX}-signedin`
        const never = `${PREFIX}-never`
        await createUser(ctx.request, ctx.token, signedIn, { signIn: true })
        await createUser(ctx.request, ctx.token, never)
        await ctx.request.dispose()
        await page.reload()
        await page.getByRole('tab', { name: 'Users' }).click()
        await page.waitForSelector('.auto-paged tbody tr td strong')

        const columns = (await page.locator('.auto-paged thead th').allInnerTexts()).map((t) => t.trim())
        expect(columns).toContain('Roles')
        expect(columns).toContain('Last login')
        expect(columns).not.toContain('Status')

        // The account that signed in carries a formatted stamp; the one that never did shows a dash.
        await expect(rowFor(page, signedIn)).toContainText('2026')
        await expect(rowFor(page, never)).toContainText('–')
        // Roles come from the account, so the role it was created with is on the row.
        const roleName = await roleForProbes(playwright)
        if (roleName) {
            await expect(rowFor(page, signedIn)).toContainText(roleName)
        }
    })

    test('dims a disabled account and restores it on hover', async ({ page, playwright }) => {
        const ctx = await api(playwright)
        const disabled = `${PREFIX}-disabled`
        const active = `${PREFIX}-active`
        await createUser(ctx.request, ctx.token, disabled, { status: 'disabled' })
        await createUser(ctx.request, ctx.token, active)
        await ctx.request.dispose()
        await page.reload()
        await page.getByRole('tab', { name: 'Users' }).click()
        await page.waitForSelector('.auto-paged tbody tr td strong')

        const disabledRow = rowFor(page, disabled)
        await expect(disabledRow).toHaveClass(/user-disabled/)
        expect(await disabledRow.evaluate((el) => window.getComputedStyle(el).opacity)).toBe('0.55')

        await expect(rowFor(page, active)).not.toHaveClass(/user-disabled/)
        expect(await rowFor(page, active).evaluate((el) => window.getComputedStyle(el).opacity)).toBe('1')

        // Dimming must not make a disabled account unreadable when you go to act on it.
        await disabledRow.hover()
        await expect.poll(async () => disabledRow.evaluate((el) => window.getComputedStyle(el).opacity)).toBe('1')
    })
})
