import ApiService from '@/services/api_service'

export function getHotkeys() {
    return ApiService.get('/users/my-hotkeys')
}

export function updateHotkeys(data) {
    return ApiService.put('/users/my-hotkeys', data)
}

export function getUserWordLists() {
    return ApiService.get('/users/my-word-lists')
}

export function getAvailableWordLists(filter) {
    return ApiService.get('/users/available-word-lists?search=' + filter.search)
}

export function updateUserWordLists(data) {
    return ApiService.put('/users/my-word-lists', data)
}

export function getAllUserProductTypes() {
    return ApiService.get('/users/my-product-types')
}

export function getAllUserPublishersPresets() {
    return ApiService.get('/users/my-publisher-presets')
}

export function getMyTotp() {
    return ApiService.get('/users/my-totp')
}

export function beginMyTotpEnrollment() {
    return ApiService.post('/users/my-totp', {})
}

export function confirmMyTotpEnrollment(code: string) {
    return ApiService.post('/users/my-totp', { code })
}

export function disableMyTotp(code: string) {
    return ApiService.delete('/users/my-totp', { data: { code } })
}

export function getMyPasskeys() {
    return ApiService.get('/users/my-passkeys')
}

export function beginPasskeyRegistration() {
    return ApiService.post('/users/my-passkeys/register-begin', {})
}

export function finishPasskeyRegistration(challenge_id: string, credential: unknown, name: string) {
    return ApiService.post('/users/my-passkeys/register-finish', { challenge_id, credential, name })
}

export function renamePasskey(id: number, name: string) {
    return ApiService.put('/users/my-passkeys/' + id, { name })
}

export function deletePasskey(id: number) {
    return ApiService.delete('/users/my-passkeys/' + id)
}
