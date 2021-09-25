import ApiService from "@/services/api_service";

export function getAllBotsNodes(filter) {
    return ApiService.get('/bots/nodes?search=' + filter.search)
}

export function createNewBotsNode(node) {
    return ApiService.post('/bots/nodes/add', node)
}

export function updateBotsNode(node) {
    return ApiService.put('/bots/node/' + node.id, node)
}

export function deleteBotsNode(node) {
    return ApiService.delete('/bots/node/' + node.id)
}

export function getAllBotPresets(filter) {
    return ApiService.get('/bots/presets?search=' + filter.search)
}

export function createNewBotPreset(preset) {
    return ApiService.post('/bots/presets/add', preset)
}

export function updateBotPreset(node) {
    return ApiService.put('/bots/preset/' + node.id, node)
}

export function deleteBotPreset(node) {
    return ApiService.delete('/bots/preset/' + node.id)
}