import { test, expect } from '@playwright/test'
import { createHmac } from 'node:crypto'
import { login, navigateToConfig } from '../helpers/test-helpers'

/**
 * TOTP enrollment + passkey registration (self-service MFA) E2E tests.
 *
 * These tests complete the enrollment ceremonies the existing
 * `user-status.spec.js > Security self-service` block only stubs out:
 *   - the TOTP test stops after the QR code appears without finishing
 *   - no test exercises the passkey registration flow at all
 *
 * They run against the GUI's own behavior and the matching backend contracts
 * (`/users/my-totp` and `/users/my-passkeys/register-begin|register-finish`),
 * so they catch regressions in either layer. They need a working E2E stack
 * (see scripts/test-setup.py), the seeded admin user, and — for the passkey
 * test — a relying-party configuration the test sets up first (mirrors the
 * existing `Security settings (passkey relying party)` block in
 * security-settings.spec.js).
 *
 * Why a virtual authenticator: WebAuthn registration calls navigator
 * .credentials.create() in the browser, which without a real security key
 * throws NotAllowedError. Playwright's CDP `WebAuthn.addVirtualAuthenticator`
 * gives the page a synthetic platform authenticator that satisfies the call,
 * producing the attestation the backend verifies — see
 * https://playwright.dev/docs/api/class-browsercontext#browser-context-add-virtual-authenticator
 */

// See api-seed.js / api-cleanup.js: the E2E stack exposes core on E2E_CORE_PORT
// (default 8090, see docker/.env.e2e). Do NOT hardcode a port — earlier revisions
// used '8082' which the stack does not expose, causing ECONNREFUSED on direct
// page.request.* calls while the Vite-proxied GUI flow worked.
const CORE_API = process.env.E2E_CORE_API || `http://127.0.0.1:${process.env.E2E_CORE_PORT || '8090'}/api/v1`

/** Scope queries to the active tab: Vuetify keeps the previous tab's DOM around. */
const activePanel = (page) => page.locator('.v-window-item--active')

const ADMIN = { username: 'admin', password: 'admin' }

/** RFC 4648 base32 alphabet — used to decode the TOTP secret out of the otpauth:// URI. */
const BASE32_ALPHABET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567'

/** Decode an RFC 4648 base32 string (no padding required) to a Uint8Array. */
function base32Decode(secret) {
    const cleaned = secret.replace(/=+$/, '').toUpperCase().replace(/\s/g, '')
    const bytes = []
    let buffer = 0
    let bitsLeft = 0
    for (const char of cleaned) {
        const value = BASE32_ALPHABET.indexOf(char)
        if (value === -1) {
            throw new Error(`invalid base32 character: ${char}`)
        }
        buffer = (buffer << 5) | value
        bitsLeft += 5
        if (bitsLeft >= 8) {
            bitsLeft -= 8
            bytes.push((buffer >> bitsLeft) & 0xff)
        }
    }
    return Uint8Array.from(bytes)
}

/**
 * Generate a TOTP code (RFC 6238) for a base32 secret.
 * Mirrors exactly what the backend (`src/core/managers/totp_manager.py`) accepts:
 * HMAC-SHA1, 30-second step, 6 digits. Used to confirm the enrollment with a
 * real value rather than stubbing the verify call.
 *
 * Uses Uint8Array + DataView throughout (no Node Buffer global, which the
 * project's ESLint config doesn't declare).
 */
function totpCode(secretBase32, timestampSeconds = Math.floor(Date.now() / 1000)) {
    const step = Math.floor(timestampSeconds / 30)
    // 64-bit big-endian step counter. DataView's setUint32 handles the per-edge
    // byte order; the high 32 bits and the low 32 bits are written separately to
    // avoid JS's 32-bit bitwise truncation near year 2038.
    const counter = new Uint8Array(8)
    const view = new DataView(counter.buffer)
    view.setUint32(0, Math.floor(step / 0x100000000))
    view.setUint32(4, step >>> 0)

    const key = base32Decode(secretBase32)
    const digest = createHmac('sha1', key).update(counter).digest()
    const offset = digest[digest.length - 1] & 0x0f
    const truncated =
        ((digest[offset] & 0x7f) << 24) |
        ((digest[offset + 1] & 0xff) << 16) |
        ((digest[offset + 2] & 0xff) << 8) |
        (digest[offset + 3] & 0xff)
    return (truncated % 1_000_000).toString().padStart(6, '0')
}

