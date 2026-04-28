import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAuthStore } from '@/stores/auth'
import { useUserStore } from '@/stores/user'
import { useAuth } from '@/composables/useAuth'

// Mock AuthService (used internally by useAuth for permission/token checks)
vi.mock('@/services/auth_service', () => ({
  default: {
    isAuthenticated: vi.fn(() => false),
    needTokenRefresh: vi.fn(() => false),
    hasPermission: vi.fn(() => false),
    hasAnyPermission: vi.fn(() => false),
    hasAllPermissions: vi.fn(() => false)
  }
}))

// Helper: build a JWT with given expiry
function makeJwt(expInSeconds = 3600) {
  const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }))
  const payload = btoa(
    JSON.stringify({
      sub: 'admin',
      exp: Math.floor(Date.now() / 1000) + expInSeconds,
      user_claims: { id: 1, name: 'Admin', permissions: ['ASSESS_ACCESS'] }
    })
  )
  return `${header}.${payload}.${btoa('sig')}`
}

describe('useAuth composable', () => {
  let AuthService

  beforeEach(async () => {
    localStorage.clear()
    setActivePinia(createPinia())
    vi.clearAllMocks()
    const mod = await import('@/services/auth_service')
    AuthService = mod.default
  })

  // ── Returned Shape ────────────────────────────
  describe('return shape', () => {
    it('should expose permissions constants', () => {
      const auth = useAuth()
      expect(auth.permissions).toBeDefined()
      expect(auth.permissions.ASSESS_ACCESS).toBe('ASSESS_ACCESS')
      expect(auth.permissions.ANALYZE_UPDATE).toBe('ANALYZE_UPDATE')
    })

    it('should expose computed user from userStore', () => {
      const userStore = useUserStore()
      userStore.setUser({ id: 5, name: 'Test', permissions: [] })

      const auth = useAuth()
      expect(auth.user.value).toMatchObject({ id: 5, name: 'Test' })
    })

    it('should expose isAuth computed from authStore', () => {
      const auth = useAuth()
      expect(auth.isAuth.value).toBe(false)

      // Set a valid JWT
      const authStore = useAuthStore()
      authStore.setJwtToken(makeJwt())
      expect(auth.isAuth.value).toBe(true)
    })

    it('should expose hasExternalLogin/hasExternalLogout', () => {
      const auth = useAuth()
      expect(auth.hasExternalLogin.value).toBe(false)
      expect(auth.hasExternalLogout.value).toBe(false)
    })
  })

  // ── Permission Methods ────────────────────────
  describe('permission checks', () => {
    it('checkPermission should delegate to AuthService.hasPermission', () => {
      AuthService.hasPermission.mockReturnValue(true)

      const auth = useAuth()
      const result = auth.checkPermission('ASSESS_ACCESS')

      expect(AuthService.hasPermission).toHaveBeenCalledWith('ASSESS_ACCESS')
      expect(result).toBe(true)
    })

    it('checkAnyPermission should delegate to AuthService.hasAnyPermission', () => {
      AuthService.hasAnyPermission.mockReturnValue(true)

      const auth = useAuth()
      const result = auth.checkAnyPermission(['ASSESS_ACCESS', 'ANALYZE_ACCESS'])

      expect(AuthService.hasAnyPermission).toHaveBeenCalledWith(['ASSESS_ACCESS', 'ANALYZE_ACCESS'])
      expect(result).toBe(true)
    })

    it('checkAllPermissions should delegate to AuthService.hasAllPermissions', () => {
      AuthService.hasAllPermissions.mockReturnValue(false)

      const auth = useAuth()
      const result = auth.checkAllPermissions(['ASSESS_ACCESS', 'PUBLISH_CREATE'])

      expect(AuthService.hasAllPermissions).toHaveBeenCalledWith(['ASSESS_ACCESS', 'PUBLISH_CREATE'])
      expect(result).toBe(false)
    })
  })

  // ── Token / Auth Methods ──────────────────────
  describe('token methods', () => {
    it('isAuthenticated should delegate to AuthService', () => {
      AuthService.isAuthenticated.mockReturnValue(true)

      const auth = useAuth()
      expect(auth.isAuthenticated()).toBe(true)
      expect(AuthService.isAuthenticated).toHaveBeenCalled()
    })

    it('needTokenRefresh should delegate to AuthService', () => {
      AuthService.needTokenRefresh.mockReturnValue(true)

      const auth = useAuth()
      expect(auth.needTokenRefresh()).toBe(true)
      expect(AuthService.needTokenRefresh).toHaveBeenCalled()
    })
  })

  // ── Logout ────────────────────────────────────
  describe('logout', () => {
    it('should call authStore.logout and reload when no external URL', async () => {
      // authStore.logout is synchronous (returns void, not a promise)
      // The composable calls authStore.logout().then(...)
      // So we need logout to be promisified - but the actual store's logout is sync.
      // We'll mock it to return a resolved promise.
      const authStore = useAuthStore()
      const originalLogout = authStore.logout.bind(authStore)
      authStore.logout = vi.fn(() => {
        originalLogout()
        return Promise.resolve()
      })

      // Mock window.location.reload
      const reloadSpy = vi.fn()
      Object.defineProperty(window, 'location', {
        value: { reload: reloadSpy, href: '' },
        writable: true,
        configurable: true
      })

      const auth = useAuth()
      await auth.logout()

      expect(authStore.logout).toHaveBeenCalled()
      expect(reloadSpy).toHaveBeenCalled()
    })
  })
})
