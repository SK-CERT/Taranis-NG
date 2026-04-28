import ApiService from '@/services/api_service'

export function getAllProducts(filter_data) {
  let filter = '?search=' + encodeURIComponent(filter_data.filter.search)
  if (filter_data.filter.range && filter_data.filter.range !== 'ALL') {
    filter += '&range=' + encodeURIComponent(filter_data.filter.range)
  }

  // Backend uses a single 'published' parameter:
  // published=true -> show only published
  // published=false -> show only unpublished
  // no parameter -> show all
  if (filter_data.filter.published) {
    filter += '&published=true'
  } else if (filter_data.filter.unpublished) {
    filter += '&published=false'
  }

  filter += '&sort=' + encodeURIComponent(filter_data.filter.sort)
  filter += '&offset=' + encodeURIComponent(filter_data.offset)
  filter += '&limit=' + encodeURIComponent(filter_data.limit)

  return ApiService.getWithCancel('screenData', '/publish/products' + filter)
}

export async function getAllProductsUnpaginated(filter_data) {
  // Get all products with pagination for select all functionality
  const PAGE_SIZE = 200
  let allItems = []
  let offset = 0
  let hasMore = true
  let totalCount = 0

  while (hasMore) {
    let filter = '?offset=' + offset
    filter += '&limit=' + PAGE_SIZE
    filter += '&search=' + encodeURIComponent(filter_data.filter.search)
    if (filter_data.filter.range && filter_data.filter.range !== 'ALL') {
      filter += '&range=' + encodeURIComponent(filter_data.filter.range)
    }

    // Backend uses a single 'published' parameter:
    // published=true -> show only published
    // published=false -> show only unpublished
    // no parameter -> show all
    if (filter_data.filter.published) {
      filter += '&published=true'
    } else if (filter_data.filter.unpublished) {
      filter += '&published=false'
    }

    filter += '&sort=' + encodeURIComponent(filter_data.filter.sort)

    const response = await ApiService.get('/publish/products' + filter)

    if (response?.data?.items) {
      allItems = allItems.concat(response.data.items)
      totalCount = response.data.total_count || 0

      // Check if we got fewer items than requested, or if we've reached the total
      if (response.data.items.length < PAGE_SIZE || allItems.length >= totalCount) {
        hasMore = false
      } else {
        offset += PAGE_SIZE
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

export function deleteProduct(product) {
  return ApiService.delete('/publish/products/' + product.id)
}

export function publishProduct(product, publisher_ids) {
  return ApiService.post('/publish/products/publish', {
    product,
    publisher_ids
  })
}

export function previewProduct(data, ctrl_key, jwt) {
  return ApiService.post('/publish/products/preview-ticket', {
    product: data,
    ctrl: ctrl_key,
    jwt
  })
}
