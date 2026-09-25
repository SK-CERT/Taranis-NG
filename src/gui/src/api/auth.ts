import ApiService from '@/services/api_service'

export function login(userData: Record<string, unknown> = {}) {
    return ApiService.post('/auth/login', userData)
}

export function getLoginMethods() {
    return ApiService.get('/auth/methods')
}

/** Redeem the HttpOnly, one-time handle left by a redirect-based login. */
export function redeemRedirectLogin() {
    return ApiService.post('/auth/redeem', null, { withCredentials: true })
}

export function mfaTotp(mfa_token: string, code: string) {
    return ApiService.post('/auth/mfa/totp', { mfa_token, code })
}

export function mfaTotpEnroll(enroll_token: string, code?: string) {
    return ApiService.post('/auth/mfa/totp/enroll', code ? { enroll_token, code } : { enroll_token })
}

/** Register a passkey as the second factor during a forced enrollment (mid-login, no session yet). */
export function mfaWebauthnEnroll(enroll_token: string, challenge_id?: string, credential?: unknown, name?: string) {
    return ApiService.post('/auth/mfa/webauthn/enroll', credential ? { enroll_token, challenge_id, credential, name } : { enroll_token })
}

export function mfaWebauthnBegin(mfa_token: string) {
    return ApiService.post('/auth/mfa/webauthn/begin', { mfa_token })
}

export function mfaWebauthnFinish(mfa_token: string, challenge_id: string, credential: unknown) {
    return ApiService.post('/auth/mfa/webauthn/finish', { mfa_token, challenge_id, credential })
}

export function passkeyLoginBegin() {
    return ApiService.post('/auth/webauthn/login/begin', {})
}

export function passkeyLoginFinish(challenge_id: string, credential: unknown) {
    return ApiService.post('/auth/webauthn/login/finish', { challenge_id, credential })
}

export function logout() {
    return ApiService.post('/auth/logout', null, { withCredentials: true })
}

export function refresh() {
    return ApiService.get('/auth/refresh')
}

export function initSSE() {
    return ApiService.post('/sse-init', null, { withCredentials: true })
}
