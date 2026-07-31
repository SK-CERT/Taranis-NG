import ApiService from '@/services/api_service'

type HttpMethod = 'get' | 'post'

const isRecord = (value: unknown): value is Record<string, unknown> => typeof value === 'object' && value !== null

function normalizeMethod(method: unknown): HttpMethod {
    if (typeof method !== 'string') {
        return 'post'
    }
    return method.toLowerCase() === 'get' ? 'get' : 'post'
}

function callLogin(method: HttpMethod, payload: Record<string, unknown>) {
    const { method: _method, ...body } = payload
    if (method === 'get') {
        const params = isRecord(body['params']) ? body['params'] : body
        return ApiService.get('/auth/login', { params })
    }
    return ApiService.post('/auth/login', body)
}

export function login(userData: Record<string, unknown> = {}, method?: unknown) {
    const preferredMethod = normalizeMethod(method)
    return callLogin(preferredMethod, userData)
}

export function getLoginMethods() {
    return ApiService.get('/auth/methods')
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
