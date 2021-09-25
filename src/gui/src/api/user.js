import ApiService from "@/services/api_service";

export function getProfile() {
    return ApiService.get(`/user/profile`)
}

export function updateProfile(data) {
    return ApiService.put(`/user/profile`, data)
}

export function getAllUserWordLists() {
    return ApiService.get('/user/wordlists')
}

export function getAllUserProductTypes() {
    return ApiService.get('/user/producttypes')
}

export function getAllUserPublishersPresets() {
    return ApiService.get('/user/publishers/presets')
}