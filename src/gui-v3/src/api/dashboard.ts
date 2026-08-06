import ApiService from '@/services/api_service'

export type TagCloudQuery =
    | { range: 'TODAY' | 'LAST_7_DAYS' }
    | {
          dateFrom: string
          dateTo: string
      }

const DEFAULT_TAG_CLOUD_QUERY: TagCloudQuery = { range: 'LAST_7_DAYS' }

/** Get dashboard data for one tag-cloud period. */
export function getDashboardData(tagCloudQuery: TagCloudQuery = DEFAULT_TAG_CLOUD_QUERY) {
    const query = new URLSearchParams()
    if ('range' in tagCloudQuery) {
        query.set('tag_cloud_range', tagCloudQuery.range)
    } else {
        query.set('tag_cloud_date_from', tagCloudQuery.dateFrom)
        query.set('tag_cloud_date_to', tagCloudQuery.dateTo)
    }

    return ApiService.getWithCancel('screenData', `/dashboard-data?${query.toString()}`)
}
