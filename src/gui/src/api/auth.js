import ApiService from "@/services/api_service";

export function login(userData) {
    return ApiService.post(`/auth/login`, userData);
}

export function logout() {
    return ApiService.post('/auth/logout', null, { withCredentials: true });  // allow delete jwt_id cookie
}

export function refresh() {
    return ApiService.get(`/auth/refresh`)
}

export function initSSE() {
    return ApiService.post('/sse-init', null, { withCredentials: true });  // allow save jwt_id cookie
}
