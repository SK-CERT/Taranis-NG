import { describe, expect, it, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { mountWithPlugins } from '../helpers/mount-helpers'
import Login from '@/views/Login.vue'

const mocks = vi.hoisted(() => ({
    authenticated: false,
    login: vi.fn(async () => {
        mocks.authenticated = true
        return { data: { access_token: 'token' } }
    }),
    push: vi.fn()
}))

vi.mock('vue-router', () => ({
    useRouter: () => ({ push: mocks.push }),
    useRoute: () => ({ query: { code: 'authorization-code', session_state: 'session' } })
}))

vi.mock('@/stores/auth', () => ({
    useAuthStore: () => ({
        hasExternalLoginUrl: true,
        hasExternalLogoutUrl: false,
        getExternalCallbackURL: 'https://taranis.example.test/v2/login',
        getLoginURL: 'https://identity.example.test/login',
        getLogoutURL: '/logout',
        login: mocks.login
    })
}))

vi.mock('@/composables/useAuth', () => ({
    useAuth: () => ({ isAuthenticated: () => mocks.authenticated })
}))

describe('Login external callback', () => {
    it('exchanges the callback without applying local username/password validation', async () => {
        mocks.authenticated = false
        mocks.login.mockClear()
        mocks.push.mockClear()
        mountWithPlugins(Login)
        await flushPromises()

        expect(mocks.login).toHaveBeenCalledWith({
            params: {
                code: 'authorization-code',
                session_state: 'session',
                redirect_uri: 'https://taranis.example.test/v2/login'
            },
            method: 'get'
        })
        expect(mocks.push).toHaveBeenCalledWith('/')
    })
})
