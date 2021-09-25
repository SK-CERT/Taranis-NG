import ApiService from "@/services/api_service";

export function getAllCollectorsNodes(filter) {
    return ApiService.get('/collectors/nodes?search=' + filter.search)
}

export function createNewCollectorsNode(node) {
    return ApiService.post('/collectors/nodes/add', node)
}

export function updateCollectorsNode(node) {
    return ApiService.put('/collectors/node/' + node.id, node)
}

export function deleteCollectorsNode(node) {
    return ApiService.delete('/collectors/node/' + node.id)
}

export function getAllOSINTSources(filter) {
    return ApiService.get('/collectors/sources?search=' + filter.search)
}

export function getManualOSINTSources() {
    return ApiService.get('/collectors/sources/manual')
}

export function createNewOSINTSource(source) {
    return ApiService.post('/collectors/sources/add', source)
}

export function updateOSINTSource(source) {
    return ApiService.put('/collectors/source/' + source.id, source)
}

export function deleteOSINTSource(source) {
    return ApiService.delete('/collectors/source/' + source.id)
}

export function getAllOSINTSourceGroups(filter) {
    return ApiService.get('/collectors/sources/groups?search=' + filter.search)
}

export function createNewOSINTSourceGroup(group) {
    return ApiService.post('/collectors/sources/groups/add', group)
}

export function updateOSINTSourceGroup(group) {
    return ApiService.put('/collectors/sources/group/' + group.id, group)
}

export function deleteOSINTSourceGroup(group) {
    return ApiService.delete('/collectors/sources/group/' + group.id)
}