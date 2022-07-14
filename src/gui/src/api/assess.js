import ApiService from '@/services/api_service'

export function getAllOSINTSourceGroupsAssess () {
  return ApiService.get('/assess/osint-source-groups')
}

export function getOSINTSourceGroupsList () {
  return ApiService.get('/assess/osint-source-group-list')
}

export function getOSINTSourcesList () {
  return ApiService.get('/assess/osint-sources-list')
}

export function getManualOSINTSources () {
  return ApiService.get('/assess/manual-osint-sources')
}

export function getNewsItemsByGroup (group_id, filter_data) {
  const filter = `?search=${encodeURIComponent(filter_data.filter.search)}` +
    `&read=${encodeURIComponent(filter_data.filter.read)}` +
    `&important=${encodeURIComponent(filter_data.filter.important)}` +
    `&relevant=${encodeURIComponent(filter_data.filter.relevant)}` +
    `&in_analyze=${encodeURIComponent(filter_data.filter.in_analyze)}` +
    `&range=${encodeURIComponent(filter_data.filter.range)}` +
    `&sort=${encodeURIComponent(filter_data.filter.sort)}` +
    `&offset=${encodeURIComponent(filter_data.offset)}` +
    `&limit=${encodeURIComponent(filter_data.limit)}`

  return ApiService.get(`/assess/news-item-aggregates-by-group/${group_id}${filter}`)
}

export function addNewsItem (data) {
  return ApiService.post('/assess/news-items', data)
}

export function getNewsItemAggregate (group_id, aggregate_id) {
  return ApiService.get(`/assess/news-item-aggregates/${aggregate_id}`)
}

export function voteNewsItemAggregate (group_id, aggregate_id, vote) {
  return ApiService.put(`/assess/news-item-aggregates/${aggregate_id}`, { group_id: group_id, vote: vote })
}

export function readNewsItemAggregate (group_id, aggregate_id) {
  return ApiService.put(`/assess/news-item-aggregates/${aggregate_id}`, { group_id: group_id, read: true })
}

export function deleteNewsItemAggregate (group_id, aggregate_id) {
  return ApiService.delete(`/assess/news-item-aggregates/${aggregate_id}`)
}

export function importantNewsItemAggregate (group_id, aggregate_id) {
  return ApiService.put(`/assess/news-item-aggregates/${aggregate_id}`, {
    group_id: group_id,
    important: true
  })
}

export function groupAction (data) {
  return ApiService.put('/assess/news-item-aggregates-group-action', data)
}

export function saveNewsItemAggregate (group_id, aggregate_id, title, description, comments) {
  return ApiService.put(`/assess/news-item-aggregates/${aggregate_id}`, {
    group_id: group_id,
    title: title,
    description: description,
    comments: comments
  })
}

export function getNewsItem (news_item_id) {
  return ApiService.get(`/assess/news-items/${news_item_id}`)
}

export function voteNewsItem (group_id, news_item_id, vote) {
  return ApiService.put(`/assess/news-items/${news_item_id}`, { group_id: group_id, vote: vote })
}

export function readNewsItem (group_id, news_item_id) {
  return ApiService.put(`/assess/news-items/${news_item_id}`, { group_id: group_id, read: true })
}

export function deleteNewsItem (group_id, news_item_id) {
  return ApiService.delete(`/assess/news-items/${news_item_id}`)
}

export function importantNewsItem (group_id, news_item_id) {
  return ApiService.put(`/assess/news-items/${news_item_id}`, { group_id: group_id, important: true })
}
