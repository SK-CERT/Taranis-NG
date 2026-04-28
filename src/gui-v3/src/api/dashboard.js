import ApiService from '@/services/api_service'

/**
 * Get dashboard data
 * @param {number} tagCloudDays - Number of days for tag cloud (default: 7)
 */
export function getDashboardData(tagCloudDays = 7) {
  return ApiService.getWithCancel('screenData', `/dashboard-data?tag_cloud_day=${tagCloudDays}`)
}
