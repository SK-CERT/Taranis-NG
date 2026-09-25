import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia } from 'pinia'
import { bootstrapTestingToken } from '@/services/testing_auth'
import { useAuthStore } from '@/stores/auth'

describe('testing authentication bootstrap', () => {
    beforeEach(() => {
        localStorage.clear()
        document.cookie = 'jwt=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT'
    })

    afterEach(() => {
        vi.unstubAllEnvs()
    })

    it('installs the explicit E2E token directly without creating a readable cookie', () => {
        vi.stubEnv('VITE_APP_TARANIS_NG_TESTING_TOKEN', 'e2e-token')
        const pinia = createPinia()

        expect(bootstrapTestingToken(pinia)).toBe(true)
        expect(useAuthStore(pinia).jwt).toBe('e2e-token')
        expect(document.cookie).not.toContain('e2e-token')
    })

    it('leaves an anonymous session unchanged when the testing hook is unset', () => {
        vi.stubEnv('VITE_APP_TARANIS_NG_TESTING_TOKEN', '')
        const pinia = createPinia()

        expect(bootstrapTestingToken(pinia)).toBe(false)
        expect(useAuthStore(pinia).jwt).toBe('')
    })
})
