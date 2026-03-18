import ApiService from "@/services/api_service";

export function login(userData, method = 'post') {
    if (method === 'post')
        return ApiService.post(`/auth/login`, userData);
    else
        return ApiService.get(`/auth/login`, userData);
}

export function logout() {
    return ApiService.post('/auth/logout', null, { withCredentials: true });  // allow delete sse_token cookie
}

export function refresh() {
    return ApiService.get(`/auth/refresh`)
}

export function initSSE() {
    return ApiService.post('/sse-init', null, { withCredentials: true });  // allow save sse_token cookie
}
