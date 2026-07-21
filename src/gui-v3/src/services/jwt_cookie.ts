import type { Pinia } from 'pinia'
import { useAuthStore } from '@/stores/auth'

/**
 * Adopt the JWT the core handed us in a cookie.
 *
 * A redirect login (OIDC / OAuth 2.0 / SAML) cannot return the token in a response
 * body: the browser arrives here through a plain redirect, carrying the JWT in the
 * "jwt" cookie the core set. The same cookie is how the E2E testing token is
 * injected.
 *
 * This has to run *before* the router resolves its first navigation, otherwise the
 * auth guard sees an anonymous store and bounces the user to the login page they
 * have just come back from.
 *
 * @param pinia - the store instance, since this runs before the app is mounted.
 * @returns whether a token was adopted.
 */
export function consumeJwtCookie(pinia: Pinia): boolean {
    const testingToken = import.meta.env.VITE_APP_TARANIS_NG_TESTING_TOKEN
    if (testingToken && typeof testingToken === 'string') {
        document.cookie = `jwt=${testingToken}; path=/`
    }

    const cookies = document.cookie.split(';').reduce<Record<string, string>>((acc, cookie) => {
        const [key, value] = cookie.trim().split('=')
        if (!key) {
            return acc
        }
        acc[key] = value ?? ''
        return acc
    }, {})

    const jwt = cookies['jwt']
    if (!jwt) {
        return false
    }

    useAuthStore(pinia).setToken(jwt)
    document.cookie = 'jwt=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT'
    return true
}
