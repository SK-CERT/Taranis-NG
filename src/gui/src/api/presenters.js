import ApiService from "@/services/api_service";

export function getAllPresentersNodes(filter) {
    return ApiService.get('/presenters/nodes?search=' + filter.search)
}

export function createNewPresentersNode(node) {
    return ApiService.post('/presenters/nodes/add', node)
}

export function updatePresentersNode(node) {
    return ApiService.put('/presenters/node/' + node.id, node)
}

export function deletePresentersNode(node) {
    return ApiService.delete('/presenters/node/' + node.id)
}
