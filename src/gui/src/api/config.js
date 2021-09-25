import ApiService from "@/services/api_service";

export function reloadDictionaries(type) {
    return ApiService.get('/config/attributes/dictionaries/' + type + '/reload')
}

export function getAllAttributes(filter) {
    return ApiService.get('/config/attributes?search=' + filter.search)
}

export function createNewAttribute(attribute) {
    return ApiService.post('/config/attribute/new', attribute)
}

export function updateAttribute(attribute) {
    return ApiService.put('/config/attribute/' + attribute.id, attribute)
}

export function deleteAttribute(attribute) {
    return ApiService.delete('/config/attribute/' + attribute.id)
}

export function getAttributeEnums(filter) {
    return ApiService.get('/config/attribute/enums/' + filter.attribute_id + '?search=' + filter.search + '&offset=' + filter.offset + '&limit=' + filter.limit)
}

export function addAttributeEnum(attribute_id, data) {
    return ApiService.post('/config/attribute/enums/' + attribute_id, data)
}

export function updateAttributeEnum(attribute_id, data) {
    return ApiService.put('/config/attribute/enums/' + attribute_id, data)
}

export function deleteAttributeEnum(attribute_enum_id) {
    return ApiService.delete('/config/attribute/enums/' + attribute_enum_id)
}

export function getAllReportItemTypes(filter) {
    return ApiService.get('/config/reportitemtypes?search=' + filter.search)
}

export function createNewReportItemType(report_item_type) {
    return ApiService.post('/config/reportitemtype/new', report_item_type)
}

export function deleteReportItemType(report_item_type) {
    return ApiService.delete('/config/reportitemtype/' + report_item_type.id)
}

export function updateReportItemType(report_item_type) {
    return ApiService.put('/config/reportitemtype/' + report_item_type.id, report_item_type)
}

export function getAllProductTypes(filter) {
    return ApiService.get('/config/producttypes?search=' + filter.search)
}

export function createNewProductType(product_type) {
    return ApiService.post('/config/producttype/new', product_type)
}

export function deleteProductType(product_type) {
    return ApiService.delete('/config/producttype/' + product_type.id)
}

export function updateProductType(role) {
    return ApiService.put('/config/producttype/' + role.id, role)
}

export function getAllPermissions(filter) {
    return ApiService.get('/config/permissions?search=' + filter.search)
}

export function getAllExternalPermissions(filter) {
    return ApiService.get('/config/external/permissions?search=' + filter.search)
}

export function getAllRoles(filter) {
    return ApiService.get('/config/roles?search=' + filter.search)
}

export function createNewRole(role) {
    return ApiService.post('/config/roles/new', role)
}

export function updateRole(role) {
    return ApiService.put('/config/role/' + role.id, role)
}

export function deleteRole(role) {
    return ApiService.delete('/config/role/' + role.id)
}

export function getAllACLEntries(filter) {
    return ApiService.get('/config/acls?search=' + filter.search)
}

export function createNewACLEntry(acl) {
    return ApiService.post('/config/acls/new', acl)
}

export function updateACLEntry(acl) {
    return ApiService.put('/config/acl/' + acl.id, acl)
}

export function deleteACLEntry(acl) {
    return ApiService.delete('/config/acl/' + acl.id)
}

export function getAllOrganizations(filter) {
    return ApiService.get('/config/organizations?search=' + filter.search)
}

export function createNewOrganization(organization) {
    return ApiService.post('/config/organizations/new', organization)
}

export function updateOrganization(organization) {
    return ApiService.put('/config/organization/' + organization.id, organization)
}

export function deleteOrganization(organization) {
    return ApiService.delete('/config/organization/' + organization.id)
}

export function getAllUsers(filter) {
    return ApiService.get('/config/users?search=' + filter.search)
}

export function createNewUser(user) {
    return ApiService.post('/config/users/new', user)
}

export function updateUser(user) {
    return ApiService.put('/config/user/' + user.id, user)
}

export function deleteUser(user) {
    return ApiService.delete('/config/user/' + user.id)
}

export function getAllExternalUsers(filter) {
    return ApiService.get('/config/external/users?search=' + filter.search)
}

export function createNewExternalUser(user) {
    return ApiService.post('/config/external/users/new', user)
}

export function updateExternalUser(user) {
    return ApiService.put('/config/external/user/' + user.id, user)
}

export function deleteExternalUser(user) {
    return ApiService.delete('/config/external/user/' + user.id)
}

export function getAllWordLists(filter) {
    return ApiService.get('/config/wordlists?search=' + filter.search)
}

export function createNewWordList(word_list) {
    return ApiService.post('/config/wordlist/new', word_list)
}

export function updateWordList(word_list) {
    return ApiService.put('/config/wordlist/' + word_list.id, word_list)
}

export function deleteWordList(word_list) {
    return ApiService.delete('/config/wordlist/' + word_list.id)
}