import { describe, expect, it } from 'vitest'
import { getExternalAuthCallbackUrl, getExternalAuthUrl, resolveExternalAuthUrl } from '@/services/auth/runtime_urls'

describe('external authentication runtime URLs', () => {
    it('rejects dangerous schemes and incomplete runtime placeholders', () => {
        expect(getExternalAuthUrl('javascript:alert(1)')).toBeNull()
        expect(getExternalAuthUrl('data:text/html,test')).toBeNull()
        expect(getExternalAuthUrl('$VITE_APP_TARANIS_NG_LOGIN_URL')).toBeNull()
        expect(getExternalAuthUrl('https://id.test/$VITE_APP_TARANIS_NG_LOGIN_URL')).toBeNull()
    })

    it('accepts HTTP(S) absolute and same-origin relative configuration', () => {
        expect(getExternalAuthUrl('https://id.test/login')).toBe('https://id.test/login')
        expect(getExternalAuthUrl('/sso/login')).toBe('/sso/login')
    })

    it('always uses the Vue 3 base for callback and post-logout substitution', () => {
        const callback = getExternalAuthCallbackUrl()
        expect(callback).toBe(`${window.location.origin}/v2/login`)
        expect(resolveExternalAuthUrl('https://id.test/login?redirect_uri=TARANIS_GUI_URI', callback)).toBe(
            `https://id.test/login?redirect_uri=${encodeURIComponent(callback)}`
        )
    })
})
