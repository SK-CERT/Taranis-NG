import ApiService from "@/services/api_service";

export function getAllProducts(filter_data) {
    let filter = "?search=" + encodeURIComponent(filter_data.filter.search)
    filter += "&range=" + encodeURIComponent(filter_data.filter.range)
    filter += "&published=" + encodeURIComponent(filter_data.filter.published)
    filter += "&unpublished=" + encodeURIComponent(filter_data.filter.unpublished)
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

export function publishProduct(product, publisher_ids) {
    return ApiService.post('/publish/products/publish', {
        product: product,
        publisher_ids: publisher_ids
    })
}

export function previewProduct(data, ctrl_key, jwt) {
    // return a token
    return ApiService.post('/publish/products/preview', {
        product: data,
        ctrl: ctrl_key,
        jwt: jwt
    })
}
