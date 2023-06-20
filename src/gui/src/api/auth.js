import ApiService from "@/services/api_service";

export function authenticate(userData, method = 'post') {
    if (method === 'post')
        return ApiService.post(`/auth/login`, userData);
    else
        return ApiService.get(`/auth/login`, userData);
}

export function refresh() {
    return ApiService.get(`/auth/refresh`)
}