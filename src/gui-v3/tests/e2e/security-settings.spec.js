import { test, expect } from '@playwright/test'
import { login, navigateToConfig } from '../helpers/test-helpers'

/**
 * Security settings (WebAuthn relying party) E2E tests.
 *
 * Covers the Security tab of Access Management — the site-wide WebAuthn
 * relying-party configuration (rp_id / rp_name / origins) and the twofold
 * passkey switches. Passkeys are *credentials owned by users* (see
 * src/core/model/webauthn_credential.py), not an identity provider — the
 * relying-party fields only describe this site to the authenticator, so they
 * live in model/security_settings.py rather than in auth_provider. That's why
 * this is its own spec: the Security tab is a sibling of Login Methods under
 * Access Management, not a child of it (mirroring the GUI one-file-per-tab
 * convention the rest of the e2e/ folder already follows for
 * roles / organizations / user-status / auth-providers).
 *
 * This block was previously the `Security settings (passkey relying party)`
 * describe inside auth-providers.spec.js; it shares no auth-provider-specific
 * helpers (no selectKind / fillDialogField / openDialog / saveDialog / findRow*
 * / IDP_CERT fixtures), only the generic `login` / `navigateToConfig` /
 * `activePanel` helpers, which is why the split is cheap.
 *
 * Coupling to note: mfa-enrollment.spec.js's passkey-registration test sets up
 * its own relying-party config by mirroring this suite's beforeEach (see the
 * setupPasskeyRelyingParty helper there), and the rest of the e2e suite treats
 * `passkey_enabled: false` as the baseline — this spec's last test restores it.
 */

// The core API base. Defaults to the backend the Playwright webServer boots
// (E2E_CORE_PORT, default 8090 — see docker/.env.e2e); override with
// E2E_CORE_API if your setup differs. Inlined here (rather than imported) so
// the constant is available to module-scope helpers without a circular import
// on the test-helpers file. NOTE: must NOT be hardcoded to a literal port
// (earlier revisions used 'http://127.0.0.1:8082/...', which the E2E stack
// does not expose — it uses 8090), so direct page.request.* calls targeting
// the backend ECONNREFUSE while the Vite-proxied GUI flow worked.
const CORE_API = process.env.E2E_CORE_API || `http://127.0.0.1:${process.env.E2E_CORE_PORT || '8090'}/api/v1`

/** Scope queries to the active tab: Vuetify keeps the previous tab's DOM around. */
const activePanel = (page) => page.locator('.v-window-item--active')

/**
 * PUT the baseline security settings via the API so every test starts from a
 * known state (passkeys off, empty relying-party fields) — and, crucially, so
 * `updated_by`/`updated_at` are populated. On a virgin database the settings
 * row is lazily created with `updated_by = NULL` and the "Last updated by"
 * caption the beforeEach guard waits on never renders. The only other writer
 * of /config/security is mfa-enrollment.spec.js, whose tests are
 * chromium-only — so on the firefox/webkit CI jobs (fresh stack per matrix
 * browser, workers: 1) nothing had saved the settings before this spec ran
 * and all three tests timed out on the guard. Seeding here makes the spec
 * self-contained instead of order-dependent.
 */
async function seedSecurityBaseline(request) {
    const loginRes = await request.post(`${CORE_API}/auth/login`, {
        data: { username: 'admin', password: 'admin' }
    })
    expect(loginRes.ok(), `seed login failed: ${loginRes.status()} ${await loginRes.text()}`).toBe(true)
    const { access_token: token } = await loginRes.json()
    const seedRes = await request.put(`${CORE_API}/config/security`, {
        headers: { Authorization: `Bearer ${token}` },
        data: {
            passkey_enabled: false,
            passkey_second_factor: true,
            require_mfa: false,
            rp_id: '',
            rp_name: '',
            origins: ''
        }
    })
    expect(seedRes.ok(), `seed PUT /config/security failed: ${seedRes.status()} ${await seedRes.text()}`).toBe(true)
}

