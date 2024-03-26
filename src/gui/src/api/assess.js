import ApiService from "@/services/api_service";

export function getAllOSINTSourceGroupsAssess() {
    return ApiService.get('/assess/osint-source-groups')
}

export function getManualOSINTSources() {
    return ApiService.get('/assess/manual-osint-sources')
}

export function getNewsItemsByGroup(group_id, filter_data) {
    let filter = "?search=" + encodeURIComponent(filter_data.filter.search)
    filter += "&read=" + encodeURIComponent(filter_data.filter.read)
    filter += "&important=" + encodeURIComponent(filter_data.filter.important)
    filter += "&relevant=" + encodeURIComponent(filter_data.filter.relevant)
    filter += "&in_analyze=" + encodeURIComponent(filter_data.filter.in_analyze)
    filter += "&range=" + encodeURIComponent(filter_data.filter.range)
    filter += "&sort=" + encodeURIComponent(filter_data.filter.sort)
    filter += "&offset=" + encodeURIComponent(filter_data.offset)
    filter += "&limit=" + encodeURIComponent(filter_data.limit)

    return ApiService.getWithCancel('screenData', '/assess/news-item-aggregates-by-group/' + group_id + filter)
}

export function addNewsItem(data) {
    return ApiService.post('/assess/news-items', data)
}

export function voteNewsItemAggregate(group_id, aggregate_id, vote) {
    return ApiService.put('/assess/news-item-aggregates/' + aggregate_id, {group_id: group_id, vote: vote})
}

export function readNewsItemAggregate(group_id, aggregate_id) {
    return ApiService.put('/assess/news-item-aggregates/' + aggregate_id, {group_id: group_id, read: true})
}

export function deleteNewsItemAggregate(group_id, aggregate_id) {
    return ApiService.delete('/assess/news-item-aggregates/' + aggregate_id)
}

export function importantNewsItemAggregate(group_id, aggregate_id) {
    return ApiService.put('/assess/news-item-aggregates/' + aggregate_id, {
        group_id: group_id,
        important: true
    })
}

export function groupAction(data) {
    return ApiService.put('/assess/news-item-aggregates-group-action', data)
}

export function saveNewsItemAggregate(group_id, aggregate_id, title, description, comments) {
    return ApiService.put('/assess/news-item-aggregates/' + aggregate_id, {
        group_id: group_id,
        title: title,
        description: description,
        comments: comments
    })
}

export function getNewsItem(news_item_id) {
    return ApiService.get('/assess/news-items/' + news_item_id)
}

export function voteNewsItem(group_id, news_item_id, vote) {
    return ApiService.put('/assess/news-items/' + news_item_id, {group_id: group_id, vote: vote})
}

export function readNewsItem(group_id, news_item_id) {
    return ApiService.put('/assess/news-items/' + news_item_id, {group_id: group_id, read: true})
}

export function deleteNewsItem(group_id, news_item_id) {
    return ApiService.delete('/assess/news-items/' + news_item_id)
}

export function importantNewsItem(group_id, news_item_id) {
    return ApiService.put('/assess/news-items/' + news_item_id, {group_id: group_id, important: true})
}