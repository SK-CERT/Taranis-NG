import ApiService from '@/services/api_service'

export function getAllReportItemGroups () {
  return ApiService.get('/analyze/report-item-groups')
}

export function getAllReportItems (filter_data) {
  let filter = `?search=${encodeURIComponent(filter_data.filter.search)}` +
    `&completed=${encodeURIComponent(filter_data.filter.completed)}` +
    `&incompleted=${encodeURIComponent(filter_data.filter.incompleted)}` +
    `&range=${encodeURIComponent(filter_data.filter.range)}` +
    `&sort=${encodeURIComponent(filter_data.filter.sort)}` +
    `&offset=${encodeURIComponent(filter_data.offset)}` +
    `&limit=${encodeURIComponent(filter_data.limit)}`
  if (filter_data.group !== null) {
    filter += `&group=${encodeURIComponent(filter_data.group)}`
  }

  return ApiService.get(`/analyze/report-items${filter}`)
}

export function getReportItem (report_item_id) {
  return ApiService.get(`/analyze/report-items/${report_item_id}`)
}

export function getReportItemData (report_item_id, data) {
  let params = ''
  if (data.update !== undefined) {
    params += `&update=${encodeURIComponent(data.update)}`
  }
  if (data.add !== undefined) {
    params += `&add=${encodeURIComponent(data.add)}`
  }
  if (data.title !== undefined) {
    params += `&title=${encodeURIComponent(data.title)}`
  }
  if (data.title_prefix !== undefined) {
    params += `&title_prefix=${encodeURIComponent(data.title_prefix)}`
  }
  if (data.attribute_id !== undefined) {
    params += `&attribute_id=${encodeURIComponent(data.attribute_id)}`
  }
  if (data.completed !== undefined) {
    params += `&completed=${encodeURIComponent(data.completed)}`
  }
  if (data.aggregate_ids !== undefined) {
    let aggregate_ids = ''
    for (const aggregate_id in data.aggregate_ids) { // FIXME(mw): this can probably be solved quicker with Array.reduce
      aggregate_ids += '--' + aggregate_id
    }
    aggregate_ids = aggregate_ids.replace('--', '')
    params += `&aggregate_ids=${encodeURIComponent(aggregate_ids)}`
  }
  if (data.remote_report_item_ids !== undefined) {
    let remote_report_item_ids = ''
    for (const remote_report_item_id in data.remote_report_item_ids) {
      remote_report_item_ids += '--' + remote_report_item_id
    }
    remote_report_item_ids = remote_report_item_ids.replace('--', '')
    params += `&remote_report_item_ids=${encodeURIComponent(remote_report_item_ids)}`
  }

  params = params.replace('&', '?')

  return ApiService.get(`/analyze/report-items/${report_item_id}/data${params}`)
}

export function createNewReportItem (data) {
  return ApiService.post('/analyze/report-items', data)
}

export function deleteReportItem (report_item) {
  return ApiService.delete(`/analyze/report-items/${report_item.id}`)
}

export function updateReportItem (report_item_id, data) {
  return ApiService.put(`/analyze/report-items/${report_item_id}`, data)
}

export function getReportItemLocks (report_item_id) {
  return ApiService.get(`/analyze/report-items/${report_item_id}/field-locks`)
}

export function lockReportItem (report_item_id, data) {
  return ApiService.put(`/analyze/report-items/${report_item_id}/field-locks/${data.field_id}/lock`, data)
}

export function unlockReportItem (report_item_id, data) {
  return ApiService.put(`/analyze/report-items/${report_item_id}/field-locks/${data.field_id}/unlock`, data)
}

export function holdLockReportItem (report_item_id, data) {
  return ApiService.put(`/analyze/report-items/${report_item_id}/field-locks/${data.field_id}/hold`, data)
}

export function getAllReportItemTypes () {
  return ApiService.get('/analyze/report-item-types')
}

export function getAttributeEnums (filter) {
  return ApiService.get(`/analyze/report-item-attributes/${filter.attribute_id}/enums?search=${filter.search}&offset=${filter.offset}&limit=${filter.limit}`)
}

export function removeAttachment (data) {
  return ApiService.delete(`/analyze/report-items/${data.report_item_id}/file-attributes/${data.attribute_id}`)
}