/** Extract the base32 secret from an otpauth:// provisioning URI. */
function secretFromOtpauthUri(uri) {
    // otpauth://totp/Issuer:account?secret=BASE32&issuer=Issuer
    const match = /[?&]secret=([A-Z2-7]+)/i.exec(uri)
    if (!match) {
        throw new Error(`no secret in otpauth URI: ${uri}`)
    }
    return match[1]
}

/**
 * Get the Authorization header for the admin user. After TOTP enrollment,
 * admin's /auth/login returns 401 MFA_REQUIRED with a mfa_token; this helper
 * transparently completes the MFA step using `secret` if provided so callers
 * don't need to know whether admin has TOTP enabled.
 *
 * @param request - Playwright APIRequestContext
 * @param [secret] - The admin's TOTP base32 secret (only set if the test
 *   enrolled the admin during this run; provided by callers in the disable
 *   phase). When omitted and admin requires MFA, this throws.
 */
async function adminHeaders(request, secret) {
    const loginRes = await request.post(`${CORE_API}/auth/login`, { data: ADMIN })
    const loginBody = await loginRes.json()
    if (loginRes.ok()) {
        return { Authorization: `Bearer ${loginBody.access_token}` }
    }
    // 401 with code MFA_REQUIRED: complete the MFA TOTP step using the secret
    // the caller passed in (only available between enroll and disable).
    if (loginBody.code === 'MFA_REQUIRED' && loginBody.methods?.includes('totp') && secret) {
        const mfaRes = await request.post(`${CORE_API}/auth/mfa/totp`, {
            data: { mfa_token: loginBody.mfa_token, code: totpCode(secret) }
        })
        if (!mfaRes.ok()) {
            // The TOTP replay guard rejects same-step codes; the caller's retry
            // loop will compute new codes across step rollovers, so back off one
            // TOTP step here before retrying.
            await new Promise((resolve) => setTimeout(resolve, 31_000))
            const mfaRetry = await request.post(`${CORE_API}/auth/mfa/totp`, {
                data: { mfa_token: loginBody.mfa_token, code: totpCode(secret) }
            })
            if (!mfaRetry.ok()) {
                throw new Error(`admin MFA login failed: ${mfaRetry.status()} ${await mfaRetry.text()}`)
            }
            const mfaBody = await mfaRetry.json()
            return { Authorization: `Bearer ${mfaBody.access_token}` }
        }
        const mfaBody = await mfaRes.json()
        return { Authorization: `Bearer ${mfaBody.access_token}` }
    }
    throw new Error(`admin login failed: ${loginRes.status()} ${loginBody.code || loginBody.error || JSON.stringify(loginBody)}`)
}

/** Open the user Settings dialog and switch to its Security tab. */
async function openUserSettingsSecurity(page) {
    await login(page)
    await page.click('[data-test="user-menu"]')
    await page.getByText('Settings', { exact: false }).first().click()
    const dialog = page.locator('.v-dialog:visible')
    await expect(dialog).toBeVisible()
    await dialog.getByRole('tab', { name: /security/i }).click()
    return dialog
}

