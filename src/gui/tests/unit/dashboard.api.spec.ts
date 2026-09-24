import { beforeEach, describe, expect, it, vi } from 'vitest'
import { getDashboardData } from '@/api/dashboard'
import ApiService from '@/services/api_service'

vi.mock('@/services/api_service', () => ({
    default: { getWithCancel: vi.fn() }
}))

describe('dashboard api', () => {
    beforeEach(() => vi.clearAllMocks())

    it('loads the last seven days by default', () => {
        getDashboardData()

        expect(ApiService.getWithCancel).toHaveBeenCalledWith('screenData', '/dashboard-data?tag_cloud_range=LAST_7_DAYS')
    })

    it('loads a named tag-cloud range', () => {
        getDashboardData({ range: 'TODAY' })

        expect(ApiService.getWithCancel).toHaveBeenCalledWith('screenData', '/dashboard-data?tag_cloud_range=TODAY')
    })

    it('loads an explicit tag-cloud interval', () => {
        getDashboardData({ dateFrom: '2026-08-02', dateTo: '2026-08-05' })

        expect(ApiService.getWithCancel).toHaveBeenCalledWith(
            'screenData',
            '/dashboard-data?tag_cloud_date_from=2026-08-02&tag_cloud_date_to=2026-08-05'
        )
    })
})
