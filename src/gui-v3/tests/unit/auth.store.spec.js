import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAuthStore } from '@/stores/auth'

// Mock dependencies
vi.mock('@/api/auth', () => ({
  authenticate: vi.fn(),
  refresh: vi.fn()
}))

vi.mock('@/services/api_service', () => ({
  default: {
    setHeader: vi.fn()
  }
}))

// Helper: build a minimal JWT with given payload and expiry
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
  const sig = btoa('fake-signature')
  return `${header}.${payload}.${sig}`
}

function makeExpiredJwt(claims = {}) {
  return makeJwt(claims, -3600)
}

describe('Auth Store', () => {
  let authApi

  beforeEach(async () => {
    localStorage.clear()
    setActivePinia(createPinia())
    vi.clearAllMocks()
    authApi = await import('@/api/auth')
  })

  // ── Initial State ─────────────────────────────
  describe('Initial State', () => {
    it('should have empty jwt when localStorage is empty', () => {
      const store = useAuthStore()
      expect(store.jwt).toBe('')
    })

    it('should not be authenticated with empty jwt', () => {
      const store = useAuthStore()
      expect(store.isAuthenticated).toBe(false)
    })

    it('should return null getUserData with empty jwt', () => {
      const store = useAuthStore()
      expect(store.getUserData).toBe(null)
    })

    it('should return empty getSubjectName with empty jwt', () => {
      const store = useAuthStore()
      expect(store.getSubjectName).toBe('')
    })
  })

  // ── JWT Parsing ───────────────────────────────
  describe('JWT Parsing', () => {
    it('should parse user_claims from a valid JWT', () => {
      localStorage.ACCESS_TOKEN = makeJwt({ id: 42, name: 'Test', org: 'Org1' })
      const store = useAuthStore()
      expect(store.getUserData).toMatchObject({
        id: 42,
        name: 'Test',
        organization_name: 'Org1'
      })
    })

    it('should parse sub from JWT as subject name', () => {
      localStorage.ACCESS_TOKEN = makeJwt({ sub: 'testuser' })
      const store = useAuthStore()
      expect(store.getSubjectName).toBe('testuser')
    })

    it('should return null getUserData for malformed JWT', () => {
      localStorage.ACCESS_TOKEN = 'not.a.jwt'
      const store = useAuthStore()
      expect(store.getUserData).toBe(null)
    })

    it('should return empty string getSubjectName for malformed JWT', () => {
      localStorage.ACCESS_TOKEN = 'bad-token'
      const store = useAuthStore()
      expect(store.getSubjectName).toBe('')
    })
  })

  // ── isAuthenticated ───────────────────────────
  describe('isAuthenticated', () => {
    it('should be true for a valid, non-expired JWT', () => {
      localStorage.ACCESS_TOKEN = makeJwt()
      const store = useAuthStore()
      expect(store.isAuthenticated).toBe(true)
    })

    it('should be false for an expired JWT', () => {
      localStorage.ACCESS_TOKEN = makeExpiredJwt()
      const store = useAuthStore()
      expect(store.isAuthenticated).toBe(false)
    })

    it('should be false for a JWT with fewer than 3 parts', () => {
      localStorage.ACCESS_TOKEN = 'only.two'
      const store = useAuthStore()
      expect(store.isAuthenticated).toBe(false)
    })

    it('should be false for empty string', () => {
      const store = useAuthStore()
      expect(store.isAuthenticated).toBe(false)
    })
  })

  // ── Login ─────────────────────────────────────
  describe('login', () => {
    it('should store JWT from successful login response', async () => {
      const token = makeJwt({ sub: 'admin' })
      vi.mocked(authApi.authenticate).mockResolvedValue({
        data: { access_token: token }
      })

      const store = useAuthStore()
      await store.login({ username: 'admin', password: 'pass' })

      expect(store.jwt).toBe(token)
      expect(store.isAuthenticated).toBe(true)
      expect(localStorage.ACCESS_TOKEN).toBe(token)
    })

    it('should set API header after login', async () => {
      const { default: ApiService } = await import('@/services/api_service')
      const token = makeJwt()
      vi.mocked(authApi.authenticate).mockResolvedValue({
        data: { access_token: token }
      })

      const store = useAuthStore()
      await store.login({ username: 'admin', password: 'pass' })

      expect(ApiService.setHeader).toHaveBeenCalled()
    })

    it('should clear JWT on failed login', async () => {
      vi.mocked(authApi.authenticate).mockRejectedValue(new Error('401'))

      const store = useAuthStore()
      await expect(store.login({ username: 'bad', password: 'bad' })).rejects.toThrow('401')

      expect(store.jwt).toBe('')
      expect(store.isAuthenticated).toBe(false)
    })

    it('should dispatch logged-in window event', async () => {
      const token = makeJwt()
      vi.mocked(authApi.authenticate).mockResolvedValue({
        data: { access_token: token }
      })

      const handler = vi.fn()
      window.addEventListener('logged-in', handler)

      const store = useAuthStore()
      await store.login({ username: 'admin', password: 'pass' })

      expect(handler).toHaveBeenCalledTimes(1)
      window.removeEventListener('logged-in', handler)
    })

    it('should call authenticate with correct method', async () => {
      const token = makeJwt()
      vi.mocked(authApi.authenticate).mockResolvedValue({
        data: { access_token: token }
      })

      const store = useAuthStore()
      const userData = { username: 'admin', password: 'pass', method: 'get' }
      await store.login(userData)

      expect(authApi.authenticate).toHaveBeenCalledWith(userData, 'get')
    })
  })

  // ── Logout ────────────────────────────────────
  describe('logout', () => {
    it('should clear JWT and localStorage', () => {
      localStorage.ACCESS_TOKEN = makeJwt()
      const store = useAuthStore()
      expect(store.jwt).not.toBe('')

      store.logout()

      expect(store.jwt).toBe('')
      expect(localStorage.ACCESS_TOKEN).toBe('')
      expect(store.isAuthenticated).toBe(false)
    })

    it('should clear getUserData after logout', () => {
      localStorage.ACCESS_TOKEN = makeJwt({ id: 1, name: 'Admin' })
      const store = useAuthStore()
      expect(store.getUserData).not.toBe(null)

      store.logout()

      expect(store.getUserData).toBe(null)
    })
  })

  // ── Token Refresh ─────────────────────────────
  describe('refreshToken', () => {
    it('should update JWT from refresh response', async () => {
      const oldToken = makeJwt({ sub: 'admin' })
      const newToken = makeJwt({ sub: 'admin', name: 'Refreshed' })
      localStorage.ACCESS_TOKEN = oldToken

      vi.mocked(authApi.refresh).mockResolvedValue({
        data: { access_token: newToken }
      })

      const store = useAuthStore()
      await store.refreshToken()

      expect(store.jwt).toBe(newToken)
      expect(store.isAuthenticated).toBe(true)
    })

    it('should clear JWT on failed refresh', async () => {
      localStorage.ACCESS_TOKEN = makeJwt()
      vi.mocked(authApi.refresh).mockRejectedValue(new Error('Token expired'))

      const store = useAuthStore()
      await expect(store.refreshToken()).rejects.toThrow('Token expired')

      expect(store.jwt).toBe('')
      expect(store.isAuthenticated).toBe(false)
    })
  })

  // ── setToken ──────────────────────────────────
  describe('setToken', () => {
    it('should set JWT directly without dispatching logged-in event', () => {
      const handler = vi.fn()
      window.addEventListener('logged-in', handler)

      const token = makeJwt({ id: 5, name: 'External' })
      const store = useAuthStore()
      store.setToken(token)

      expect(store.jwt).toBe(token)
      expect(store.isAuthenticated).toBe(true)
      expect(handler).not.toHaveBeenCalled()
      window.removeEventListener('logged-in', handler)
    })
  })

  // ── setJwtToken / clearJwtToken ───────────────
  describe('setJwtToken / clearJwtToken', () => {
    it('setJwtToken should persist to localStorage and update ref', () => {
      const store = useAuthStore()
      const token = makeJwt()
      store.setJwtToken(token)

      expect(store.jwt).toBe(token)
      expect(localStorage.ACCESS_TOKEN).toBe(token)
    })

    it('clearJwtToken should empty both ref and localStorage', () => {
      const store = useAuthStore()
      store.setJwtToken(makeJwt())
      store.clearJwtToken()

      expect(store.jwt).toBe('')
      expect(localStorage.ACCESS_TOKEN).toBe('')
    })
  })

  // ── External Login/Logout URLs ────────────────
  describe('External URLs', () => {
    it('hasExternalLoginUrl should be false when env var is not set', () => {
      const store = useAuthStore()
      expect(store.hasExternalLoginUrl).toBe(false)
    })

    it('hasExternalLogoutUrl should be false when env var is not set', () => {
      const store = useAuthStore()
      expect(store.hasExternalLogoutUrl).toBe(false)
    })

    it('getLoginURL should default to /login', () => {
      const store = useAuthStore()
      expect(store.getLoginURL).toBe('/login')
    })

    it('getLogoutURL should default to /logout', () => {
      const store = useAuthStore()
      expect(store.getLogoutURL).toBe('/logout')
    })
  })

  // ── Persistence (localStorage → jwt on init) ─
  describe('Persistence', () => {
    it('should restore JWT from localStorage.ACCESS_TOKEN on store creation', () => {
      const token = makeJwt({ id: 7, name: 'Persisted' })
      localStorage.ACCESS_TOKEN = token

      const store = useAuthStore()
      expect(store.jwt).toBe(token)
      expect(store.getUserData).toMatchObject({ id: 7, name: 'Persisted' })
    })

    it('should default to empty string when ACCESS_TOKEN was never set', () => {
      // localStorage.clear() in beforeEach ensures ACCESS_TOKEN is unset
      const store = useAuthStore()
      expect(store.jwt).toBe('')
      expect(store.isAuthenticated).toBe(false)
    })
  })
})
