import { describe, it, expect, vi } from 'vitest'
import { reactive } from 'vue'
import { flushPromises } from '@vue/test-utils'
import { mountWithPlugins } from '../helpers/mount-helpers'
import { useAssetsStore } from '@/stores/assets'
import { getAllAssetGroups } from '@/api/assets'
import MyAssetsView from '@/views/users/MyAssetsView.vue'

const route = reactive({ params: { groupId: '3' } })
vi.mock('vue-router', () => ({ useRoute: () => route }))
vi.mock('@/composables/useAuth', () => ({ useAuth: () => ({ checkPermission: () => true }) }))
vi.mock('@/api/assets', () => ({ getAllAssetGroups: vi.fn(), getAllAssets: vi.fn(), getAllNotificationTemplates: vi.fn() }))

function mountView() {
    return mountWithPlugins(MyAssetsView, {
        global: {
            stubs: {
                ViewLayout: { template: '<div><slot name="panel"/><slot name="content"/></div>' },
                ContentDataAssets: { template: '<div data-test="asset-list" />' },
                ToolbarFilterAssets: true,
                AssetDialog: true
            }
        }
    })
}

describe('asset group loading presentation', () => {
    it('keeps loading visible until groups arrive and the initial group route is selected', async () => {
        route.params.groupId = ''
        const wrapper = mountView()
        const store = useAssetsStore()
        let resolveRequest
        getAllAssetGroups.mockImplementationOnce(
            () =>
                new Promise((resolve) => {
                    resolveRequest = resolve
                })
        )
        try {
            const request = store.loadAssetGroups()
            await flushPromises()
            expect(wrapper.find('.content-skeleton').exists()).toBe(true)
            expect(wrapper.find('.v-alert').exists()).toBe(false)
            expect(store.assetGroupsLoaded).toBe(false)

            resolveRequest({ data: { total_count: 1, items: [{ id: 3, name: 'Servers' }] } })
            await request
            await flushPromises()
            expect(wrapper.find('.content-skeleton').exists()).toBe(true)
            expect(wrapper.find('.v-alert').exists()).toBe(false)

            route.params.groupId = '3'
            await flushPromises()
            expect(wrapper.find('[data-test="asset-list"]').exists()).toBe(true)
            expect(wrapper.find('.v-alert').exists()).toBe(false)
        } finally {
            wrapper.unmount()
        }
    })

    it('shows the empty state only after a successful empty response', async () => {
        route.params.groupId = ''
        const wrapper = mountView()
        try {
            getAllAssetGroups.mockResolvedValueOnce({ data: { total_count: 0, items: [] } })
            await useAssetsStore().loadAssetGroups()
            await flushPromises()
            expect(wrapper.find('.content-skeleton').exists()).toBe(false)
            expect(wrapper.find('.v-alert').exists()).toBe(true)
        } finally {
            wrapper.unmount()
        }
    })

    it('shows a loading error instead of not-found when the groups request fails', async () => {
        route.params.groupId = '3'
        const wrapper = mountView()
        try {
            getAllAssetGroups.mockRejectedValueOnce(new Error('Request failed'))
            await expect(useAssetsStore().loadAssetGroups()).rejects.toThrow('Request failed')
            await flushPromises()
            expect(wrapper.find('.content-skeleton').exists()).toBe(false)
            expect(wrapper.findComponent({ name: 'VAlert' }).props('type')).toBe('error')
            expect(useAssetsStore().assetGroupsLoaded).toBe(false)
        } finally {
            wrapper.unmount()
        }
    })
})