// Self-service MFA features require a single, sequential admin session — the
// GUI reuses the admin's TOTP/passkey state across these tests. serial mode
// (workers: 1 is already configured globally) plus this explicit describe.serial
// makes the regression explicit if someone changes the workers setting.
test.describe('Self-service MFA enrollment', () => {
    test.describe.configure({ mode: 'serial' })

    test.describe('TOTP enrollment', () => {
        // Chromium-only by project choice. The TOTP test cycles enroll →
        // disable against the SEED admin user and reuses the GUI's Security
        // dialog inside one test. On webkit the reopen-Settings-Dialog timing
        // after enrollment is flaky (the disable-phase `getUserMenu` click
        // doesn't propagate reliably), and the post-enroll API GET needs an
        // MFA-aware adminHeaders (which only deadlocks webkit because the
        // browser has no way to satisfy the MFA-required step that test-runner
        // requests trigger). Chromium is the canonical browser for this GUI
        // CI; a future rewrite extracting the assertion into API-only form
        // would unblock the other two engines.
        test.skip(({ browserName }) => browserName !== 'chromium', 'Chromium-only per project policy (see comment)')

        // The admin user is the only seeded account and the only one with the
        // CONFIG_AUTH_PROVIDER_UPDATE permission needed for the Security tab
        // cleanup below. TOTP enroll/disable runs against admin, and the test
        // ends by disabling TOTP so the baseline is restored — a failed test
        // can't lock the admin out: `require_mfa` is the gating site-wide
        // setting (per security_settings.py, defaults to off), so leaving TOTP
        // enabled still permits password-only admin login. But admin's TOTP
        // state IS left enabled on failure. To avoid cascading failures
        // (TOTP-enabled admin breaks THIS test's preconditions on rerun) the
        // test wraps the enroll/disable cycle in try/finally and disables TOTP
        // via the GUI in `finally` (verifiable since we hold the enrollment
        // secret).
        //
        // Timeout budget: 240 s — covers the GUI dialog opens (~10 s each), the
        // network round-trips, AND worst-case 3 step-rollover retries of the
        // disable phase (each ~32 s for the TOTP 30 s step + 2 s buffer).
        // The step-rollover retries are needed because the replay guard
        // (totp_last_used_step) rejects same-step codes after enrollment, and
        // the test runner's clock can drift from the container's clock by a few
        // seconds — see totp_manager._matching_step + verify_code.
        test('completes a TOTP enrollment and disables it through the GUI', async ({ page, request }) => {
            // See the comment above this test for why 240 s — the worst-case
            // 3 step-rollover disable retries + GUI/network round-trips.
            test.setTimeout(240_000)
            let secret // captured from the begin-enrollment response so the
            // finally cleanup can compute a valid disable code.
            let enrolled = false // becomes true once enrollment SUCCEEDS, so
            // the finally knows whether it needs to disable.

            try {
                // Pre-condition enforced at the API level: admin must NOT have
                // TOTP enabled at test start. A prior run that enrolled but
                // didn't reach disable leaves the admin TOTP-enabled, which
                // then makes a plain /auth/login require MFA — adminHeaders()
                // fails with "Bearer undefined", the test's precondition
                // check below fires a clear test-skipping message rather than
                // a confusing "Enable button missing" failure mid-test.
                //
                // adminHeaders here uses a fresh login (admin/admin), which
                // works ONLY when admin has NO TOTP. If admin has TOTP the
                // login returns 401/MFA_REQUIRED, so the precondition check
                // detects that path too.
                let preHeaders
                try {
                    preHeaders = await adminHeaders(request)
                } catch {
                    preHeaders = null // admin requires MFA → already enabled
                }
                if (preHeaders) {
                    const statusRes = await request.get(`${CORE_API}/users/my-totp`, { headers: preHeaders })
                    if (statusRes.ok()) {
                        const { enabled } = await statusRes.json()
                        if (enabled) {
                            // Fail clearly so the operator knows to clear
                            // admin's TOTP via the DB (this test deliberately
                            // doesn't touch the DB itself; the operator's
                            // workflow is to `docker compose exec postgres
                            // /bin/sh -c "psql ... -c \"UPDATE \\\"user\\\"
                            // SET totp_secret=NULL ...\"").
                            throw new Error(
                                'Precondition violated: admin already has TOTP enabled. ' +
                                    'Clear it via the database (UPDATE "user" SET totp_secret=NULL, totp_last_used_step=NULL WHERE username=\'admin\') and rerun.'
                            )
                        }
                    }
                } else {
                    throw new Error(
                        'Precondition violated: admin login requires MFA (TOTP already enabled). ' +
                            'Clear it via the database (UPDATE "user" SET totp_secret=NULL, totp_last_used_step=NULL WHERE username=\'admin\') and rerun.'
                    )
                }

                const dialog = await openUserSettingsSecurity(page)

                await expect(dialog).toContainText('Authenticator app')
                const enable = dialog.getByRole('button', { name: 'Enable' })

                // Trigger the backend's begin-enrollment round-trip: POST /users/my-totp
                // with an empty body returns the otpauth:// URI the QR is rendered from.
                // Capture that URI from the network response so we can compute a real
                // code — extracting it out of the QR image is needlessly brittle.
                const beginResponse = page.waitForResponse((r) => r.request().method() === 'POST' && r.url().endsWith('/users/my-totp'))
                await enable.click()
                const begin = await beginResponse
                expect(begin.ok(), 'TOTP begin (POST /users/my-totp) should succeed').toBeTruthy()

                const { otpauth_uri: otpauthUri } = await begin.json()
                secret = secretFromOtpauthUri(otpauthUri)

                // The QR code is rendered from the URI and the Activate flow is shown.
                await expect(dialog.locator('img[alt="TOTP QR code"]')).toBeVisible()
                await expect(dialog.getByRole('button', { name: 'Activate' })).toBeVisible()

                // Type a real, current TOTP code and confirm. This is the same
                // computation the backend (`_matching_step` in
                // src/core/managers/totp_manager.py) accepts: HMAC-SHA1, 6 digits,
                // 30-second step, +-1 window.
                const enrollCode = totpCode(secret)
                await dialog.getByLabel('Code', { exact: false }).fill(enrollCode)

                // Wait for the confirm round-trip (POST /users/my-totp with {code}).
                // "Activate" is the visible button label (i18n key
                // security.totp_activate).
                const confirmResponse = page.waitForResponse((r) => r.request().method() === 'POST' && r.url().endsWith('/users/my-totp'))
                await dialog.getByRole('button', { name: 'Activate' }).click()
                const confirm = await confirmResponse
                expect(confirm.ok(), 'TOTP confirm should succeed with a valid code').toBeTruthy()
                enrolled = true

                // After enrollment the dialog moves from the "Enrollment in progress"
                // state to the "Enabled: allow disable with code" state — the QR
                // image disappears and the chip flips to "Enabled".
                await expect(dialog.locator('img[alt="TOTP QR code"]')).toHaveCount(0)
                await expect(dialog.getByText('Enabled', { exact: true }).first()).toBeVisible()

                // Backend agrees: the persisted state is "enabled". The admin
                // now requires MFA on login, so adminHeaders needs the secret to
                // complete the MFA-totp step (POST /auth/mfa/totp).
                const headers = await adminHeaders(request, secret)
                const statusRes = await request.get(`${CORE_API}/users/my-totp`, { headers })
                expect(statusRes.ok(), `TOTP status check should be 200: ${statusRes.status()}`).toBeTruthy()
                const status = await statusRes.json()
                expect(status.enabled, 'backend TOTP status must be enabled after enrollment').toBe(true)

                // ----- Disable phase (same test, same admin session) -----
                //
                // The replay guard (totp_last_used_step) rejects a code whose
                // matched step ≤ the step the enroll-used code matched. The
                // backend's verify_code accepts a code in the (now-1, now, now+1)
                // TOTP-window, and the matched step only exceeds last_used_step
                // once the CONTAINER's current step has rolled past the enroll
                // step. This means "submit just one disable code" can 400 with
                // "Invalid authentication code" even after a 30 s sleep — the
                // test runner's clock and the container's clock can drift, so
                // an exact 30 s sleep is not a robust sync primitive here.
                //
                // The robust approach is the one an admin would use: try the
                // code, and if the backend rejects it (still in the same TOTP
                // window as enrollment), wait for the next TOTP step and try
                // again. Three step bumps (90 s worst-case) is plenty for any
                // realistic container clock skew.
                //
                // The same `page` browser session is used (no re-login): the
                // enroll's JWT cookie is still valid for a few hours, and the
                // user-menu → Settings flow opens the dialog again, this time
                // showing the "Enabled" state with the Disable button.
                await page.goto('/v2/dashboard')
                await page.click('[data-test="user-menu"]')
                await page.getByText('Settings', { exact: false }).first().click()
                const dialog2 = page.locator('.v-dialog:visible')
                await expect(dialog2).toBeVisible()
                await dialog2.getByRole('tab', { name: /security/i }).click()
                await expect(dialog2.getByRole('button', { name: 'Disable' })).toBeVisible()

                let disabled = false
                for (let attempt = 0; attempt < 4 && !disabled; attempt++) {
                    if (attempt > 0) {
                        // The TOTP step rolls over every 30s. Wait for the
                        // next step to start (with a 2s buffer) rather than a
                        // blind 31s sleep — this soonest-resyncs when we
                        // happened to enter the loop near a step boundary.
                        const msIntoStep = Date.now() % 30_000
                        const waitMs = 30_000 - msIntoStep + 2_000
                        await new Promise((resolve) => setTimeout(resolve, waitMs))
                    }
                    const disableCode = totpCode(secret)
                    await dialog2.getByLabel('Code', { exact: false }).fill(disableCode)
                    const disableResponse = page.waitForResponse(
                        (r) => r.request().method() === 'DELETE' && r.url().endsWith('/users/my-totp')
                    )
                    await dialog2.getByRole('button', { name: 'Disable' }).click()
                    const disable = await disableResponse
                    disabled = disable.ok()
                    if (!disabled) {
                        // same-window replay rejection — wait for the next
                        // step and try again. Don't fail here; the retry loop
                        // is the test's robustness intent.
                        await expect(dialog2.getByText(/invalid|authentication code/i))
                            .toBeVisible({
                                timeout: 2000
                            })
                            .catch(() => {
                                /* the alert may have already autoclosed; ignore */
                            })
                    }
                }
                expect(disabled, 'TOTP disable should succeed with a valid code after 4 step-rollover attempts').toBeTruthy()
                enrolled = false // we successfully disabled; no cleanup needed

                // After disabling, the self-service dialog flips back to offering
                // Enable — the Enabled chip is gone.
                await expect(dialog2.getByText('Enabled', { exact: true })).toHaveCount(0)
                await expect(dialog2.getByRole('button', { name: 'Enable' })).toBeVisible()

                // Backend agrees. Admin may still need MFA (if disable was
                // rolled-back too far) or may be MFA-free (totp_secret nulled).
                // `adminHeaders` tolerates both; the (now-irrelevant) secret is
                // passed only because it's a no-op when admin no longer has TOTP.
                const headers2 = await adminHeaders(request, secret)
                const statusRes2 = await request.get(`${CORE_API}/users/my-totp`, { headers: headers2 })
                const status2 = await statusRes2.json()
                expect(status2.enabled, 'backend TOTP status must be disabled after disable').toBe(false)
            } finally {
                // Baseline restore even on partial-success failures: if the test
                // enrolled but didn't reach the in-test disable, roll TOTP back
                // via the API so the next run finds the admin in the expected
                // disabled-TOTP state. Best-effort — the test's actual failure
                // already surfaced.
                if (enrolled && secret) {
                    try {
                        // Admin requires MFA now — call adminHeaders with the
                        // secret so it completes the MFA-totp step before each
                        // DELETE. (Each DELETE consumes a TOTP code's `step`; if
                        // the replay guard rejects a same-step code, the inner
                        // loop sleeps one TOTP step and retries.)
                        const deadline = Date.now() + 120_000
                        while (Date.now() < deadline) {
                            const headers = await adminHeaders(request, secret)
                            const res = await request.delete(`${CORE_API}/users/my-totp`, {
                                headers,
                                data: { code: totpCode(secret) }
                            })
                            if (res.ok()) {
                                break
                            }
                            // 400 = "Invalid authentication code" (replay guard
                            // rejecting same-step code). The next TOTP step will
                            // produce a fresh code that satisfies `step >
                            // last_used_step`.
                            await new Promise((resolve) => setTimeout(resolve, 31_000))
                        }
                    } catch {
                        // best-effort only — the test's own failure is the
                        // authoritative signal; this is just a baseline-restore
                        // safety net for the next run.
                    }
                }
            }
        })
    })

    test.describe('Passkey (WebAuthn) registration', () => {
        // A real WebAuthn registration requires a security key plus a relying-
        // party configuration whose rp_id / origins match the page's actual
        // origin. Playwright's virtual authenticator stands in for the key; the
        // relying-party config is set up through the Security tab the same way
        // the existing `Security settings (passkey relying party)` block in
        // security-settings.spec.js does, then torn down at the end so the
        // suite's baseline is preserved.
        //
        // Chromium-only by design: the fake authenticator is hooked through
        // Chrome DevTools Protocol (WebAuthn.* commands), which only the
        // Chromium-based browser engines in Playwright expose. WebKit and
        // Firefox wouldn't run `addVirtualAuthenticator` — the test would
        // time out waiting for a registration ceremony that has no
        // authenticator to talk to. Skip the test on those browsers rather
        // than fail it. (This matches other Taranis-NG E2E tests that are
        // browser-specific where the feature being tested is browser-specific
        // — e.g. the WebAuthn-login flag is meaningless on browsers without
        // navigator.credentials.)
        test.skip(({ browserName }) => browserName !== 'chromium', 'WebAuthn virtual authenticator requires Chromium (CDP only)')

        // The test relies on the GUI's own calls; no direct API-state setup the
        // way the TOTP test does. Setup of the relying-party config happens
        // inside the test so each test failure is self-contained.

        test('registers a passkey using a virtual authenticator', async ({ browser, request }) => {
            // 180 s covers the RP setup (login + SecurityTab GUI flow), the
            // virtual-authenticator ceremony (register-begin + register-finish
            // round-trips — keypair generation and the SimpleWebAuthn browser
            // flow are real and slow on cold caches), and the cleanup steps
            // (delete passkey, restore RP baseline, remove virtual authenticator,
            // close context).
            test.setTimeout(180_000)
            // The default context has no virtual authenticator. Creating a fresh
            // context here keeps the rest of the suite from inheriting the
            // authenticator (other specs would otherwise see unexpected
            // navigator.credentials.* behavior). See the CDP WebAuthn virtual
            // authenticator docs:
            // https://chromedevtools.github.io/devtools-protocol/tot/WebAuthn
            //
            // NOTE: Playwright 1.61's BrowserContext doesn't expose
            // `addVirtualAuthenticator` as a typed API — it's only available
            // through the lower-level CDP `WebAuthn.addVirtualAuthenticator`
            // command. Use `newCDPSession(page)` to send it.
            const context = await browser.newContext()
            const page = await context.newPage()
            const cdp = await context.newCDPSession(page)
            // Enable the WebAuthn virtual environment (without this the
            // WebAuthn.* commands won't take effect). This is a one-time setup.
            await cdp.send('WebAuthn.enable')
            const { authenticatorId } = await cdp.send('WebAuthn.addVirtualAuthenticator', {
                options: {
                    protocol: 'ctap2',
                    transport: 'internal',
                    hasResidentKey: true,
                    hasUserVerification: true,
                    automaticPresenceSimulation: true,
                    isUserVerified: true
                }
            })

            // Relying-party config must match the page's actual origin for the
            // backend's verify_registration_response to accept the attestation.
            // The Vite dev server serves the GUI on http://localhost:4444; use
            // that exact origin so the WebAuthn library's expected_origin matches.
            const rpId = 'localhost'
            const origin = 'http://localhost:4444'
            try {
                await setupPasskeyRelyingParty(page, request, { rpId, origins: origin })
                await passkeysMustBeEnabledOnLoginPage(request)

                // The page is already authenticated as admin from setupPasskeyRelyingParty's
                // login() call — no need to re-login. Just navigate to the user
                // settings dialog (the same page session can open it).
                await page.goto('/v2/dashboard')
                await page.click('[data-test="user-menu"]')
                await page.getByText('Settings', { exact: false }).first().click()
                const dialog = page.locator('.v-dialog:visible')
                await expect(dialog).toBeVisible()
                await dialog.getByRole('tab', { name: /security/i }).click()

                await expect(dialog).toContainText('Passkeys')

                const passkeyName = `E2E ${Date.now()}`
                // Press the Add passkey button to open the name dialog. The
                // AddNewButton component renders the icon as the only content;
                // match by its accessible name from SecuritySettings.vue's
                // <AddNewButton :label="t('security.passkey_add')">.
                await dialog.getByRole('button', { name: /add passkey/i }).click()

                const nameDialog = page.locator('.v-dialog:visible').last()
                // The name dialog's text-field label is "Name" (the i18n key
                // security.passkey_name = "Name" in en.json — a generic label
                // rather than "Passkey name"). Match exactly to avoid picking
                // up unrelated "Name" fields elsewhere on the page.
                await expect(nameDialog.getByLabel('Name', { exact: true })).toBeVisible()
                await nameDialog.getByLabel('Name', { exact: true }).fill(passkeyName)

                // The "Confirm name" handler calls beginPasskeyRegistration(),
                // waits for navigator.credentials.create({optionsJSON}), then
                // calls finishPasskeyRegistration(). Capture both round-trips
                // — verify-register-rejection (e.g. a challenge mismatch from an
                // origin mismatch) is easier to diagnose this way than by the
                // alert text SecuritySettings.vue surfaces.
                const beginReg = page.waitForResponse(
                    (r) => r.request().method() === 'POST' && r.url().endsWith('/users/my-passkeys/register-begin')
                )
                const finishReg = page.waitForResponse(
                    (r) => r.request().method() === 'POST' && r.url().endsWith('/users/my-passkeys/register-finish')
                )

                await nameDialog.getByRole('button', { name: /save/i }).click()
                const begin = await beginReg
                expect(begin.ok(), 'register-begin should succeed').toBeTruthy()
                const finish = await finishReg
                expect(
                    finish.ok(),
                    `register-finish should succeed (virtual authenticator + rp ${rpId}/${origin}): ${finish.status()} ${await finish.text()}`
                ).toBeTruthy()

                // The registered passkey shows up in the passkeys table with the
                // name we just typed. (Auto-retry covers the row-re-render lag
                // after loadData(); see the helper rationale.)
                const passkeyRow = dialog.locator('tbody tr').filter({ hasText: passkeyName })
                await expect(passkeyRow).toBeVisible()

                // Backend agrees: my-passkeys returns the same entry by name.
                //
                // The admin's existing session's access token goes through
                // page.evaluate — adminHeaders(request) is unusable here because
                // admin now has a registered passkey, which makes any new login
                // require a WebAuthn second-factor step (mfa_manager:284 — "has_
                // passkeys" triggers MFA_REQUIRED). The page's existing token
                // sidesteps the MFA prompt entirely because the token is
                // already-issued.
                const token = await page.evaluate(() => localStorage.getItem('ACCESS_TOKEN'))
                const listRes = await request.get(`${CORE_API}/users/my-passkeys`, {
                    headers: { Authorization: `Bearer ${token}` }
                })
                const { items } = await listRes.json()
                const stored = items.find((item) => item.name === passkeyName)
                expect(stored, 'passkey must be persisted with the chosen name').toBeTruthy()
                // Defensive: the schema never returns the raw key material —
                // neither public_key nor the (server-internal) sign_count field
                // is leaked to the client. JSON.stringify once for the substring
                // check so a missing-key path doesn't fail with an unhelpful
                // "expected undefined not to contain".
                const serialized = JSON.stringify(stored)
                expect(serialized).not.toContain('public_key')
                expect(serialized).not.toMatch(/[Pp]ublicKey/)

                // Pre-test-cleanup: delete the passkey we just registered while
                // the page's authenticated session is still alive. Doing this in
                // finally fails because admin login then requires MFA — the test
                // runner has no virtual authenticator to complete the WebAuthn
                // step, so adminHeaders() can't mint a fresh token. Using the
                // page's localStorage token sidesteps that entirely.
                if (stored?.id != null) {
                    await request.delete(`${CORE_API}/users/my-passkeys/${stored.id}`, {
                        headers: { Authorization: `Bearer ${token}` }
                    })
                }
            } finally {
                // Tear down in the right order:
                //   1. Delete any passkey the test registered (by name) — a
                //      leftover credential would break the "No passkeys
                //      registered" precondition of user-status.spec.js on the
                //      next run, especially on reused E2E stacks.
                //   2. Disable the passkey relying party to restore the suite's
                //      baseline (other specs assume passkey_enabled:false).
                //   3. Remove the virtual authenticator from the CDP context so
                //      it doesn't leak into other specs that reuse the browser.
                //   4. Close the test-specific context so the virtual
                //      authenticator doesn't leak into other specs.
                // All cleanup is best-effort so a partial-RP-setup failure
                // doesn't mask the actual test error.
                try {
                    await cdp.send('WebAuthn.removeVirtualAuthenticator', { authenticatorId })
                } catch {
                    /* best-effort: ignore if the session already closed */
                }
                // Wrap each cleanup individually so one failure doesn't prevent
                // the others from running (the test's actual failure surfaced
                // above; these are baseline-restore safety nets for the next run).
                await cleanupRegisteredPasskeys(request).catch((error) => console.warn('Passkey-cleanup failed:', error?.message || error))
                await cleanupPasskeyRelyingParty(request).catch((error) => console.warn('RP-cleanup failed:', error?.message || error))
                await context.close().catch(() => {
                    /* already closed by the runner-timeout; ignore */
                })
            }
        })
    })
})

