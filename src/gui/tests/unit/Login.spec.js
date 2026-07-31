import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mountWithPlugins } from '../helpers/mount-helpers'
import Login from '@/views/Login.vue'
import { useAuthStore } from '@/stores/auth'
import { getLoginMethods, mfaTotp, mfaTotpEnroll, mfaWebauthnEnroll, passkeyLoginBegin, passkeyLoginFinish } from '@/api/auth'

const push = vi.fn()
let routeQuery = {}

vi.mock('vue-router', () => ({
    useRouter: () => ({ push }),
    useRoute: () => ({ query: routeQuery })
}))

vi.mock('@/api/auth', () => ({
    login: vi.fn(),
    logout: vi.fn(),
    refresh: vi.fn(),
    getLoginMethods: vi.fn().mockResolvedValue({ data: { items: [] } }),
    mfaTotp: vi.fn(),
    mfaTotpEnroll: vi.fn(),
    mfaWebauthnEnroll: vi.fn(),
    mfaWebauthnBegin: vi.fn(),
    mfaWebauthnFinish: vi.fn(),
    passkeyLoginBegin: vi.fn(),
    passkeyLoginFinish: vi.fn()
}))

vi.mock('qrcode', () => ({
    default: { toDataURL: vi.fn().mockResolvedValue('data:image/png;base64,QR') }
}))

vi.mock('@simplewebauthn/browser', () => ({
    startAuthentication: vi.fn().mockResolvedValue({ id: 'credential-1' }),
    startRegistration: vi.fn().mockResolvedValue({ id: 'new-passkey-1' })
}))

const METHODS = [
    { id: 1, name: 'Local accounts', kind: 'local', form: true, login_url: null },
    { id: 2, name: 'Corp SSO', kind: 'oidc', form: false, login_url: '/api/v1/auth/oauth/2/login' },
    { id: 3, name: 'Corp SAML', kind: 'saml', form: false, login_url: '/api/v1/auth/saml/3/login' }
]

/**
 * Mount the login page; the backend reports `methods` as the enabled providers and
 * `passkeyEnabled` as the site-wide passkey capability (a security setting, not a provider).
 */
async function mountLogin(methods = METHODS, passkeyEnabled = true) {
    getLoginMethods.mockResolvedValue({ data: { items: methods, passkey_enabled: passkeyEnabled } })
    const wrapper = mountWithPlugins(Login)
    const authStore = useAuthStore()
    // let onMounted's loadLoginMethods() resolve so the page renders the methods
    await new Promise((resolve) => setTimeout(resolve, 0))
    await wrapper.vm.$nextTick()
    return { wrapper, authStore }
}

/** Build a rejected login promise carrying a backend error payload. */
function loginRejection(data) {
    const error = new Error('request failed')
    error.response = { status: 403, data }
    return Promise.reject(error)
}

