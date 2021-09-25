import ApiService from "@/services/api_service";

export function getAllRemoteAccesses(filter) {
    return ApiService.get('/config/remote/accesses?search=' + filter.search)
}

export function createNewRemoteAccess(remote_access) {
    return ApiService.post('/config/remote/access/new', remote_access)
}

export function updateRemoteAccess(remote_access) {
    return ApiService.put('/config/remote/access/' + remote_access.id, remote_access)
}

export function deleteRemoteAccess(remote_access) {
    return ApiService.delete('/config/remote/access/' + remote_access.id)
}

export function getAllRemoteNodes(filter) {
    return ApiService.get('/config/remote/nodes?search=' + filter.search)
}

export function createNewRemoteNode(remote_node) {
    return ApiService.post('/config/remote/node/new', remote_node)
}

export function updateRemoteNode(remote_node) {
    return ApiService.put('/config/remote/node/' + remote_node.id, remote_node)
}

export function deleteRemoteNode(remote_node) {
    return ApiService.delete('/config/remote/node/' + remote_node.id)
}

export function connectRemoteNode(remote_node) {
    return ApiService.get('/config/remote/node/connect/' + remote_node.id)
}