import ApiService from "@/services/api_service";

export function getAllPublishersNodes(filter) {
    return ApiService.get('/publishers/nodes?search=' + filter.search)
}

export function createNewPublishersNode(node) {
    return ApiService.post('/publishers/nodes/add', node)
}

export function updatePublishersNode(node) {
    return ApiService.put('/publishers/node/' + node.id, node)
}

export function deletePublishersNode(node) {
    return ApiService.delete('/publishers/node/' + node.id)
}

export function getAllPublisherPresets(filter) {
    return ApiService.get('/publishers/presets?search=' + filter.search)
}

export function createNewPublisherPreset(preset) {
    return ApiService.post('/publishers/presets/add', preset)
}

export function updatePublisherPreset(node) {
    return ApiService.put('/publishers/preset/' + node.id, node)
}

export function deletePublisherPreset(node) {
    return ApiService.delete('/publishers/preset/' + node.id)
}