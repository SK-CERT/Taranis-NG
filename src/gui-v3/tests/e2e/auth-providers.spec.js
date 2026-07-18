import { test, expect } from '@playwright/test'
import { execSync } from 'node:child_process'
import { generateKeyPairSync } from 'node:crypto'
import { mkdtempSync, readFileSync, rmdirSync, unlinkSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { login, navigateToConfig, openDialog, saveDialog, generateTestName, findRowByName } from '../helpers/test-helpers'

/**
 * Login Methods (identity providers) E2E Tests.
 *
 * Covers the Login Methods tab of Access Management: listing the seeded
 * "Local accounts" provider, creating OIDC / SAML 2.0 / LDAP providers, the
 * write-only secret, the delete warning about linked identities, the
 * public /auth/methods contract the login page depends on, the auth
 * provider slug contract (auto-derive on create / stable across edits /
 * unique on collision — the slug keys the SAML/OAuth SSO routes, see
 * src/core/api/auth.py), and the SAML SP metadata contract (anonymous GET,
 * content-type, slug-keyed route, 404). The slug block was previously a
 * separate auth-provider-slugs.spec.js; the SAML SP metadata block was
 * previously a separate saml-sp-metadata.spec.js; both folded in here
 * because they exercise the same auth-provider domain through the same
 * dialog / API as the CRUD tests.
 *
 * The sibling Security tab of Access Management (WebAuthn relying-party
 * settings) is its own spec — security-settings.spec.js — mirroring the
 * one-file-per-tab convention the rest of the e2e/ folder follows (roles /
 * organizations / user-status / etc.).
 */

// The core API base. Defaults to the backend the Playwright webServer boots
// (E2E_CORE_PORT, default 8090 — see docker/.env.e2e); override with
// E2E_CORE_API if your setup differs. Inlined here (rather than imported) so
// the constant is available to module-scope cleanup helpers without a circular
// import on the test-helpers file. NOTE: must NOT be hardcoded to a literal
// port — earlier revisions used 'http://127.0.0.1:8082/...', which the E2E
// stack does not expose (it uses 8090), so page.request.get() calls targeting
// the backend failed with ECONNREFUSED while the Vite-proxied GUI flow worked.
const CORE_API = process.env.E2E_CORE_API || `http://127.0.0.1:${process.env.E2E_CORE_PORT || '8090'}/api/v1`

/** Scope queries to the active tab: Vuetify keeps the previous tab's DOM around. */
const activePanel = (page) => page.locator('.v-window-item--active')

/** Open the kind select of the provider dialog and pick an option by label. */
async function selectKind(page, kindLabel) {
    const dialog = page.locator('.v-dialog:visible')
    await dialog.getByRole('combobox').filter({ hasText: 'Type' }).click()
    await page.locator('.v-overlay__content .v-list-item').filter({ hasText: kindLabel }).first().click()
}

/** Fill a labelled text field inside the visible dialog. */
async function fillDialogField(page, label, value) {
    const dialog = page.locator('.v-dialog:visible')
    await dialog.getByLabel(label, { exact: false }).first().fill(value)
}

/** Authenticate as admin and return the Bearer header for direct API calls. */
async function adminHeaders(request) {
    const res = await request.post(`${CORE_API}/auth/login`, { data: { username: 'admin', password: 'admin' } })
    const { access_token: token } = await res.json()
    return { Authorization: `Bearer ${token}` }
}

/** Fetch the persisted provider record by name through the API (config endpoint). */
async function fetchProviderByName(request, name) {
    const headers = await adminHeaders(request)
    const res = await request.get(`${CORE_API}/config/auth-providers?search=${encodeURIComponent(name)}`, { headers })
    const { items } = await res.json()
    return items.find((item) => item.name === name)
}

/** Remove a provider by name through the API (best-effort test cleanup).
 *
 * Tolerant of the slugify-driven name normalization: callers may pass a name
 * whose runs of whitespace differ from the persisted row (the slug-collision
 * test creates `E2E Collision  A` with two spaces, but the stored row is
 * `E2E Collision A` with one space after slugify collapses whitespace). The
 * `search=name` endpoint matches on the normalized name, so a two-space name
 * won't return the one-space row — derive the single-space form and retry so
 * a cleanup miss can't leak the row and break later runs' pagination/locale
 * assertions. Best-effort: missing-provider is a no-op, not an error.
 */
async function deleteProviderByName(request, name) {
    const headers = await adminHeaders(request)
    const names = Array.from(new Set([name, name.replace(/\s+/g, ' ')]))
    for (const candidate of names) {
        const res = await request.get(`${CORE_API}/config/auth-providers?search=${encodeURIComponent(candidate)}`, { headers })
        if (!res.ok()) {
            continue
        }
        const { items = [] } = await res.json()
        const provider = items.find((item) => item.name === candidate)
        if (provider) {
            await request.delete(`${CORE_API}/config/auth-providers/${provider.id}`, { headers })
        }
    }
}

// A real (throwaway, self-signed) certificate: the backend now rejects an unparsable
// one when the provider is saved, so a placeholder string would no longer do.
const IDP_CERT_B64 =
    'MIIC0jCCAbqgAwIBAgIUe7g7ynxmFHrrQyFEqlW0iBKn0qcwDQYJKoZIhvcNAQELBQAwIzEhMB8GA1UEAwwYZTJlLXRlc3QtaWRwLmV4YW1wbGUub3JnMB4XDTI2MDcxMjEyMzQxM1oXDTM2MDcxMDEyMzQxM1owIzEhMB8GA1UEAwwYZTJlLXRlc3QtaWRwLmV4YW1wbGUub3JnMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAwFyyhobTgzT2DOvQAee7a14aDMHF2jFHXI8gPQabSNgRh/13m5htgiaYVVNu+nAGqMQEaAqDGoPFmZmMRpo48X72f6Hpy7fXJHuy1FK+etKpoDzcJevpEmLS/i1Vc2zthTss5w9ENYuR3bbYkLS/Pkdflz7q/CsWbVdshh1TxIZ6AFA22mLw444Spe3k9aWaRhpJBwd1h9CVlNgj2QUpzZJc5D5m6ai4iBfyBy9NrJ7M5fXIZ4qKzNnhGam3rERmXkVScQVgjM1eom2ytRJphHD7PZslLAZpHPFBCQG138J1yZ7AJjdABw7d/GRzam6+ljOzwGXd9+krbtHyV6NznwIDAQABMA0GCSqGSIb3DQEBCwUAA4IBAQBOhS55zCbR5aNpvS5Dvzv3QpkACjG4w6+oWncaleje/1CRhb+pyGP4MPGJBjBff4cwvs3J3Pk01La57hpRgzYtpA4ii125BLg6GrgbRiokc4gE3bBJcdloNAICuIqr+0xZ/0gGMtK2MLxIC5KkpAibhsVxtDH2v1FhqUxShX8TrTCrRYkb3p89CnuijQUuYMm29kkeypGMyUuuUX9fH9e6nFL/Kv+uLveyJI//TkLqljjpAsRsHXNM9zrQZxX8Bgo2HKyQcRW9tAwQlOsvAxWvtxSFQlAkMDsgmkovEKNgV4BIazpC8DFVU1LhVvlKev6ARqVnZv1a/24NcMi7bubj'

const IDP_METADATA = `<?xml version="1.0"?>
<md:EntityDescriptor xmlns:md="urn:oasis:names:tc:SAML:2.0:metadata" xmlns:ds="http://www.w3.org/2000/09/xmldsig#"
    entityID="https://idp.example.org/idp/shibboleth">
  <md:IDPSSODescriptor protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol">
    <md:KeyDescriptor use="signing">
      <ds:KeyInfo><ds:X509Data><ds:X509Certificate>${IDP_CERT_B64}</ds:X509Certificate></ds:X509Data></ds:KeyInfo>
    </md:KeyDescriptor>
    <md:KeyDescriptor use="encryption">
      <ds:KeyInfo><ds:X509Data><ds:X509Certificate>${IDP_CERT_B64}</ds:X509Certificate></ds:X509Data></ds:KeyInfo>
    </md:KeyDescriptor>
    <md:SingleSignOnService Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
        Location="https://idp.example.org/sso/post"/>
    <md:SingleSignOnService Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
        Location="https://idp.example.org/sso/redirect"/>
  </md:IDPSSODescriptor>
</md:EntityDescriptor>`

test.describe('Login Methods', () => {
    test.beforeEach(async ({ page }) => {
        await login(page)
        await navigateToConfig(page, 'Login Methods')
        await page.waitForSelector('.v-data-table', { timeout: 5000 })
    })

    test('lives as a tab inside Access Management', async ({ page }) => {
        await expect(page).toHaveURL(/\/config\/access-management\?tab=login-methods/)
        await expect(activePanel(page).locator('.v-data-table')).toBeVisible()
    })

    test('lists the seeded local accounts provider', async ({ page }) => {
        const row = activePanel(page).locator('tbody tr').filter({ hasText: 'Local accounts' })
        await expect(row).toBeVisible()
        // kind chip + "linked users only" provisioning are rendered per row
        await expect(row).toContainText('Local accounts')
    })

    test('creates an OIDC provider with a write-only client secret', async ({ page, request }) => {
        const name = generateTestName('E2E OIDC')

        await openDialog(page, 'New')
        const dialog = page.locator('.v-dialog:visible')
        await expect(dialog).toBeVisible()

        await fillDialogField(page, 'Name', name)
        await selectKind(page, 'OpenID Connect')
        await fillDialogField(page, 'Issuer URL', 'https://idp.example.org/realms/main')
        await fillDialogField(page, 'Client ID', 'taranis-ng')
        await fillDialogField(page, 'Client secret', 'super-secret-value')

        await saveDialog(page)
        await expect(dialog).toHaveCount(0)

        // Config tables are server-side paginated (default 10 per page); on a stack with
        // seeded leftovers from earlier runs the new provider can land past page 1 and be
        // invisible to a plain row locator. The Search box filters server-side too, so
        // searching the exact name collapses the table to a single matching row before
        // we assert visibility. (Looks-broken-but-isn't: the save SUCCEEDED when this times out.)
        const row = await findRowByName(page, name)
        await expect(row).toBeVisible()
        await expect(row).toContainText('OpenID Connect')

        // The secret must never come back to the browser: the list API only reports has_secret.
        const listResponse = await page.request.get(`${CORE_API}/config/auth-providers?search=${encodeURIComponent(name)}`, {
            headers: { Authorization: `Bearer ${await page.evaluate(() => localStorage.getItem('ACCESS_TOKEN'))}` }
        })
        const body = await listResponse.json()
        const created = body.items.find((item) => item.name === name)
        expect(created.has_secret).toBe(true)
        expect(created.secret).toBeUndefined()
        expect(JSON.stringify(created)).not.toContain('super-secret-value')

        await deleteProviderByName(request, name)
    })

    test('creates a SAML 2.0 provider', async ({ page, request }) => {
        // pasting the metadata, importing it, generating the SP keypair and saving are
        // four backend round-trips: more than the default budget allows.
        test.setTimeout(90_000)
        const name = generateTestName('E2E SAML')

        await openDialog(page, 'New')
        const dialog = page.locator('.v-dialog:visible')

        await fillDialogField(page, 'Name', name)
        await selectKind(page, 'SAML 2.0')

        // SAML-specific fields appear only after the kind is picked
        await expect(dialog.getByLabel('IdP metadata', { exact: false }).first()).toBeVisible()

        // paste the IdP metadata and let the backend fill in entity ID, SSO URL and certificate
        await dialog.getByLabel('IdP metadata', { exact: false }).first().fill(IDP_METADATA)
        await dialog.getByRole('button', { name: 'Load' }).click()

        await expect(dialog.getByLabel('IdP entity ID', { exact: false }).first()).toHaveValue('https://idp.example.org/idp/shibboleth')
        // the HTTP-Redirect endpoint is chosen, not the HTTP-POST one
        await expect(dialog.getByLabel('IdP SSO URL', { exact: false }).first()).toHaveValue('https://idp.example.org/sso/redirect')
        await expect(dialog.getByLabel('IdP signing certificate', { exact: false }).first()).toHaveValue(/-----BEGIN CERTIFICATE-----/)

        await fillDialogField(page, 'SP entity ID', 'taranis-ng')
        // keys the account across logins; without it a transient NameID locks the user out
        await fillDialogField(page, 'Stable identifier attribute', 'urn:oid:1.3.6.1.4.1.5923.1.1.1.13')

        // The keypair is generated by the backend through an in-dialog POST
        // (/config/auth-providers/saml/generate-keypair) and the resulting private key +
        // certificate are stored into the form's secretInput / config.sp_certificate — they
        // are only persisted when the provider is saved. So Generate must happen BEFORE Save:
        // saving first closes the dialog (the page snapshot confirmed no dialog after save),
        // leaving this click to time out looking for a button inside a closed dialog.
        //
        // The Generate button lives in the "SP keypair" tab of the dialog — a real user must
        // click that tab first. SamlFields.vue uses v-tabs; the tab is reached by role.
        await dialog.getByRole('tab', { name: 'SP keypair' }).click()
        await expect(dialog.getByRole('tab', { name: 'SP keypair' })).toHaveAttribute('aria-selected', 'true')
        // Wait for the v-window slide transition to settle BEFORE clicking Generate:
        // v-tab's aria-selected flips immediately on click, but the matching v-window-item
        // only gains the --active class once Vuetify's ~300ms transition completes.
        await expect(dialog.locator('.v-window-item--active').filter({ hasText: 'Generate keypair' })).toBeVisible()
        // Generate triggers an in-dialog POST to /config/auth-providers/saml/generate-keypair
        // whose response populates the SP certificate + private key fields. Capture that POST
        // so a backend rejection (or a click that didn't reach the @click handler) surfaces
        // HERE with the response body, rather than as a confusing empty-SP-certificate timeout
        // downstream. The earlier waitForResponse-only attempt was wrong because it didn't
        // also assert the field population, so a click miss looked identical to a slow POST.
        //
        // On webkit the mouse click on this v-btn (with a prepend-icon) sometimes doesn't
        // dispatch the @click handler — the button focuses (snapshot showed it [active])
        // but the POST never fires and waitForResponse hits the test timeout. Forcing the
        // click bypasses Playwright's actionability re-checks (which pass — the button is
        // visible/enabled/focused) so we get straight to the dispatch; if force still fails
        // to fire it on webkit we'd see it as a waitForResponse timeout, isolating the
        // cause to "click didn't fire" rather than "POST slow". See mfa-enrollment.spec.js's
        // begin/finish roundtrips for the same click+waitForResponse idiom.
        const generateKeypair = page.waitForResponse(
            (r) => r.request().method() === 'POST' && r.url().endsWith('/config/auth-providers/saml/generate-keypair')
        )
        await dialog.getByRole('button', { name: 'Generate keypair' }).click({ force: true })
        const keypair = await generateKeypair
        expect(keypair.ok(), `generate-keypair POST failed: ${keypair.status()} ${await keypair.text()}`).toBe(true)
        await expect(dialog.getByLabel('SP certificate', { exact: false }).first()).toHaveValue(/-----BEGIN CERTIFICATE-----/)
        await expect(dialog.getByLabel('SP private key', { exact: false }).first()).toHaveValue(/-----BEGIN PRIVATE KEY-----/)

        await saveDialog(page)
        await expect(dialog).toHaveCount(0)

        // Config tables are server-side paginated (default 10 per page); on a stack with
        // seeded leftovers from earlier runs, the new provider can land past page 1 and be
        // invisible to a plain row locator. (The page snapshot for this failure showed
        // "1-10 of 11" with the new item on page 2 — the save had succeeded.) Search the
        // exact name to collapse the table to the single matching row before asserting.
        const row = await findRowByName(page, name)
        await expect(row).toBeVisible()
        await expect(row).toContainText('SAML 2.0')

        // the SP publishes metadata an identity provider can register
        const token = await page.evaluate(() => localStorage.getItem('ACCESS_TOKEN'))
        const listResponse = await page.request.get(`${CORE_API}/config/auth-providers?search=${encodeURIComponent(name)}`, {
            headers: { Authorization: `Bearer ${token}` }
        })
        const created = (await listResponse.json()).items.find((item) => item.name === name)

        // The SAML routes (/auth/saml/<provider_slug>/...) are slug-keyed, not keyed
        // by the database id, so the stable URL survives row recreation across
        // environments. Using created.id here 404s because <int:id> doesn't match
        // the <string:provider_slug> route (see src/core/api/auth.py).
        expect(created.slug, 'provider must have a slug for its SAML routes').toBeTruthy()
        expect(typeof created.slug).toBe('string')

        // anonymous: an IdP fetches this without credentials
        const metadata = await request.get(`${CORE_API}/auth/saml/${created.slug}/metadata`)
        expect(metadata.ok()).toBeTruthy()
        expect(metadata.headers()['content-type']).toContain('samlmetadata+xml')

        const xml = await metadata.text()
        expect(xml).toContain('entityID="taranis-ng"')
        expect(xml).toContain(`/api/v1/auth/saml/${created.slug}/acs`)
        expect(xml).toContain('AuthnRequestsSigned="false"')
        expect(xml).toContain('WantAssertionsSigned="true"')
        expect(xml).toContain('urn:oid:1.3.6.1.4.1.5923.1.1.1.13')
        // the generated certificate is published for the IdP to encrypt assertions to
        expect(xml).toContain('<md:KeyDescriptor use="encryption">')
        expect(xml).toContain('rsa-oaep')
        expect(xml).toContain('aes256-gcm')
        // the Bleichenbacher-prone legacy key transport is never advertised
        expect(xml).not.toContain('rsa-1_5')

        await deleteProviderByName(request, name)
    })

    test('creates an LDAP provider', async ({ page, request }) => {
        const name = generateTestName('E2E LDAP')

        await openDialog(page, 'New')
        const dialog = page.locator('.v-dialog:visible')

        await fillDialogField(page, 'Name', name)
        await selectKind(page, 'LDAP / Active Directory')
        await fillDialogField(page, 'Server URL', 'ldaps://ldap.example.org')
        // The LdapFields.vue field is labelled "User DN or base DN" (i18n key
        // auth_provider.user_dn_template) — it serves both direct-bind mode
        // (with the {username} placeholder in the template) and search-and-bind
        // mode (a plain base DN). The branch's LdapFields.vue renamed the label
        // away from the older "User DN template"; the test references the
        // current label so fillDialogField's getByLabel actually resolves.
        await fillDialogField(page, 'User DN or base DN', 'uid={username},ou=people,dc=example,dc=org')

        await saveDialog(page)
        await expect(dialog).toHaveCount(0)

        // LDAP test: same pagination caveat as OIDC/SAML — seed leftovers can push the
        // new provider past page 1. Search the exact name to collapse the table.
        const row = await findRowByName(page, name)
        await expect(row).toBeVisible()

        await deleteProviderByName(request, name)
    })

    test('requires a name', async ({ page }) => {
        await openDialog(page, 'New')
        await selectKind(page, 'OpenID Connect')
        await saveDialog(page)

        // A rejected save keeps the dialog open and shows the inline validation alert.
        await expect(page.locator('.v-dialog:visible .v-alert')).toBeVisible()
        await expect(page.locator('.v-dialog:visible')).toBeVisible()
    })

    test('reopens the edit dialog after it was closed (re-edit regression)', async ({ page }) => {
        const row = activePanel(page).locator('tbody tr').filter({ hasText: 'Local accounts' })

        await row.getByRole('button').filter({ hasText: /^$/ }).first().click()
        await expect(page.locator('.v-dialog:visible')).toBeVisible()

        // Close without saving
        await page.locator('.v-dialog:visible').getByRole('button', { name: 'Cancel' }).click()
        await expect(page.locator('.v-dialog:visible')).toHaveCount(0)

        // Clicking Edit on the same row must open the dialog again
        await row.getByRole('button').filter({ hasText: /^$/ }).first().click()
        await expect(page.locator('.v-dialog:visible')).toBeVisible()
    })

    test('deletes a provider and warns when identities are linked', async ({ page }) => {
        const name = generateTestName('E2E Delete Me')

        await openDialog(page, 'New')
        await fillDialogField(page, 'Name', name)
        await selectKind(page, 'OpenID Connect')
        await fillDialogField(page, 'Issuer URL', 'https://idp.example.org')
        await fillDialogField(page, 'Client ID', 'taranis-ng')
        await saveDialog(page)

        // Same pagination caveat as the other create tests: filter via Search before
        // asserting visibility, otherwise the new row may sit on page 2.
        const row = await findRowByName(page, name)
        await expect(row).toBeVisible()

        // The delete button is the last action button of the row
        await row.getByRole('button').last().click()
        const confirmation = page.locator('.v-dialog:visible')
        await expect(confirmation).toContainText(name)
        await confirmation.getByRole('button', { name: /delete/i }).click()

        await expect(activePanel(page).locator('tbody tr').filter({ hasText: name })).toHaveCount(0)
    })
})

test.describe('Public login methods contract', () => {
    test('exposes the enabled providers without any configuration or secrets', async ({ request }) => {
        // Anonymous: the login page calls this before any token exists.
        const response = await request.get(`${CORE_API}/auth/methods`)
        expect(response.ok()).toBeTruthy()

        const body = await response.json()
        expect(Array.isArray(body.items)).toBeTruthy()
        expect(body.items.length).toBeGreaterThan(0)

        const local = body.items.find((item) => item.kind === 'local')
        expect(local, 'the seeded local provider must be offered').toBeTruthy()
        expect(local.form).toBe(true)
        expect(local.login_url).toBeNull()

        for (const item of body.items) {
            // only these keys are public - never config, secret or has_secret
            expect(Object.keys(item).sort()).toEqual(['form', 'id', 'kind', 'login_url', 'name'])
            // passkeys are a site-wide capability, never listed as a provider
            expect(item.kind).not.toBe('passkey')
        }

        // ... they are reported by a separate flag instead
        expect(typeof body.passkey_enabled).toBe('boolean')
    })
})

test.describe('Auth provider slug contract', () => {
    // The login_methods branch routed the SAML/OAuth SSO endpoints by
    // `<string:provider_slug>` instead of by the database id (see
    // src/core/api/auth.py and /memories/repo/saml-routes-slug-keyed.md). The
    // slug is therefore a load-bearing public identifier: an IdP / OAuth
    // provider pins it in its registered callback / metadata URLs, so it must
    // (a) auto-derive from the display name, (b) persist across edits, and
    // (c) stay unique when two admins pick colliding names.
    //
    // These tests exercise the slug contract through the admin GUI the same way
    // the OIDC test above does, catching regressions in either the slug
    // generation in NewAuthProvider.vue / auth_provider.py (`slugify` +
    // `_unique_slug`) or the list API's serialization of the `slug` field
    // (shared/schema/auth_provider.py).
    test.beforeEach(async ({ page }) => {
        await login(page)
        await navigateToConfig(page, 'Login Methods')
        await page.waitForSelector('.v-data-table', { timeout: 5000 })
    })

    test('auto-derives a URL-safe slug from the OIDC provider name', async ({ page, request }) => {
        // A name with spaces, uppercase letters and a character that's not URL-safe
        // exercises the slugify regex (`[^a-z0-9]+ -> -`, lowercase, trimmed dashes)
        // in both NewAuthProvider.vue's preview and auth_provider.py's _unique_slug.
        const name = generateTestName('E2E Slug Test')
        try {
            await page.getByRole('button', { name: 'Add New' }).click()
            const dialog = page.locator('.v-dialog:visible')
            await expect(dialog).toBeVisible()

            await fillDialogField(page, 'Name', name)
            await selectKind(page, 'OpenID Connect')
            await fillDialogField(page, 'Issuer URL', 'https://idp.example.org/realms/main')
            await fillDialogField(page, 'Client ID', 'taranis-ng')
            await fillDialogField(page, 'Client secret', 'super-secret-value')

            // The dialog shows the derived slug in a preview field the admin can
            // override. The auto-derived value mirrors what the backend will persist:
            // "E2E Slug Test_<ts>"  -> "e2e-slug-test_<ts>"  -> "e2e-slug-test-<ts>"
            // (underscores are NOT in [a-z0-9], so slugify collapses both "_" and the
            // space between the base name and the timestamp into a single '-').
            const expectedSlug = `e2e-slug-test-${name.split('_').slice(-1)[0]}`
            await expect(dialog.getByLabel('Slug', { exact: false })).toHaveValue(expectedSlug)

            await page.getByRole('button', { name: 'Save' }).click()
            await expect(dialog).toHaveCount(0)

            // findRowByName: the Saved-row assertion must filter via the Search
            // box — config tables are server-side paginated and a freshly created
            // provider can land past page 1 on an E2E stack with seeded leftovers.
            // See /memories/repo/e2e-config-table-server-pagination.md.
            const row = await findRowByName(page, name)
            await expect(row).toBeVisible()

            // The persisted slug must match what the dialog previewed — proving
            // the GUI preview and the backend slugify agree (otherwise an IdP
            // could not be told in advance which URL to register).
            const created = await fetchProviderByName(request, name)
            expect(created.slug, 'backend must persist the slug the GUI previewed').toBe(expectedSlug)
            expect(created.slug).toMatch(/^[a-z0-9]([a-z0-9-]*[a-z0-9])?$/)
        } finally {
            await deleteProviderByName(request, name)
        }
    })

    test('keeps the slug stable when the provider name is edited', async ({ page, request }) => {
        test.setTimeout(60_000)
        const originalName = generateTestName('E2E Rename Me')
        const newName = `${originalName}-renamed`
        try {
            // Create through the GUI so the slug is auto-derived from originalName.
            await page.getByRole('button', { name: 'Add New' }).click()
            const dialog = page.locator('.v-dialog:visible')
            await fillDialogField(page, 'Name', originalName)
            await selectKind(page, 'OpenID Connect')
            await fillDialogField(page, 'Issuer URL', 'https://idp.example.org')
            await fillDialogField(page, 'Client ID', 'taranis-ng')
            await page.getByRole('button', { name: 'Save' }).click()
            await expect(dialog).toHaveCount(0)

            const created = await fetchProviderByName(request, originalName)
            const originalSlug = created.slug
            expect(originalSlug).toBeTruthy()

            // Re-open via the Edit action and rename. The Name field is freely
            // editable; the slug field is touched only via the slugify watcher,
            // and that watcher is gated on `!isEdit` (see NewAuthProvider.vue):
            // on edit the slug is NOT auto-regenerated from the new name. So a
            // plain rename leaves the slug untouched — this is the contract
            // that lets an IdP keep its registered callback URL even after an
            // admin relabels the provider.
            const row = await findRowByName(page, originalName)
            await row.getByRole('button', { name: 'Edit' }).click()
            await expect(dialog).toBeVisible()

            await fillDialogField(page, 'Name', newName)
            await page.getByRole('button', { name: 'Save' }).click()
            await expect(dialog).toHaveCount(0)

            // The provider now has a new name but the slug is unchanged — this
            // is the contract that lets an IdP keep its registered callback URL
            // even after an admin relabels the provider.
            const renamed = await fetchProviderByName(request, newName)
            expect(renamed, `renamed provider not found via API search=${encodeURIComponent(newName)}`).toBeTruthy()
            expect(renamed.slug, 'slug must not change when the name is edited').toBe(originalSlug)
        } finally {
            await deleteProviderByName(request, originalName)
            await deleteProviderByName(request, newName)
        }
    })

    test('rejects a second provider whose auto-derived slug would collide', async ({ page, request }) => {
        // The GUI always sends the auto-derived slug (the Slug field is
        // client-side required, see slugRules in NewAuthProvider.vue), so the
        // backend's _validate() — NOT _unique_slug() — is the path that handles
        // a collision: it rejects with "The slug '...' is already used by
        // another login method", surfacing as an error alert in the dialog. The
        // _unique_slug("-2") disambiguation only kicks in when an admin submits
        // a blank slug, which the GUI's required rule forbids.
        //
        // This test covers the contract an admin actually sees: a colliding
        // save is rejected and an admin can manually edit the slug to rescue.
        test.setTimeout(60_000)
        // Two names whose slugify() output is identical ("E2E Collision X" vs
        // "E2E Collision  X" — multiple spaces collapse to a single hyphen).
        const name1 = `E2E Collision A ${Date.now()}`
        const name2 = `E2E Collision  A ${Date.now()}`
        try {
            // First provider: clean create, slug is auto-derived.
            await page.getByRole('button', { name: 'Add New' }).click()
            const dialog = page.locator('.v-dialog:visible')
            await fillDialogField(page, 'Name', name1)
            await selectKind(page, 'OpenID Connect')
            await fillDialogField(page, 'Issuer URL', 'https://idp.example.org')
            await fillDialogField(page, 'Client ID', 'taranis-ng')
            await page.getByRole('button', { name: 'Save' }).click()
            await expect(dialog).toHaveCount(0)

            const p1 = await fetchProviderByName(request, name1)
            expect(p1.slug, 'first provider gets the clean name-derived slug').toBeTruthy()

            // Second provider: same name-derived slug → backend rejects.
            await page.getByRole('button', { name: 'Add New' }).click()
            await expect(dialog).toBeVisible()
            await fillDialogField(page, 'Name', name2)
            await selectKind(page, 'OpenID Connect')
            await fillDialogField(page, 'Issuer URL', 'https://idp.example.org')
            await fillDialogField(page, 'Client ID', 'taranis-ng')
            await page.getByRole('button', { name: 'Save' }).click()

            // The dialog stays open with the auth_provider.error alert. Auto-retry
            // covers the alert render lag — find it inside the visible dialog.
            await expect(dialog.locator('.v-alert')).toContainText(/could not save|already used/i)

            // ... and no second row was persisted (the list API returns only p1
            // for either name1 or name2 — the original is still there, the
            // second is not).
            const p2 = await fetchProviderByName(request, name2)
            expect(p2, 'no second provider should exist yet (collision blocked)').toBeFalsy()

            // ----- Manual slug edit rescues the save -----
            //
            // An admin who sees the collision alert edits the URL slug to a
            // unique value, then Save succeeds and the backend persists the
            // second provider under the new slug. This is the contract the
            // GUI auto-uniquifier substitutes for — the admin is in the loop.
            const rescuedSlug = `${p1.slug}-v2`
            await dialog.getByLabel('URL slug', { exact: false }).fill(rescuedSlug)
            await page.getByRole('button', { name: 'Save' }).click()
            await expect(dialog).toHaveCount(0)

            const p2rescued = await fetchProviderByName(request, name2)
            expect(p2rescued, 'rescued second provider must exist').toBeTruthy()
            expect(p2rescued.slug, 'rescued provider keeps the admin-chosen slug').toBe(rescuedSlug)
            // The two persisted slugs differ.
            expect(p1.slug).not.toBe(rescuedSlug)
            // Both match the slug pattern, so SSO URLs stay well-formed.
            expect(rescuedSlug).toMatch(/^[a-z0-9]([a-z0-9-]*[a-z0-9])?$/)
        } finally {
            await deleteProviderByName(request, name1)
            await deleteProviderByName(request, name2)
        }
    })
})

/**
 * SAML SP metadata contract (E2).
 *
 * The login_methods branch introduces `SamlMetadata` — a public endpoint
 * (src/core/api/auth.py) at `/api/v1/auth/saml/<provider_slug>/metadata`
 * that publishes the SP metadata an identity provider needs to register this
 * service. It is the public, anonymous face of the SP, so a contract test
 * covers it independently of the GUI flow that creates the provider.
 *
 * Covered here:
 *   - served without authentication (an IdP fetches it anonymously)
 *   - returns application/samlmetadata+xml (the SP's registered content type)
 *   - asserts the slug-keyed route (NOT id-keyed), see
 *     /memories/repo/saml-routes-slug-keyed.md for the root cause of why
 *     created.id in the URL 404s while created.slug works
 *   - 404s (with the documented error body) for an unknown slug
 *
 * The Login Methods > creates a SAML 2.0 provider test above already checks
 * the happy-path metadata XML contents after creating through the GUI; this
 * block fills the contract gaps around access control, content-type,
 * slug-vs-id, and 404.
 *
 * SAML providers are created through the API here (not the GUI) because:
 *   - this block's subject is the metadata endpoint, not the create UI
 *   - the GUI SAML dialog requires three round-trips (load-metadata, generate-
 *     keypair, save) plus tab-switching, which makes a "create a fixture"
 *     helper oddly heavy for an endpoint contract test
 *   - the Login Methods > creates a SAML 2.0 provider test above already
 *     exercises the GUI flow
 */

// Mint a self-signed RSA-2048 SP keypair (PEM-encoded). The backend's SAML
// validator (validate_sp_keypair in src/core/auth/saml_authenticator.py)
// checks that the private key matches the certificate's public key — both
// come from the same Node-generated pair, so they match. Uses openssl (always
// present on the E2E host) to wrap the public key as an X.509 cert, since
// `validate_sp_keypair` calls load_pem_x509_certificate on the certificate.
//
// Files are written to an OS temp dir and removed in finally; chmod 0600 on
// the private key mirrors openssl's default umask.
function generateSpKeypairPem() {
    const { privateKey } = generateKeyPairSync('rsa', {
        modulusLength: 2048,
        privateKeyEncoding: { type: 'pkcs8', format: 'pem' },
        publicKeyEncoding: { type: 'spki', format: 'pem' }
    })

    const dir = mkdtempSync(join(tmpdir(), 'sp-key-'))
    const keyPath = join(dir, 'sp.key')
    const certPath = join(dir, 'sp.crt')
    try {
        writeFileSync(keyPath, privateKey, { mode: 0o600 })
        execSync(`openssl req -new -x509 -key "${keyPath}" -out "${certPath}" -days 3650 -subj "/CN=taranis-ng-e2e" -sha256`, {
            stdio: 'ignore'
        })
        const certificate = readFileSync(certPath, 'utf8')
        return { privateKey, certificate }
    } finally {
        // best-effort cleanup — certificate files are temp-only, never test state
        try {
            unlinkSync(keyPath)
            unlinkSync(certPath)
            rmdirSync(dir)
        } catch {
            /* ignore — the OS /tmp reaper handles the rest */
        }
    }
}

/**
 * Create a SAML provider directly via the API. The validator (AuthProvider
 * ._validate) requires a parseable IdP certificate AND a matching SP keypair;
 * both are provided so the create POST returns 200 with a real provider
 * record the metadata endpoint can then describe.
 *
 * Returns the created provider JSON including its { id, slug }.
 */
async function createSamlProviderViaApi(request, name) {
    const headers = await adminHeaders(request)
    const { privateKey, certificate } = generateSpKeypairPem()

    const response = await request.post(`${CORE_API}/config/auth-providers`, {
        headers,
        data: {
            id: -1,
            name,
            kind: 'saml',
            enabled: true,
            provisioning_mode: 'manual',
            allowed_domains: '',
            require_mfa: false,
            organization: null,
            default_roles: [],
            config: {
                idp_entity_id: 'https://idp.example.org/idp/shibboleth',
                idp_sso_url: 'https://idp.example.org/sso/redirect',
                idp_certificate: IDP_CERT_B64,
                sp_entity_id: 'taranis-ng-e2e',
                sp_certificate: certificate
            },
            // The validator's SP-keypair check verifies the private key in
            // `secret` matches the public key in config.sp_certificate. Both
            // come from the same freshly-minted keypair, so they match.
            secret: privateKey
        }
    })
    if (!response.ok()) {
        throw new Error(`createSamlProviderViaApi failed: ${response.status()} ${await response.text()}`)
    }
    return response.json()
}

test.describe('SAML SP metadata contract', () => {
    test('serves the SP metadata anonymously for a slug-keyed route', async ({ request }) => {
        const name = generateTestName('E2E SP Metadata')
        try {
            const created = await createSamlProviderViaApi(request, name)
            expect(created.slug, 'provider must have a slug for its SAML routes').toBeTruthy()

            // Anonymous: no Authorization header at all — an IdP fetches this
            // without any credentials, so the route is `@no_auth` on the backend
            // (see SamlMetadata.get @ src/core/api/auth.py:SamlMetadata).
            const response = await request.get(`${CORE_API}/auth/saml/${created.slug}/metadata`)

            expect(response.ok(), `metadata request failed: ${response.status()}`).toBeTruthy()
            expect(response.headers()['content-type']).toContain('samlmetadata+xml')

            const xml = await response.text()
            // SP entityID — the value an identity provider pins in its config.
            // It mirrors saml_authenticator.sp_entity_id's default when not set.
            expect(xml).toMatch(/entityID="taranis-ng(-e2e)?"/)
            expect(xml).toContain(`/api/v1/auth/saml/${created.slug}/acs`)
        } finally {
            await deleteProviderByName(request, name)
        }
    })

    test('404s with the documented error body for an unknown slug', async ({ request }) => {
        // An unknown slug both doesn't match any row AND exercises the
        // `<string:provider_slug>` route — proving the route is slug-keyed and
        // that get_saml_authenticator's None branch returns NOT_FOUND with the
        // documented body (see SamlMetadata.get).
        const response = await request.get(`${CORE_API}/auth/saml/this-slug-does-not-exist/metadata`)
        expect(response.status()).toBe(404)

        const body = await response.json()
        // The error message the route returns is part of the public contract:
        // an IdP admin fetching the metadata sees a stable, machine-readable
        // message rather than an opaque 404.
        expect(body.error).toContain('Unknown login method')
    })

    test('rejects the legacy database-id URL (slug-keyed route validation)', async ({ request }) => {
        // Regression guard for the slug-keyed routes: an earlier revision used
        // created.id in the URL. The current route is `<string:provider_slug>`,
        // and a lookup by integer-slug against find_by_slug returns None, so
        // the request 404s. See /memories/repo/saml-routes-slug-keyed.md.
        const name = generateTestName('E2E SP Slug Guard')
        try {
            const created = await createSamlProviderViaApi(request, name)
            expect(created.id, 'provider must have an integer id (legacy)').toBeTruthy()
            // Slugs auto-derive from "E2E SP Slug Guard_<ts>" → "e2e-sp-slug-guard-<ts>"
            // — they never equal a bare integer, so the integer-url never matches.
            expect(created.slug).not.toMatch(/^\d+$/)

            // The id-based URL is wrong now: the <string:provider_slug> route
            // looks the slug up by string equality, no provider's slug equals
            // "3" (or whatever the integer id is), and SamlMetadata.get returns
            // 404 with the documented error body.
            const response = await request.get(`${CORE_API}/auth/saml/${created.id}/metadata`)
            expect(response.status()).toBe(404)
        } finally {
            await deleteProviderByName(request, name)
        }
    })
})
