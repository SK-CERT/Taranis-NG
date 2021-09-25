import ApiService from "@/services/api_service";

export function getAllProducts(data) {
    return ApiService.post('/publish/products', data)
}

export function createProduct(data) {
    return ApiService.post('/publish/product/new', data)
}

export function deleteProduct(product) {
    return ApiService.delete('/publish/product/' + product.id)
}

export function publishProduct(product_id, publisher_id) {
    return ApiService.post('/publish/product', {product_id: product_id, publisher_id: publisher_id})
}

