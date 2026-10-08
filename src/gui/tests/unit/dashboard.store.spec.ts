import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { getDashboardData } from '@/api/dashboard'
import { useDashboardStore } from '@/stores/dashboard'

vi.mock('@/api/dashboard', () => ({
    getDashboardData: vi.fn()
}))

describe('dashboard store', () => {
    beforeEach(() => {
        setActivePinia(createPinia())
        vi.mocked(getDashboardData).mockReset()
    })

    it('keeps the first day the tag cloud still holds', async () => {
        vi.mocked(getDashboardData).mockResolvedValue({
            data: { tag_cloud: [{ word: 'kernel', word_quantity: 3 }], tag_cloud_oldest_date: '2026-09-22' }
        } as never)
        const store = useDashboardStore()

        await store.loadDashboardData({ range: 'LAST_7_DAYS' })

        expect(store.dashboard_data.tag_cloud_oldest_date).toBe('2026-09-22')
        expect(store.dashboard_data.tag_cloud).toEqual([{ word: 'kernel', word_quantity: 3 }])
    })

    it('leaves the oldest day empty when core does not send one', async () => {
        vi.mocked(getDashboardData).mockResolvedValue({ data: { tag_cloud: [] } } as never)
        const store = useDashboardStore()

        await store.loadDashboardData()

        expect(store.dashboard_data.tag_cloud_oldest_date).toBe('')
    })
})