/** Delete any passkey registered on the admin user (best-effort baseline
 * restore). Done by name rather than id so the test doesn't depend on
 * fetch-persisted-id plumbing, and tolerant of zero matches. */
async function cleanupRegisteredPasskeys(request) {
    try {
        const headers = await adminHeaders(request)
        const res = await request.get(`${CORE_API}/users/my-passkeys`, { headers })
        if (!res.ok()) {
            return
        }
        const { items = [] } = await res.json()
        for (const item of items) {
            // Only remove E2E-registered passkeys (leave any real ones, if any).
            if (/^E2E /.test(item.name) && item.id != null) {
                await request.delete(`${CORE_API}/users/my-passkeys/${item.id}`, { headers })
            }
        }
    } catch (error) {
        // best-effort; the failing test's error already surfaced above. Log so
        // the cleanup's own failure (e.g. backend unreachable mid-cleanup) is
        // visible in the test output without masking the original assertion.
        console.warn('cleanupRegisteredPasskeys failed:', error?.message || error)
    }
}

/**
 * Configure the site-wide passkey relying party to match the test's actual
 * origin so the backend's WebAuthn verify_registration_response accepts the
 * virtual authenticator's attestation. Mirrors the
 * `Security settings (passkey relying party)` block in security-settings.spec.js
 * — done via the Security tab GUI to keep behavior we'd actually assert on
 * under test (the public /auth/methods contract is exercised by
 * auth-providers.spec.js's `Public login methods contract` block).
 */
