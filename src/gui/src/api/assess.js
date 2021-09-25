import ApiService from "@/services/api_service";

export function getAllOSINTSourceGroupsAssess() {
    return ApiService.get('/assess/sources/groups')
}

export function getNewsItemsByGroup(group_id, data) {
    return ApiService.post('/assess/newsitems/group/' + group_id, data)
}

export function addNewsItem(data) {
    return ApiService.post('/assess/newsitem/add', data)
}

export function voteNewsItemAggregate(group_id, aggregate_id, vote) {
    return ApiService.put('/assess/newsitems/aggregate/' + aggregate_id, {group_id: group_id, vote: vote})
}

export function readNewsItemAggregate(group_id, aggregate_id) {
    return ApiService.put('/assess/newsitems/aggregate/' + aggregate_id, { group_id: group_id, read: true})
}

export function deleteNewsItemAggregate(group_id, aggregate_id) {
    return ApiService.delete('/assess/newsitems/aggregate/' + aggregate_id, {group_id: group_id, delete: true})
}

export function importantNewsItemAggregate(group_id, aggregate_id) {
    return ApiService.put('/assess/newsitems/aggregate/' + aggregate_id, {
        group_id: group_id,
        important: true
    })
}

export function groupAction(data) {
    if (data.type === 'delete') {
        return ApiService.delete('/assess/newsitems/group/action', data)
    } else {
        return ApiService.post('/assess/newsitems/group/action', data)
    }
}

export function saveNewsItemAggregate(group_id, aggregate_id, title, description, comments) {
    return ApiService.put('/assess/newsitems/aggregate/' + aggregate_id, {
        group_id: group_id,
        title: title,
        description: description,
        comments: comments
    })
}

export function getNewsItem(news_item_id) {
    return ApiService.get('/assess/newsitem/' + news_item_id)
}

export function voteNewsItem(group_id, news_item_id, vote) {
    return ApiService.put('/assess/newsitem/' + news_item_id, {group_id: group_id, vote: vote})
}

export function readNewsItem(group_id, news_item_id) {
    return ApiService.put('/assess/newsitem/' + news_item_id, {group_id: group_id, read: true})
}

export function deleteNewsItem(group_id, news_item_id) {
    return ApiService.delete('/assess/newsitem/' + news_item_id, {group_id: group_id, delete: true})
}

export function importantNewsItem(group_id, news_item_id) {
    return ApiService.put('/assess/newsitem/' + news_item_id, {group_id: group_id, important: true})
}