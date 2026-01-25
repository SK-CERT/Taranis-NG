import ApiService from "@/services/api_service";

export function getAllProducts(filter_data) {
    let filter = "?search=" + encodeURIComponent(filter_data.filter.search)
    filter += "&range=" + encodeURIComponent(filter_data.filter.range)
    filter += "&completed=" + encodeURIComponent(filter_data.filter.completed)
    filter += "&incompleted=" + encodeURIComponent(filter_data.filter.incompleted)
    filter += "&sort=" + encodeURIComponent(filter_data.filter.sort)
    filter += "&offset=" + encodeURIComponent(filter_data.offset)
    filter += "&limit=" + encodeURIComponent(filter_data.limit)

    return ApiService.getWithCancel('screenData', '/publish/products' + filter)
}

export function createProduct(data) {
    return ApiService.post('/publish/products', data)
}

export function updateProduct(data) {
    return ApiService.put('/publish/products/' + data.id, data)
}

export function deleteProduct(product) {
    return ApiService.delete('/publish/products/' + product.id)
}

export function publishProduct(product_id, publisher_id) {
    return ApiService.post('/publish/products/' + product_id + '/publishers/' + publisher_id, {})
}