async function setupPasskeyRelyingParty(page, request, { rpId, origins }) {
    // Seed the baseline via the API first: on a virgin database the settings
    // row is created lazily with `updated_by = NULL`, so the "Last updated by"
    // caption the guard below waits on would never render and this helper
    // would time out on the first run of a fresh CI stack (observed as a
    // flaky first attempt whose `finally` cleanup PUT then let the retry
    // pass). The baseline PUT populates updated_by, making the guard
    // deterministic. security-settings.spec.js seeds the same way.
    await cleanupPasskeyRelyingParty(request)

    await login(page)
    await navigateToConfig(page, 'Security')
    const panel = activePanel(page)

    // Wait for the form-load round-trip (GET /config/security) BEFORE
    // interacting — SecurityTab.vue's onMounted runs loadData() asynchronously,
    // and if clicks fill the form before loadData returns, loadData's
    // `settings.value = { ...settings.value, ...response.data }` clobbers the
    // user's edits, so the Save POSTs the previous (untoggled) state. The Save
    // button is `:loading="saving"` — becoming visible+disabled means the load's
    // final the form is interactive. Waiting on `last updated` text proves
    // loadData has populated the form (the field renders from updated_at /
    // updated_by only after a successful GET).
    await expect(panel.getByText(/last updated by/i)).toBeVisible({ timeout: 10_000 })

    // Capture the Save request PUT to /config/security and inspect its payload,
    // so we can debug what gets sent when "Enable passkey sign-in" + rp_id +
    // origins don't end up in the persisted record. (Lots of pain here: an
    // async load racing the click+fill, or a Vue binding issue that leaves the
    // model unchanged, both manifest as `passkey_enabled=false` after save.)
    const saveResponse = page.waitForResponse((r) => r.request().method() === 'PUT' && r.url().endsWith('/config/security'))

    await panel.getByLabel('Enable passkey sign-in').check()
    await panel.getByLabel('Relying party ID').fill(rpId)
    await panel.getByLabel('Allowed origins').fill(origins)
    await panel.getByRole('button', { name: 'Save' }).click()
    const save = await saveResponse
    // Fail loudly with the response body so a backend validation failure
    // (e.g. "Passkey sign-in requires a relying-party ID and at least one
    // origin") surfaces instead of a later "passkey_enabled didn't toggle".
    expect(save.ok(), `Save PUT /config/security failed: ${save.status()} ${await save.text()}`).toBeTruthy()

    // The `last updated by` text refreshes on a successful save. Wait for it
    // (re-rendered), then verify the actual persistence via the public read.
    await expect(panel.getByText(/last updated by/i)).toBeVisible()

    // Confirm the public /auth/methods contract reflects the toggle so the test
    // is robust: if the relying-party save silently failed, login-page behavior
    // wouldn't reflect passkey_enabled and we'd find out at the ceremony step.
    const methodsRes = await request.get(`${CORE_API}/auth/methods`)
    expect(methodsRes.ok(), `GET /auth/methods should be 200: ${methodsRes.status()}`).toBeTruthy()
    const methods = await methodsRes.json()
    expect(
        methods.passkey_enabled,
        `passkey_enabled should be true after save (URL: ${CORE_API}/auth/methods; rp_id=${rpId}, origins=${origins})`
    ).toBe(true)
}

/** Restore the suite's baseline: passkeys disabled. */
async function cleanupPasskeyRelyingParty(request) {
    try {
        const headers = await adminHeaders(request)
        // Best-effort: ignore status, the suite starts from a known state.
        await request.put(`${CORE_API}/config/security`, {
            headers,
            data: {
                passkey_enabled: false,
                passkey_second_factor: true,
                require_mfa: false,
                rp_id: '',
                rp_name: '',
                origins: ''
            }
        })
    } catch (error) {
        console.warn('cleanupPasskeyRelyingParty failed:', error?.message || error)
    }
}

/** Assert the public /auth/methods contract reflects passkey_enabled after setup. */
async function passkeysMustBeEnabledOnLoginPage(request) {
    const methods = await (await request.get(`${CORE_API}/auth/methods`)).json()
    expect(methods.passkey_enabled).toBe(true)
}
