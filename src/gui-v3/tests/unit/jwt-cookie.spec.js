import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import { createPinia } from 'pinia'
import { consumeJwtCookie } from '@/services/jwt_cookie'
import { useAuthStore } from '@/stores/auth'

const clearJwtCookie = () => {
    document.cookie = 'jwt=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT'
}

describe('consumeJwtCookie', () => {
    let pinia

    beforeEach(() => {
        localStorage.clear()
        clearJwtCookie()
        pinia = createPinia()
    })

    afterEach(clearJwtCookie)

    // A redirect login (OIDC/OAuth2/SAML) comes back as a plain browser redirect with
    // the JWT in a cookie. main.ts calls this before the router resolves its first
    // navigation - otherwise the auth guard sees an anonymous store and bounces the
    // user straight back to the login page they just returned from.
    it('adopts the token a redirect login handed over in the cookie', () => {
        document.cookie = 'jwt=token-from-idp; path=/'

        expect(consumeJwtCookie(pinia)).toBe(true)
        expect(useAuthStore(pinia).jwt).toBe('token-from-idp')
    })

    it('clears the cookie so the token is not replayed on the next page load', () => {
        document.cookie = 'jwt=token-from-idp; path=/'

        consumeJwtCookie(pinia)

        expect(document.cookie).not.toContain('token-from-idp')
    })

    it('leaves an anonymous visitor alone when no cookie was handed over', () => {
        expect(consumeJwtCookie(pinia)).toBe(false)
        expect(useAuthStore(pinia).jwt).toBeFalsy()
    })
})
