import ApiService from '@/services/api_service'

type HttpMethod = 'get' | 'post'

type MethodErrorShape = {
    status?: number
    response?: { status?: number }
    request?: { status?: number }
    message?: string
}

const isRecord = (value: unknown): value is Record<string, unknown> => typeof value === 'object' && value !== null

const getMethodErrorStatus = (error: unknown): number | undefined => {
    if (!isRecord(error)) {
        return undefined
    }

    const status = error['status']
    if (typeof status === 'number') {
        return status
    }

    const response = error['response']
    if (isRecord(response) && typeof response['status'] === 'number') {
        return response['status']
    }

    const request = error['request']
    if (isRecord(request) && typeof request['status'] === 'number') {
        return request['status']
    }

    return undefined
}

function normalizeMethod(method: unknown): HttpMethod {
    if (typeof method !== 'string') {
        return 'post'
    }
    return method.toLowerCase() === 'get' ? 'get' : 'post'
}

function getPreferredMethod(envValue: unknown, fallback: HttpMethod): HttpMethod {
    if (typeof envValue !== 'string') {
        return fallback
    }
    return normalizeMethod(envValue)
}

function isMethodNotAllowed(error: unknown): boolean {
    if (typeof error !== 'object' || error === null) {
        return false
    }

    const maybeError = error as MethodErrorShape
    const status = getMethodErrorStatus(error)
    if (status === 405) {
        return true
    }

    return typeof maybeError.message === 'string' && /\b405\b/.test(maybeError.message)
}

async function requestWithMethodFallback<T>(preferredMethod: HttpMethod, request: (method: HttpMethod) => Promise<T>): Promise<T> {
    try {
        return await request(preferredMethod)
    } catch (error) {
        if (!isMethodNotAllowed(error)) {
            throw error
        }

        const fallbackMethod = preferredMethod === 'post' ? 'get' : 'post'
        return request(fallbackMethod)
    }
}

function callLogin(method: 'get' | 'post', payload: Record<string, unknown>) {
    const { method: _method, ...body } = payload
    if (method === 'get') {
        const params = isRecord(body['params']) ? body['params'] : body
        return ApiService.get('/auth/login', { params })
    }
    return ApiService.post('/auth/login', body)
}

export async function login(userData: Record<string, unknown> = {}, method?: unknown) {
    const defaultMethod = getPreferredMethod(import.meta.env.VITE_APP_TARANIS_NG_LOGIN_METHOD, 'post')
    const preferredMethod = typeof method === 'string' ? normalizeMethod(method) : defaultMethod
    return requestWithMethodFallback(preferredMethod, (httpMethod) => callLogin(httpMethod, userData))
}

function callLogout(method: 'get' | 'post') {
    if (method === 'get') {
        return ApiService.get('/auth/logout', { withCredentials: true })
    }
    return ApiService.post('/auth/logout', null, { withCredentials: true })
}

export async function logout() {
    const preferredMethod = getPreferredMethod(import.meta.env.VITE_APP_TARANIS_NG_LOGOUT_METHOD, 'post')
    return requestWithMethodFallback(preferredMethod, callLogout)
}

export function refresh() {
    return ApiService.get('/auth/refresh')
}

function callSseInit(method: 'get' | 'post') {
    if (method === 'get') {
        return ApiService.get('/sse-init', { withCredentials: true })
    }
    return ApiService.post('/sse-init', null, { withCredentials: true })
}

export async function initSSE() {
    // Some deployments expose SSE init as GET while others use POST.
    const preferredMethod = getPreferredMethod(import.meta.env.VITE_APP_TARANIS_NG_SSE_INIT_METHOD, 'post')
    return requestWithMethodFallback(preferredMethod, callSseInit)
}
