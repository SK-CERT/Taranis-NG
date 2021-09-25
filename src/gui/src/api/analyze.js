import ApiService from "@/services/api_service";

export function getAllReportItemGroups() {
    return ApiService.get('/analyze/reportitems/groups')
}

export function getAllReportItems(data) {
    return ApiService.post('/analyze/reportitems', data)
}

export function getReportItem(report_item_id) {
    return ApiService.get('/analyze/reportitem/' + report_item_id)
}

export function getReportItemData(report_item_id, data) {
    return ApiService.post('/analyze/reportitem/data/' + report_item_id, data)
}

export function createNewReportItem(data) {
    return ApiService.post('/analyze/reportitem/new', data)
}

export function deleteReportItem(report_item) {
    return ApiService.delete('/analyze/reportitem/' + report_item.id)
}

export function updateReportItem(report_item_id, data) {
    return ApiService.put('/analyze/reportitem/' + report_item_id, data)
}

export function getReportItemLocks(report_item_id) {
    return ApiService.get('/analyze/reportitem/locks/' + report_item_id)
}

export function lockReportItem(report_item_id, data) {
    return ApiService.put('/analyze/reportitem/lock/' + report_item_id, data)
}

export function unlockReportItem(report_item_id, data) {
    return ApiService.put('/analyze/reportitem/unlock/' + report_item_id, data)
}

export function holdLockReportItem(report_item_id, data) {
    return ApiService.put('/analyze/reportitem/holdlock/' + report_item_id, data)
}

export function getAllReportItemTypes() {
    return ApiService.get('/analyze/reportitem/types')
}

export function getAttributeEnums(filter) {
    return ApiService.get('/analyze/attribute/enums/' + filter.attribute_id + '?search=' + filter.search + '&offset=' + filter.offset + '&limit=' + filter.limit)
}

export function removeAttachment(data) {
    return ApiService.post(`/analyze/attribute/removeattachment/` + data.report_item_id, data, false)
}