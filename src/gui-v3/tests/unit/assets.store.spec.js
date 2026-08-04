import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useAssetsStore } from '@/stores/assets'
import * as assetsApi from '@/api/assets'

vi.mock('@/api/assets', () => ({
    getAllAssetGroups: vi.fn(),
    getAllNotificationTemplates: vi.fn(),
    getAllAssets: vi.fn()
}))

describe('assets store', () => {
    beforeEach(() => {
        setActivePinia(createPinia())
        vi.clearAllMocks()
    })

    it('loads asset groups', async () => {
        vi.mocked(assetsApi.getAllAssetGroups).mockResolvedValue({ data: { total_count: 1, items: [{ id: 'g1', name: 'Group' }] } })
        const store = useAssetsStore()
        await store.loadAssetGroups({ search: 'Group' })
        expect(assetsApi.getAllAssetGroups).toHaveBeenCalledWith({ search: 'Group' })
        expect(store.assetGroups.items).toEqual([{ id: 'g1', name: 'Group' }])
    })

    it('loads assets for a group and can clear them', async () => {
        const request = { group_id: 'g1', filter: { search: '', sort: 'ALPHABETICAL', vulnerable: false } }
        vi.mocked(assetsApi.getAllAssets).mockResolvedValue({ data: { total_count: 1, items: [{ id: 1, name: 'Host' }] } })
        const store = useAssetsStore()
        await store.loadAssets(request)
        expect(store.assets.total_count).toBe(1)
        store.clearAssets()
        expect(store.assets).toEqual({ total_count: 0, items: [] })
    })
})
