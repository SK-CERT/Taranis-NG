import ApiService from '@/services/api_service'

function buildFilterQueryString(filter_data) {
    let filter = '?offset=' + encodeURIComponent(filter_data.offset || 0)
    filter += '&limit=' + encodeURIComponent(filter_data.limit || 50)
    filter += '&sort=' + encodeURIComponent(filter_data.filter.sort)

    if (filter_data.filter.search != '') {
        filter += '&search=' + encodeURIComponent(filter_data.filter.search)
    }
    if (filter_data.filter.completed != 'ALL') {
        filter += '&completed=' + encodeURIComponent(filter_data.filter.completed)
    }
    if (filter_data.filter.range != 'ALL') {
        filter += '&range=' + encodeURIComponent(filter_data.filter.range)
    }
    if (filter_data.group) {
        filter += '&group=' + encodeURIComponent(filter_data.group)
    }
    return filter
}

export function getAllReportItemGroups() {
    return ApiService.get('/analyze/report-item-groups')
}

export function getAllReportItems(filter_data) {
    return ApiService.getWithCancel('screenData', '/analyze/report-items' + buildFilterQueryString(filter_data))
}

export async function getAllReportItemsUnpaginated(filter_data) {
    // Get all items with pagination for select all functionality
    const PAGE_SIZE = 200
    let allItems = []
    let hasMore = true
    let totalCount = 0

    filter_data.offset = 0
    filter_data.limit = PAGE_SIZE

    while (hasMore) {
        const filter = buildFilterQueryString(filter_data)
        const response = await ApiService.get('/analyze/report-items' + filter)

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

export function getReportItem(report_item_id) {
    return ApiService.get('/analyze/report-items/' + report_item_id)
}

export function getReportItemData(report_item_id, data) {
    let params = ''
    if (data.update !== undefined) {
        params += '&update=' + encodeURIComponent(data.update)
    }
    if (data.add !== undefined) {
        params += '&add=' + encodeURIComponent(data.add)
    }
    if (data.title !== undefined) {
        params += '&title=' + encodeURIComponent(data.title)
    }
    if (data.title_prefix !== undefined) {
        params += '&title_prefix=' + encodeURIComponent(data.title_prefix)
    }
    if (data.attribute_id !== undefined) {
        params += '&attribute_id=' + encodeURIComponent(data.attribute_id)
    }
    if (data.completed !== undefined) {
        params += '&completed=' + encodeURIComponent(data.completed)
    }
    if (data.aggregate_ids !== undefined) {
        let aggregate_ids = ''
        for (const aggregate_id in data.aggregate_ids) {
            aggregate_ids += '--' + aggregate_id
        }
        aggregate_ids = aggregate_ids.replace('--', '')
        params += '&aggregate_ids=' + encodeURIComponent(aggregate_ids)
    }
    if (data.remote_report_item_ids !== undefined) {
        let remote_report_item_ids = ''
        for (const remote_report_item_id in data.remote_report_item_ids) {
            remote_report_item_ids += '--' + remote_report_item_id
        }
        remote_report_item_ids = remote_report_item_ids.replace('--', '')
        params += '&remote_report_item_ids=' + encodeURIComponent(remote_report_item_ids)
    }

    params = params.replace('&', '?')

    return ApiService.get('/analyze/report-items/' + report_item_id + '/data' + params)
}

export function createNewReportItem(data) {
    const payload = {
        uuid: data.uuid || null,
        title: data.title,
        title_prefix: data.title_prefix,
        report_item_type_id: data.report_item_type_id,
        state_id: data.state_id,
        news_item_aggregates: data.news_item_aggregates || [],
        remote_report_items: data.remote_report_items || [],
        attributes: data.attributes || []
    }

    return ApiService.post('/analyze/report-items', payload)
}

export function deleteReportItem(report_item) {
    return ApiService.delete('/analyze/report-items/' + report_item.id)
}

export function updateReportItem(report_item_id, data) {
    return ApiService.put('/analyze/report-items/' + report_item_id, data)
}

export function getReportItemLocks(report_item_id) {
    return ApiService.get('/analyze/report-items/' + report_item_id + '/field-locks')
}

export function lockReportItem(report_item_id, data) {
    return ApiService.put('/analyze/report-items/' + report_item_id + '/field-locks/' + data.field_id + '/lock', data)
}

export function unlockReportItem(report_item_id, data) {
    return ApiService.put('/analyze/report-items/' + report_item_id + '/field-locks/' + data.field_id + '/unlock', data)
}

export function holdLockReportItem(report_item_id, data) {
    return ApiService.put('/analyze/report-items/' + report_item_id + '/field-locks/' + data.field_id + '/hold', data)
}

export function getAllReportItemTypes() {
    return ApiService.get('/analyze/report-item-types')
}

export function getAttributeEnums(filter) {
    return ApiService.get(
        '/analyze/report-item-attributes/' +
            filter.attribute_id +
            '/enums?search=' +
            filter.search +
            '&offset=' +
            filter.offset +
            '&limit=' +
            filter.limit
    )
}

export function removeAttachment(data) {
    return ApiService.delete('/analyze/report-items/' + data.report_item_id + '/file-attributes/' + data.attribute_id)
}

export function aiGenerate(attribute_id, news_item_agreggate_ids) {
    return ApiService.post('/analyze/report-item-attributes/' + attribute_id + '/llm-generate', {
        news_item_agreggate_ids
    })
}

export function getReportItemsByAggregate(aggregate_id) {
    return ApiService.get('/analyze/report-items-by-aggregate/' + aggregate_id)
}

export function downloadAttachment(download_link, optional_file_name) {
    return ApiService.download(download_link, undefined, optional_file_name)
}