describe('Login page', () => {
    beforeEach(() => {
        localStorage.clear()
        routeQuery = {}
        for (const name of ['mfa_token', 'mfa_methods', 'mfa_enroll']) {
            document.cookie = `${name}=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT`
        }
        vi.clearAllMocks()
    })

    // ── Method rendering ──────────────────────────
    it('renders the credentials form when a form-based provider is enabled', async () => {
        const { wrapper } = await mountLogin()
        expect(wrapper.find('[data-test="login-username"]').exists()).toBe(true)
        expect(wrapper.find('[data-test="login-password"]').exists()).toBe(true)
        expect(wrapper.find('[data-test="login-submit"]').exists()).toBe(true)
    })

    it('renders one SSO button per redirect provider, including SAML', async () => {
        const { wrapper } = await mountLogin()
        expect(wrapper.find('[data-test="login-sso-2"]').exists()).toBe(true)
        expect(wrapper.find('[data-test="login-sso-3"]').exists()).toBe(true)
        expect(wrapper.text()).toContain('Sign in with Corp SSO')
        expect(wrapper.text()).toContain('Sign in with Corp SAML')
    })

    it('shows the passkey button only when passkey sign-in is enabled site-wide', async () => {
        const { wrapper } = await mountLogin(METHODS, true)
        expect(wrapper.find('[data-test="login-passkey"]').exists()).toBe(true)

        const { wrapper: noPasskey } = await mountLogin(METHODS, false)
        expect(noPasskey.find('[data-test="login-passkey"]').exists()).toBe(false)
    })

    it('hides the provider select when only one form-based provider exists', async () => {
        const { wrapper } = await mountLogin()
        expect(wrapper.find('[data-test="login-provider"]').exists()).toBe(false)
    })

    it('shows the provider select when several form-based providers exist', async () => {
        const { wrapper } = await mountLogin([...METHODS, { id: 4, name: 'Corp LDAP', kind: 'ldap', form: true, login_url: null }])
        expect(wrapper.find('[data-test="login-provider"]').exists()).toBe(true)
        expect(wrapper.vm.selectedProviderId).toBe(1)
    })

    it('still renders the password form when the methods endpoint returns nothing (older backend)', async () => {
        const { wrapper } = await mountLogin([], false)
        expect(wrapper.vm.hasFormMethods).toBe(true)
        expect(wrapper.find('[data-test="login-username"]').exists()).toBe(true)
    })

    // ── Credentials login ─────────────────────────
    it('submits the selected provider with the credentials', async () => {
        const { wrapper, authStore } = await mountLogin()
        authStore.login = vi.fn().mockResolvedValue({})
        Object.defineProperty(authStore, 'isAuthenticated', { get: () => true, configurable: true })

        wrapper.vm.username = 'admin'
        wrapper.vm.password = 'admin'
        await wrapper.vm.handleFormSubmit()

        expect(authStore.login).toHaveBeenCalledWith({ username: 'admin', password: 'admin', provider_id: 1 })
    })

    // ── Backend error codes ───────────────────────
    it.each([
        ['PENDING_APPROVAL', 'awaiting administrator approval'],
        ['ACCOUNT_DISABLED', 'account is disabled'],
        ['USERNAME_COLLISION', 'already exists'],
        ['ACCOUNT_NOT_LINKED', 'not linked to any account'],
        ['DOMAIN_NOT_ALLOWED', 'domain is not allowed']
    ])('surfaces the %s login rejection', async (code, expectedText) => {
        const { wrapper, authStore } = await mountLogin()
        authStore.login = vi.fn().mockImplementation(() => loginRejection({ code }))

        wrapper.vm.username = 'someone'
        wrapper.vm.password = 'secret'
        await wrapper.vm.handleFormSubmit()
        await wrapper.vm.$nextTick()

        expect(wrapper.vm.showLoginError).toBe(true)
        expect(wrapper.find('[data-test="login-error"]').text().toLowerCase()).toContain(expectedText.toLowerCase())
    })

    it('shows the error passed back from an OAuth/SAML redirect flow', async () => {
        routeQuery = { login_error: 'pending_approval' }
        const { wrapper } = await mountLogin()

        expect(wrapper.vm.showLoginError).toBe(true)
        expect(wrapper.find('[data-test="login-error"]').text()).toContain('awaiting administrator approval')
    })

    // ── MFA step ──────────────────────────────────
    it('switches to the MFA step when the backend demands a second factor', async () => {
        const { wrapper, authStore } = await mountLogin()
        authStore.login = vi
            .fn()
            .mockImplementation(() => loginRejection({ code: 'MFA_REQUIRED', methods: ['totp', 'passkey'], mfa_token: 'mfa-token-1' }))

        wrapper.vm.username = 'admin'
        wrapper.vm.password = 'admin'
        await wrapper.vm.handleFormSubmit()
        await wrapper.vm.$nextTick()

        expect(wrapper.vm.step).toBe('mfa')
        expect(wrapper.vm.mfaToken).toBe('mfa-token-1')
        expect(wrapper.find('[data-test="login-totp"]').exists()).toBe(true)
        // the password form is replaced by the MFA panel
        expect(wrapper.find('[data-test="login-password"]').exists()).toBe(false)
    })

    it('completes the login with a valid TOTP code', async () => {
        const { wrapper, authStore } = await mountLogin()
        authStore.finishLogin = vi.fn()
        mfaTotp.mockResolvedValue({ data: { access_token: 'jwt-token' } })

        wrapper.vm.step = 'mfa'
        wrapper.vm.mfaToken = 'mfa-token-1'
        wrapper.vm.totpCode = '123456'
        await wrapper.vm.handleTotpSubmit()

        expect(mfaTotp).toHaveBeenCalledWith('mfa-token-1', '123456')
        expect(authStore.finishLogin).toHaveBeenCalledWith('jwt-token')
        expect(push).toHaveBeenCalled()
    })

    it('reports an invalid TOTP code and clears the field', async () => {
        const { wrapper } = await mountLogin()
        mfaTotp.mockImplementation(() => loginRejection({ code: 'TOTP_INVALID' }))

        wrapper.vm.step = 'mfa'
        wrapper.vm.mfaToken = 'mfa-token-1'
        wrapper.vm.totpCode = '000000'
        await wrapper.vm.handleTotpSubmit()
        await wrapper.vm.$nextTick()

        expect(wrapper.vm.showLoginError).toBe(true)
        expect(wrapper.vm.totpCode).toBe('')
    })

    // ── Forced TOTP enrollment ────────────────────
    it('walks the user through enrollment when the provider requires MFA', async () => {
        const { wrapper, authStore } = await mountLogin()
        authStore.login = vi.fn().mockImplementation(() => loginRejection({ code: 'MFA_ENROLLMENT_REQUIRED', enroll_token: 'enroll-1' }))
        mfaTotpEnroll.mockResolvedValue({ data: { otpauth_uri: 'otpauth://totp/Taranis:admin?secret=ABC' } })

        wrapper.vm.username = 'admin'
        wrapper.vm.password = 'admin'
        await wrapper.vm.handleFormSubmit()
        await wrapper.vm.$nextTick()

        expect(wrapper.vm.step).toBe('enroll')
        expect(mfaTotpEnroll).toHaveBeenCalledWith('enroll-1')
        expect(wrapper.vm.qrDataUrl).toBe('data:image/png;base64,QR')
        expect(wrapper.find('[data-test="login-enroll-code"]').exists()).toBe(true)
    })

    // A user forced to set up a second factor should not be pushed into an authenticator
    // app when the site accepts passkeys - registering one *is* the factor.
    it('offers a passkey on the enrollment step when the site accepts passkeys as a second factor', async () => {
        const { wrapper, authStore } = await mountLogin()
        authStore.login = vi
            .fn()
            .mockImplementation(() =>
                loginRejection({ code: 'MFA_ENROLLMENT_REQUIRED', enroll_token: 'enroll-1', methods: ['totp', 'passkey'] })
            )
        mfaTotpEnroll.mockResolvedValue({ data: { otpauth_uri: 'otpauth://totp/Taranis:admin?secret=ABC' } })

        wrapper.vm.username = 'admin'
        wrapper.vm.password = 'admin'
        await wrapper.vm.handleFormSubmit()
        await wrapper.vm.$nextTick()

        expect(wrapper.vm.step).toBe('enroll')
        expect(wrapper.find('[data-test="login-enroll-passkey"]').exists()).toBe(true)
    })

    it('hides the passkey option when TOTP is the only accepted second factor', async () => {
        const { wrapper, authStore } = await mountLogin()
        authStore.login = vi
            .fn()
            .mockImplementation(() => loginRejection({ code: 'MFA_ENROLLMENT_REQUIRED', enroll_token: 'enroll-1', methods: ['totp'] }))
        mfaTotpEnroll.mockResolvedValue({ data: { otpauth_uri: 'otpauth://totp/Taranis:admin?secret=ABC' } })

        wrapper.vm.username = 'admin'
        wrapper.vm.password = 'admin'
        await wrapper.vm.handleFormSubmit()
        await wrapper.vm.$nextTick()

        expect(wrapper.find('[data-test="login-enroll-passkey"]').exists()).toBe(false)
    })

    it('registers a passkey as the second factor and completes the login', async () => {
        const { wrapper, authStore } = await mountLogin()
        authStore.finishLogin = vi.fn()
        mfaWebauthnEnroll
            .mockResolvedValueOnce({ data: { options: { challenge: 'abc' }, challenge_id: 'chal-1' } })
            .mockResolvedValueOnce({ data: { access_token: 'jwt-after-passkey-enroll' } })

        wrapper.vm.step = 'enroll'
        wrapper.vm.enrollToken = 'enroll-1'
        await wrapper.vm.handleEnrollPasskey()

        expect(mfaWebauthnEnroll).toHaveBeenNthCalledWith(1, 'enroll-1')
        expect(mfaWebauthnEnroll).toHaveBeenNthCalledWith(2, 'enroll-1', 'chal-1', { id: 'new-passkey-1' }, 'Passkey')
        // no TOTP code is asked for: the authenticator has just verified the user
        expect(authStore.finishLogin).toHaveBeenCalledWith('jwt-after-passkey-enroll')
    })

    it('activates the enrollment with a confirmation code and logs in', async () => {
        const { wrapper, authStore } = await mountLogin()
        authStore.finishLogin = vi.fn()
        mfaTotpEnroll.mockResolvedValue({ data: { access_token: 'jwt-after-enroll' } })

        wrapper.vm.step = 'enroll'
        wrapper.vm.enrollToken = 'enroll-1'
        wrapper.vm.totpCode = '123456'
        await wrapper.vm.handleEnrollSubmit()

        expect(mfaTotpEnroll).toHaveBeenCalledWith('enroll-1', '123456')
        expect(authStore.finishLogin).toHaveBeenCalledWith('jwt-after-enroll')
    })

    // ── MFA after a redirect login (OIDC/OAuth2/SAML) ──
    // The core is mid-redirect and cannot answer with a JSON challenge, so it hands the
    // scoped token over in a cookie; this page runs the same step a form login would.
    it('challenges for TOTP when a redirect login left a second factor owed', async () => {
        document.cookie = 'mfa_token=mfa-from-idp; path=/'
        document.cookie = 'mfa_methods=totp,passkey; path=/'

        const { wrapper } = await mountLogin()
        await wrapper.vm.$nextTick()

        expect(wrapper.vm.step).toBe('mfa')
        expect(wrapper.vm.mfaToken).toBe('mfa-from-idp')
        expect(wrapper.vm.mfaMethods).toEqual(['totp', 'passkey'])
        // the token is single-use: leaving it in the jar would replay it on the next visit
        expect(document.cookie).not.toContain('mfa-from-idp')
    })

    it('starts TOTP enrollment when a redirect provider requires MFA and the user has none', async () => {
        document.cookie = 'mfa_enroll=enroll-from-idp; path=/'
        mfaTotpEnroll.mockResolvedValue({ data: { otpauth_uri: 'otpauth://totp/Taranis:jsmith?secret=ABC' } })

        const { wrapper } = await mountLogin()
        await wrapper.vm.$nextTick()

        expect(wrapper.vm.step).toBe('enroll')
        expect(mfaTotpEnroll).toHaveBeenCalledWith('enroll-from-idp')
        expect(document.cookie).not.toContain('enroll-from-idp')
    })

    it('shows the plain credentials form when no challenge cookie came back', async () => {
        const { wrapper } = await mountLogin()

        expect(wrapper.vm.step).toBe('credentials')
    })

    // ── Passkeys ──────────────────────────────────
    it('logs in passwordless with a passkey', async () => {
        const { wrapper, authStore } = await mountLogin()
        authStore.finishLogin = vi.fn()
        passkeyLoginBegin.mockResolvedValue({ data: { options: { challenge: 'abc' }, challenge_id: 'chal-1' } })
        passkeyLoginFinish.mockResolvedValue({ data: { access_token: 'jwt-passkey' } })

        await wrapper.vm.handlePasskeyLogin()

        expect(passkeyLoginBegin).toHaveBeenCalled()
        expect(passkeyLoginFinish).toHaveBeenCalledWith('chal-1', { id: 'credential-1' })
        expect(authStore.finishLogin).toHaveBeenCalledWith('jwt-passkey')
    })

    it('reports a rejected passkey login (e.g. disabled account)', async () => {
        const { wrapper } = await mountLogin()
        passkeyLoginBegin.mockResolvedValue({ data: { options: {}, challenge_id: 'chal-1' } })
        passkeyLoginFinish.mockImplementation(() => loginRejection({ code: 'ACCOUNT_DISABLED' }))

        await wrapper.vm.handlePasskeyLogin()
        await wrapper.vm.$nextTick()

        expect(wrapper.vm.showLoginError).toBe(true)
        expect(wrapper.find('[data-test="login-error"]').text()).toContain('account is disabled')
    })

    // ── Redirect providers ────────────────────────

    /** jsdom/happy-dom forbid assigning window.location.href directly. */
    function captureNavigation() {
        const assign = vi.fn()
        Object.defineProperty(window, 'location', {
            value: {
                origin: 'https://taranis.example.org',
                set href(value) {
                    assign(value)
                }
            },
            writable: true,
            configurable: true
        })
        return assign
    }

    /** The gotoUrl the core will redirect the browser back to once the IdP is done. */
    const gotoUrlOf = (assign) => decodeURIComponent(assign.mock.calls[0][0].split('gotoUrl=')[1])

    it('sends the browser to the provider login endpoint with a gotoUrl', async () => {
        const { wrapper } = await mountLogin()
        const assign = captureNavigation()

        wrapper.vm.handleRedirectLogin(METHODS[2]) // SAML

        expect(assign).toHaveBeenCalledWith(expect.stringContaining('/api/v1/auth/saml/3/login?gotoUrl='))
        expect(assign).toHaveBeenCalledWith(expect.stringContaining(encodeURIComponent('https://taranis.example.org')))
    })

    it('returns from the IdP into the app rather than back to this page', async () => {
        const { wrapper } = await mountLogin()
        const assign = captureNavigation()

        wrapper.vm.handleRedirectLogin(METHODS[1]) // OIDC

        // landing on /login again would flash the login screen at an authenticated user
        expect(gotoUrlOf(assign)).toBe('https://taranis.example.org/dashboard')
    })

    it('returns to the deep link the auth guard sent the user away from', async () => {
        routeQuery = { redirect: '/assess' }
        const { wrapper } = await mountLogin()
        const assign = captureNavigation()

        wrapper.vm.handleRedirectLogin(METHODS[1]) // OIDC

        expect(gotoUrlOf(assign)).toBe('https://taranis.example.org/assess')
    })

    // ── Step navigation ───────────────────────────
    it('returns to the credentials step and drops the MFA tokens', async () => {
        const { wrapper } = await mountLogin()
        wrapper.vm.step = 'mfa'
        wrapper.vm.mfaToken = 'mfa-token-1'
        wrapper.vm.totpCode = '123456'

        wrapper.vm.backToCredentials()
        await wrapper.vm.$nextTick()

        expect(wrapper.vm.step).toBe('credentials')
        expect(wrapper.vm.mfaToken).toBe('')
        expect(wrapper.vm.totpCode).toBe('')
    })
})
