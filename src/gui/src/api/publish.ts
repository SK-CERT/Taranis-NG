import ApiService from '@/services/api_service'
import { tagFilterQuery } from '@/api/tags'

export function buildFilterQueryString(filter_data) {
    let filter = '?offset=' + encodeURIComponent(filter_data.offset)
    filter += '&limit=' + encodeURIComponent(filter_data.limit)
    filter += '&sort=' + encodeURIComponent(filter_data.filter.sort)

    if (filter_data.filter.search != '') {
        filter += '&search=' + encodeURIComponent(filter_data.filter.search)
    }
    if (filter_data.filter.published != 'ALL') {
        filter += '&published=' + encodeURIComponent(filter_data.filter.published)
    }
    if (filter_data.filter.range != 'ALL') {
        filter += '&range=' + encodeURIComponent(filter_data.filter.range)
    }
    filter += tagFilterQuery(filter_data.filter)
    return filter
}

export function getAllProducts(filter_data) {
    return ApiService.getWithCancel('screenData', '/publish/products' + buildFilterQueryString(filter_data))
}

export async function getAllProductsUnpaginated(filter_data) {
    // Get all products with pagination for select all functionality
    const PAGE_SIZE = 200
    let allItems = []
    let hasMore = true
    let totalCount = 0

    filter_data.offset = 0
    filter_data.limit = PAGE_SIZE

    while (hasMore) {
        const filter = buildFilterQueryString(filter_data)
        const response = await ApiService.get('/publish/products' + filter)

        if (response?.data?.items) {
            allItems = allItems.concat(response.data.items)
            totalCount = response.data.total_count || 0

            // Check if we got fewer items than requested, or if we've reached the total
            if (response.data.items.length < PAGE_SIZE || allItems.length >= totalCount) {
                hasMore = false
            } else {
                filter_data.offset += PAGE_SIZE
            }
        } else {
            hasMore = false
        }
    }

    return {
        data: {
            items: allItems,
            total_count: totalCount
        }
    }
}

export function createProduct(data) {
    return ApiService.post('/publish/products', data)
}

export function updateProduct(data) {
    return ApiService.put('/publish/products/' + data.id, data)
}

export function getProductById(product_id) {
    return ApiService.get('/publish/products/' + product_id)
}

export function deleteProduct(product) {
    return ApiService.delete('/publish/products/' + product.id)
}

// `language` is the one the product is rendered in (the tab chosen in the publish dialog).
export function publishProduct(product: unknown, publisher_ids: Array<number | string>, language: string | null = null) {
    return ApiService.post('/publish/products/publish', {
        product,
        publisher_ids,
        language
    })
}

// Translates the product's title and description without storing them; they are saved with the product.
export function translateProduct(data: {
    texts: { title?: string; description?: string }
    source_language: string | null
    languages: string[]
    report_item_ids: Array<number | string>
}) {
    return ApiService.post('/publish/products/translate', data)
}

// What rendering in `language` falls back on: reports missing it, outdated translations, templates.
export function checkProductLanguage(product: unknown, language: string | null) {
    return ApiService.post('/publish/products/language-check', { product, language })
}

export function getPublishPublicWebs() {
    return ApiService.get('/publish/public-webs')
}

export function previewProduct(data, ctrl_key, jwt, language: string | null = null) {
    return ApiService.post('/publish/products/preview-ticket', {
        product: data,
        ctrl: ctrl_key,
        jwt,
        language
    })
}
