import ApiService from "@/services/api_service";

export function getHotkeys() {
    return ApiService.get(`/users/my-hotkeys`)
}

export function updateHotkeys(data) {
    return ApiService.put(`/users/my-hotkeys`, data)
}

export function getUserWordLists() {
    return ApiService.get('/users/my-word-lists')
}

export function updateUserWordLists(data) {
    return ApiService.put(`/users/my-word-lists`, data)
}

export function getAllUserProductTypes() {
    return ApiService.get('/users/my-product-types')
}

export function getAllUserPublishersPresets() {
    return ApiService.get('/users/my-publisher-presets')
}
