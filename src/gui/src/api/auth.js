import ApiService from "@/services/api_service";

export function login(userData, method = 'post') {
    if (method === 'post')
        return ApiService.post(`/auth/login`, userData, { withCredentials: true });  // allow save sse_token cookie
    else
        return ApiService.get(`/auth/login`, userData);
}

export function logout() {
    return ApiService.post('/auth/logout', null, { withCredentials: true });
}

export function refresh() {
    return ApiService.get(`/auth/refresh`)
}
