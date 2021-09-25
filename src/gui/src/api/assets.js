import ApiService from "@/services/api_service";

export function getAllAssetGroups(filter) {
    return ApiService.get('/assets/groups?search=' + filter.search)
}

export function createNewAssetGroup(group) {
    return ApiService.post('/assets/group/add', group)
}

export function updateAssetGroup(group) {
    return ApiService.put('/assets/group/' + group.id, group)
}

export function deleteAssetGroup(group) {
    return ApiService.delete('/assets/group/' + group.id)
}

export function getAllNotificationTemplates(filter) {
    return ApiService.get('/assets/templates?search=' + filter.search)
}

export function createNewNotificationTemplate(template) {
    return ApiService.post('/assets/template/add', template)
}

export function updateNotificationTemplate(template) {
    return ApiService.put('/assets/template/' + template.id, template)
}

export function deleteNotificationTemplate(template) {
    return ApiService.delete('/assets/template/' + template.id)
}

export function getAllAssets(data) {
    return ApiService.get('/assets/' + data.group_id + '?search=' + data.filter.search + "&sort=" + data.filter.sort + "&vulnerable=" + data.filter.vulnerable)
}

export function createNewAsset(asset) {
    return ApiService.post('/asset/add', asset)
}

export function solveVulnerability(data) {
    return ApiService.post('/asset/vulnerability', data)
}

export function updateAsset(asset) {
    return ApiService.put('/asset/' + asset.id, asset)
}

export function deleteAsset(asset) {
    return ApiService.delete('/asset/' + asset.id)
}

export function findAttributeCPE() {
    return ApiService.get('/assets/attribute/cpe')
}

export function getCPEAttributeEnums(filter) {
    return ApiService.get('/assets/attribute/cpe/enums?search=' + filter.search + '&offset=' + filter.offset + '&limit=' + filter.limit)
}