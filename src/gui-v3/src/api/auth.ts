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

export function logout() {
    return ApiService.post('/auth/logout', null, { withCredentials: true })
}

export function refresh() {
    return ApiService.get('/auth/refresh')
}

export function initSSE() {
    return ApiService.post('/sse-init', null, { withCredentials: true })
}
