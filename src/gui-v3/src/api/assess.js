import ApiService from '@/services/api_service'

export function getAllOSINTSourceGroupsAssess() {
  return ApiService.get('/assess/osint-source-groups')
}

export function getManualOSINTSources() {
  return ApiService.get('/assess/manual-osint-sources')
}

export function getNewsItemsByGroup(group_id, filter_data) {
  let filter = '?offset=' + encodeURIComponent(filter_data.offset || 0)
  filter += '&limit=' + encodeURIComponent(filter_data.limit || 20)
  filter += '&sort=' + encodeURIComponent(filter_data.filter.sort)

  if (filter_data.filter.search && filter_data.filter.search !== '') {
    filter += '&search=' + encodeURIComponent(filter_data.filter.search)
  }
  if (filter_data.filter.read !== 'ALL') {
    filter += '&read=' + encodeURIComponent(filter_data.filter.read === true)
  }
  if (filter_data.filter.important !== 'ALL') {
    filter += '&important=' + encodeURIComponent(filter_data.filter.important === true)
  }
  if (filter_data.filter.relevant !== 'ALL') {
    filter += '&relevant=' + encodeURIComponent(filter_data.filter.relevant === true)
  }
  if (filter_data.filter.range && filter_data.filter.range !== 'ALL') {
    filter += '&range=' + encodeURIComponent(filter_data.filter.range)
  }

  return ApiService.getWithCancel(
    'screenData',
    '/assess/news-item-aggregates-by-group/' + group_id + filter
  )
}

export async function selectAllNewsItems(filter_data) {
  // Get all items with pagination for select all functionality
  const PAGE_SIZE = 200
  let allItems = []
  let offset = 0
  let hasMore = true
  let totalCount = 0

  while (hasMore) {
    let filter = '?offset=' + offset
    filter += '&limit=' + PAGE_SIZE
    filter += '&sort=' + encodeURIComponent(filter_data.data.filter.sort)

    if (filter_data.data.filter.search && filter_data.data.filter.search !== '') {
      filter += '&search=' + encodeURIComponent(filter_data.data.filter.search)
    }
    if (filter_data.data.filter.read !== 'ALL') {
      filter += '&read=' + encodeURIComponent(filter_data.data.filter.read === true)
    }
    if (filter_data.data.filter.important !== 'ALL') {
      filter += '&important=' + encodeURIComponent(filter_data.data.filter.important === true)
    }
    if (filter_data.data.filter.relevant !== 'ALL') {
      filter += '&relevant=' + encodeURIComponent(filter_data.data.filter.relevant === true)
    }
    if (filter_data.data.filter.range && filter_data.data.filter.range !== 'ALL') {
      filter += '&range=' + encodeURIComponent(filter_data.data.filter.range)
    }

    const response = await ApiService.get(
      '/assess/news-item-aggregates-by-group/' + filter_data.group_id + filter
    )

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

export function addNewsItem(data) {
  return ApiService.post('/assess/news-items', data)
}

export function voteNewsItemAggregate(group_id, aggregate_id, vote) {
  return ApiService.put('/assess/news-item-aggregates/' + aggregate_id, { group_id, vote })
}

export function readNewsItemAggregate(group_id, aggregate_id) {
  return ApiService.put('/assess/news-item-aggregates/' + aggregate_id, { group_id, read: true })
}

export function deleteNewsItemAggregate(group_id, aggregate_id) {
  return ApiService.delete('/assess/news-item-aggregates/' + aggregate_id)
}

export function importantNewsItemAggregate(group_id, aggregate_id) {
  return ApiService.put('/assess/news-item-aggregates/' + aggregate_id, {
    group_id,
    important: true
  })
}

export function groupAction(data) {
  return ApiService.put('/assess/news-item-aggregates-group-action', data)
}

export function saveNewsItemAggregate(group_id, aggregate_id, title, description, comments) {
  return ApiService.put('/assess/news-item-aggregates/' + aggregate_id, {
    group_id,
    title,
    description,
    comments
  })
}

export function getNewsItem(news_item_id) {
  return ApiService.get('/assess/news-items/' + news_item_id)
}

export function voteNewsItem(group_id, news_item_id, vote) {
  return ApiService.put('/assess/news-items/' + news_item_id, { group_id, vote })
}

export function readNewsItem(group_id, news_item_id) {
  return ApiService.put('/assess/news-items/' + news_item_id, { group_id, read: true })
}

export function deleteNewsItem(group_id, news_item_id) {
  return ApiService.delete('/assess/news-items/' + news_item_id)
}

export function importantNewsItem(group_id, news_item_id) {
  return ApiService.put('/assess/news-items/' + news_item_id, { group_id, important: true })
}
