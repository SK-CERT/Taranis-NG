import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { getAllAssets } from '@/api/assets'
import { useAssetsStore } from '@/stores/assets'

vi.mock('@/api/assets', () => ({
    getAllAssetGroups: vi.fn(),
    getAllAssets: vi.fn(),
    getAllNotificationTemplates: vi.fn()
}))

const deferred = <T>() => {
    let resolve!: (value: T) => void
    const promise = new Promise<T>((done) => {
        resolve = done
    })
    return { promise, resolve }
}

describe('assets store request ordering', () => {
    beforeEach(() => {
        setActivePinia(createPinia())
        vi.clearAllMocks()
    })

    it('does not let a stale group request overwrite a newer route request', async () => {
        const first = deferred<{ data: { total_count: number; items: Array<{ id: number; name: string }> } }>()
        const second = deferred<{ data: { total_count: number; items: Array<{ id: number; name: string }> } }>()
        vi.mocked(getAllAssets)
            .mockReturnValueOnce(first.promise as unknown as ReturnType<typeof getAllAssets>)
            .mockReturnValueOnce(second.promise as unknown as ReturnType<typeof getAllAssets>)
        const store = useAssetsStore()

        const oldGroup = store.loadAssets({ group_id: 'old', filter: { search: '', vulnerable: false, sort: 'ALPHABETICAL' } })
        const currentGroup = store.loadAssets({ group_id: 'current', filter: { search: '', vulnerable: false, sort: 'ALPHABETICAL' } })

        second.resolve({ data: { total_count: 1, items: [{ id: 2, name: 'current asset' }] } })
        await currentGroup
        first.resolve({ data: { total_count: 1, items: [{ id: 1, name: 'stale asset' }] } })
        await oldGroup

        expect(store.assets.items).toEqual([{ id: 2, name: 'current asset' }])
    })
})
