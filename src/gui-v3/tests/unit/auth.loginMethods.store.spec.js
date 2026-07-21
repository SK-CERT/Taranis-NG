import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAuthStore } from '@/stores/auth'
import { useUserStore } from '@/stores/user'

vi.mock('@/api/auth', () => ({
    login: vi.fn(),
    logout: vi.fn(),
    refresh: vi.fn(),
    getLoginMethods: vi.fn()
}))

vi.mock('@/services/api_service', () => ({
    default: {
        setHeader: vi.fn()
    }
}))

function makeJwt(claims = {}, expInSeconds = 3600) {
    const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }))
    const payload = btoa(
        JSON.stringify({
            sub: claims.sub || 'admin',
            exp: Math.floor(Date.now() / 1000) + expInSeconds,
            user_claims: {
                id: claims.id || 1,
                name: claims.name || 'Admin User',
                organization_name: claims.org || 'Test Org',
                permissions: claims.permissions || ['ASSESS_ACCESS']
            }
        })
    )
    return `${header}.${payload}.${btoa('fake-signature')}`
}

const METHODS = [
    { id: 1, name: 'Local accounts', kind: 'local', form: true, login_url: null },
    { id: 2, name: 'Corp SSO', kind: 'oidc', form: false, login_url: '/api/v1/auth/oauth/2/login' },
    { id: 3, name: 'Corp SAML', kind: 'saml', form: false, login_url: '/api/v1/auth/saml/3/login' }
]

describe('Auth store - login methods', () => {
    let authApi

    beforeEach(async () => {
        localStorage.clear()
        setActivePinia(createPinia())
        vi.clearAllMocks()
        authApi = await import('@/api/auth')
    })

    it('starts with no login methods loaded and passkeys off', () => {
        const store = useAuthStore()
        expect(store.loginMethods).toEqual([])
        expect(store.passkeyEnabled).toBe(false)
    })

    it('loads the enabled login methods from the backend', async () => {
        authApi.getLoginMethods.mockResolvedValue({ data: { items: METHODS, passkey_enabled: false } })
        const store = useAuthStore()

        const methods = await store.loadLoginMethods()

        expect(authApi.getLoginMethods).toHaveBeenCalled()
        expect(methods).toHaveLength(3)
        expect(store.loginMethods.map((method) => method.kind)).toEqual(['local', 'oidc', 'saml'])
    })

    it('reads passkey availability from the site-wide flag, not from a provider', async () => {
        authApi.getLoginMethods.mockResolvedValue({ data: { items: METHODS, passkey_enabled: true } })
        const store = useAuthStore()

        await store.loadLoginMethods()

        expect(store.passkeyEnabled).toBe(true)
        // passkeys are never listed as a login method
        expect(store.loginMethods.some((method) => method.kind === 'passkey')).toBe(false)
    })

    it('falls back to an empty list when the endpoint fails (older backend)', async () => {
        authApi.getLoginMethods.mockRejectedValue(new Error('404'))
        const store = useAuthStore()

        const methods = await store.loadLoginMethods()

        expect(methods).toEqual([])
        expect(store.loginMethods).toEqual([])
        expect(store.passkeyEnabled).toBe(false)
    })

    it('login sends the selected provider_id along with the credentials', async () => {
        authApi.login.mockResolvedValue({ data: { access_token: makeJwt() } })
        const store = useAuthStore()

        await store.login({ username: 'admin', password: 'admin', provider_id: 2 })

        expect(authApi.login).toHaveBeenCalledWith({ username: 'admin', password: 'admin', provider_id: 2 }, undefined)
    })

    it('finishLogin stores the token from a multi-step (MFA/passkey) login and hydrates the user', () => {
        const store = useAuthStore()
        const userStore = useUserStore()
        const dispatched = vi.spyOn(window, 'dispatchEvent')

        store.finishLogin(makeJwt({ name: 'Second Factor User', permissions: ['CONFIG_ACCESS'] }))

        expect(store.isAuthenticated).toBe(true)
        expect(localStorage.getItem('ACCESS_TOKEN')).toBeTruthy()
        expect(userStore.permissions).toContain('CONFIG_ACCESS')
        // App.vue listens for this to start SSE / settings after login
        expect(dispatched).toHaveBeenCalledWith(expect.objectContaining({ type: 'logged-in' }))
    })
})
