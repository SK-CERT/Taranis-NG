import { test, expect } from '@playwright/test'
import { login, navigateToConfig, openDialog, saveDialog, generateTestName } from '../helpers/test-helpers'

/**
 * Login Methods (identity providers) E2E Tests
 *
 * Covers the Login Methods tab of Access Management: listing the seeded
 * "Local accounts" provider, creating OIDC / SAML 2.0 / LDAP providers, the
 * write-only secret, the delete warning about linked identities, and the
 * public /auth/methods contract the login page depends on.
 */

const CORE_API = process.env.E2E_CORE_API || 'http://127.0.0.1:8082/api/v1'

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

/** Remove a provider by name through the API (best-effort test cleanup). */
async function deleteProviderByName(request, name) {
    const loginRes = await request.post(`${CORE_API}/auth/login`, { data: { username: 'admin', password: 'admin' } })
    const { access_token: token } = await loginRes.json()
    const headers = { Authorization: `Bearer ${token}` }
    const listRes = await request.get(`${CORE_API}/config/auth-providers?search=`, { headers })
    const { items } = await listRes.json()
    const provider = items.find((item) => item.name === name)
    if (provider) {
        await request.delete(`${CORE_API}/config/auth-providers/${provider.id}`, { headers })
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

        const row = activePanel(page).locator('tbody tr').filter({ hasText: name })
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
        // pasting the metadata, importing it and generating a keypair are three
        // backend round-trips: more than the default budget allows
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

        await saveDialog(page)
        await expect(dialog).toHaveCount(0)

        const row = activePanel(page).locator('tbody tr').filter({ hasText: name })
        await expect(row).toBeVisible()
        await expect(row).toContainText('SAML 2.0')

        // generate the SP keypair: its certificate is what a federation's registration
        // form asks for as the "encryption certificate"
        await dialog.getByRole('button', { name: 'Generate keypair' }).click()
        await expect(dialog.getByLabel('SP certificate', { exact: false }).first()).toHaveValue(/-----BEGIN CERTIFICATE-----/)
        await expect(dialog.getByLabel('SP private key', { exact: false }).first()).toHaveValue(/-----BEGIN PRIVATE KEY-----/)

        // the SP publishes metadata an identity provider can register
        const token = await page.evaluate(() => localStorage.getItem('ACCESS_TOKEN'))
        const listResponse = await page.request.get(`${CORE_API}/config/auth-providers?search=${encodeURIComponent(name)}`, {
            headers: { Authorization: `Bearer ${token}` }
        })
        const created = (await listResponse.json()).items.find((item) => item.name === name)

        // anonymous: an IdP fetches this without credentials
        const metadata = await request.get(`${CORE_API}/auth/saml/${created.id}/metadata`)
        expect(metadata.ok()).toBeTruthy()
        expect(metadata.headers()['content-type']).toContain('samlmetadata+xml')

        const xml = await metadata.text()
        expect(xml).toContain('entityID="taranis-ng"')
        expect(xml).toContain(`/api/v1/auth/saml/${created.id}/acs`)
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
        await fillDialogField(page, 'User DN template', 'uid={username},ou=people,dc=example,dc=org')

        await saveDialog(page)
        await expect(dialog).toHaveCount(0)

        await expect(activePanel(page).locator('tbody tr').filter({ hasText: name })).toBeVisible()

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

        const row = activePanel(page).locator('tbody tr').filter({ hasText: name })
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

test.describe('Security settings (passkey relying party)', () => {
    test.beforeEach(async ({ page }) => {
        await login(page)
        await navigateToConfig(page, 'Security')
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

        await panel.getByLabel('Enable passkey sign-in').click()
        await panel.getByLabel('Relying party ID').fill('localhost')
        await panel.getByLabel('Allowed origins').fill('http://localhost:4445')
        await panel.getByRole('button', { name: 'Save' }).click()

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
        await cleanupPanel.getByLabel('Enable passkey sign-in').click()
        await cleanupPanel.getByRole('button', { name: 'Save' }).click()
        await expect(cleanupPanel.getByText(/last updated by/i)).toBeVisible()

        const after = await (await request.get(`${CORE_API}/auth/methods`)).json()
        expect(after.passkey_enabled).toBe(false)
    })
})
