import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { mountWithPlugins } from '../helpers/mount-helpers'
import ContentDataAssets from '@/components/assets/ContentDataAssets.vue'
import MyAssetsNav from '@/views/nav/MyAssetsNav.vue'
import DashboardView from '@/views/users/DashboardView.vue'

const mocks = vi.hoisted(() => ({
    route: { path: '/myassets/group/3', params: { groupId: '3' } },
    router: { push: vi.fn(), replace: vi.fn() },
    assetsStore: {
        assetGroups: { total_count: 1, items: [{ id: 3, name: 'Servers' }] },
        assets: { total_count: 1, items: [{ id: 8, name: 'host.example' }] },
        loadAssetGroups: vi.fn().mockResolvedValue({}),
        loadAssets: vi.fn().mockResolvedValue({}),
        clearAssets: vi.fn()
    },
    dashboardStore: {
        dashboard_data: {
            total_news_items: 1,
            total_products: 2,
            total_report_items: 3,
            total_database_items: 4,
            latest_collected: '',
            news_items_by_day: [],
            tag_cloud: [],
            report_item_states: {},
            product_states: {}
        },
        loadDashboardData: vi.fn().mockResolvedValue(undefined)
    }
}))

vi.mock('vue-router', () => ({
    useRoute: () => mocks.route,
    useRouter: () => mocks.router
}))

vi.mock('@/stores/assets', () => ({ useAssetsStore: () => mocks.assetsStore }))
vi.mock('@/stores/dashboard', () => ({ useDashboardStore: () => mocks.dashboardStore }))
vi.mock('@/api/assets', () => ({ deleteAsset: vi.fn() }))
vi.mock('@/composables/useAuth', () => ({ useAuth: () => ({ checkPermission: () => true }) }))

const stubs = {
    CardAsset: { template: '<div class="asset-card-stub" />' },
    GroupNavList: { template: '<div class="group-nav-stub" />' },
    WordCloud: { template: '<div class="word-cloud-stub" />' },
    VDialog: {
        props: ['modelValue'],
        template: '<div v-if="modelValue" class="dialog-stub"><slot /></div>'
    }
}

describe('SSE resynchronization for Assets and Dashboard', () => {
    beforeEach(() => {
        vi.useFakeTimers()
        vi.setSystemTime(new Date(2026, 7, 6, 12, 0, 0))
        vi.clearAllMocks()
    })

    afterEach(() => {
        vi.useRealTimers()
    })

    it('refreshes the active asset group and asset-group navigation once per signal burst', async () => {
        const content = mountWithPlugins(ContentDataAssets, { global: { stubs } })
        const navigation = mountWithPlugins(MyAssetsNav, { global: { stubs } })

        try {
            await flushPromises()
            vi.clearAllMocks()

            for (let i = 0; i < 6; i++) window.dispatchEvent(new CustomEvent('sse-resync'))
            await vi.advanceTimersByTimeAsync(100)
            await flushPromises()

            expect(mocks.assetsStore.loadAssets).toHaveBeenCalledTimes(1)
            expect(mocks.assetsStore.loadAssets).toHaveBeenCalledWith({
                group_id: '3',
                filter: { search: '', vulnerable: false, sort: 'ALPHABETICAL' }
            })
            expect(mocks.assetsStore.loadAssetGroups).toHaveBeenCalledTimes(1)
            expect(mocks.assetsStore.clearAssets).not.toHaveBeenCalled()
        } finally {
            content.unmount()
            navigation.unmount()
        }
    })

    it('refreshes Dashboard after a missed-event signal and coalesces bursts', async () => {
        const wrapper = mountWithPlugins(DashboardView, { global: { stubs } })

        try {
            await flushPromises()
            mocks.dashboardStore.loadDashboardData.mockClear()

            window.dispatchEvent(new CustomEvent('sse-resync'))
            window.dispatchEvent(new CustomEvent('sse-resync'))
            await vi.advanceTimersByTimeAsync(100)
            await flushPromises()

            expect(mocks.dashboardStore.loadDashboardData).toHaveBeenCalledTimes(1)
        } finally {
            wrapper.unmount()
        }
    })

    it('loads the selected tag-cloud interval and excludes today from custom dates', async () => {
        const wrapper = mountWithPlugins(DashboardView, { global: { stubs } })

        try {
            await flushPromises()
            expect(mocks.dashboardStore.loadDashboardData).toHaveBeenLastCalledWith({ range: 'LAST_7_DAYS' })

            const button = (label) => wrapper.findAll('button').find((candidate) => candidate.text().trim() === label)

            await button('Today').trigger('click')
            await flushPromises()
            expect(mocks.dashboardStore.loadDashboardData).toHaveBeenLastCalledWith({ range: 'TODAY' })

            await button('yesterday').trigger('click')
            await flushPromises()
            expect(mocks.dashboardStore.loadDashboardData).toHaveBeenLastCalledWith({
                dateFrom: '2026-08-05',
                dateTo: '2026-08-05'
            })

            await button('Custom Filter').trigger('click')
            await flushPromises()
            const dateInputs = wrapper.findAll('input[type="date"]')
            expect(dateInputs).toHaveLength(2)
            expect(dateInputs[1].attributes('max')).toBe('2026-08-05')

            await dateInputs[0].setValue('2026-08-02')
            await dateInputs[1].setValue('2026-08-04')
            await button('Done').trigger('click')
            await flushPromises()
            expect(mocks.dashboardStore.loadDashboardData).toHaveBeenLastCalledWith({
                dateFrom: '2026-08-02',
                dateTo: '2026-08-04'
            })

            await button('Custom Filter').trigger('click')
            await flushPromises()
            expect(wrapper.findAll('input[type="date"]')).toHaveLength(2)
        } finally {
            wrapper.unmount()
        }
    })
})