test.describe('Security settings (passkey relying party)', () => {
    test.beforeEach(async ({ page, request }) => {
        await seedSecurityBaseline(request)
        await login(page)
        await navigateToConfig(page, 'Security')
        // SecurityTab.vue's onMounted fires loadData() (GET /config/security)
        // asynchronously; navigateToConfig() only waits for the tab click, not
        // for that round-trip. If loadData() resolves after we toggle/fill, its
        // `settings.value = { ...settings.value, ...response.data }` clobbers
        // our edits and Save POSTs the previous (untoggled) state — which
        // manifests as `passkey_enabled: false` after a "successful" save.
        // The "Last updated by" caption renders only from updated_at/
        // updated_by populated by the GET response, so awaiting it proves the
        // form is interactive before we touch it. (Same guard the
        // mfa-enrollment.spec.js setupPasskeyRelyingParty helper uses.)
        await expect(activePanel(page).getByText(/last updated by/i)).toBeVisible({ timeout: 10_000 })
    })

    test('lives as its own tab, separate from Login Methods', async ({ page }) => {
        await expect(page).toHaveURL(/\/config\/access-management\?tab=security/)
        await expect(activePanel(page)).toContainText('Passkeys (WebAuthn)')
        // the framing makes clear this is not an identity provider
        await expect(activePanel(page)).toContainText('credentials owned by users')
    })

    test('refuses to enable passkeys without a relying-party configuration', async ({ page }) => {
        const panel = activePanel(page)

        await panel.getByLabel('Enable passkey sign-in').click()
        await panel.getByRole('button', { name: 'Save' }).click()

        // the required-field rules block the save; nothing is persisted
        await expect(panel.locator('.v-messages__message').first()).toBeVisible()
    })

    test('saves the relying-party configuration and turns passkey sign-in on', async ({ page, request }) => {
        const panel = activePanel(page)

        // Capture the Save PUT to /config/security and assert its status, so a
        // backend rejection (e.g. "requires a relying-party ID and origin") or
        // a loadData()-race that POSTs the untoggled state surfaces HERE — with
        // the response body — rather than as a confusing `passkey_enabled:false`
        // downstream. Mirrors the proven setupPasskeyRelyingParty helper in
        // mfa-enrollment.spec.js. Use .check() (explicit on, idempotent) rather
        // than .click() (toggles current state) so the toggle can't be flipped
        // the wrong way by a Vuetify switch DOM/binding propagation lag —
        // firefox in particular has shown the switch's checked-attribute lags
        // the model by a tick, making a .click()'s net effect dependent on
        // timing. .check() always lands on "on" regardless of starting state.
        const enableSave = page.waitForResponse((r) => r.request().method() === 'PUT' && r.url().endsWith('/config/security'))
        await panel.getByLabel('Enable passkey sign-in').check()
        await panel.getByLabel('Relying party ID').fill('localhost')
        await panel.getByLabel('Allowed origins').fill('http://localhost:4445')
        await panel.getByRole('button', { name: 'Save' }).click()
        const enableRes = await enableSave
        expect(enableRes.ok(), `enable Save PUT /config/security failed: ${enableRes.status()} ${await enableRes.text()}`).toBe(true)

        await expect(panel.getByText(/last updated by/i)).toBeVisible()

        // the login page now offers passwordless sign-in
        const methods = await (await request.get(`${CORE_API}/auth/methods`)).json()
        expect(methods.passkey_enabled).toBe(true)

        // an authenticated visit to /login redirects to the dashboard, so drop the session first
        await page.evaluate(() => localStorage.clear())
        await page.goto('/v2/login')
        await expect(page.locator('[data-test="login-passkey"]')).toBeVisible()

        // put it back so the rest of the suite starts from a clean state
        await login(page)
        await navigateToConfig(page, 'Security')
        const cleanupPanel = activePanel(page)
        // Same loadData()-race guard as the beforeEach: navigateToConfig() returns
        // once the tab is clicked, before loadData() resolves. Without this
        // wait, toggling Enable then Save can fire while the previous
        // (untoggled) state is still being applied, leaving passkey_enabled on.
        await expect(cleanupPanel.getByText(/last updated by/i)).toBeVisible({ timeout: 10_000 })
        // Capture the cleanup PUT too, with the same loud assertion + .uncheck()
        // (explicit off, idempotent) for the firefox switch-propagation reason
        // noted on the enable step above.
        const cleanupSave = page.waitForResponse((r) => r.request().method() === 'PUT' && r.url().endsWith('/config/security'))
        await cleanupPanel.getByLabel('Enable passkey sign-in').uncheck()
        await cleanupPanel.getByRole('button', { name: 'Save' }).click()
        const cleanupRes = await cleanupSave
        expect(cleanupRes.ok(), `cleanup Save PUT /config/security failed: ${cleanupRes.status()} ${await cleanupRes.text()}`).toBe(true)
        await expect(cleanupPanel.getByText(/last updated by/i)).toBeVisible()

        const after = await (await request.get(`${CORE_API}/auth/methods`)).json()
        expect(after.passkey_enabled).toBe(false)
    })
})
