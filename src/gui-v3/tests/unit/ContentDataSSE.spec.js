import { describe, it, expect, beforeEach, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { mountWithPlugins } from '../helpers/mount-helpers'
import ContentDataAssess from '@/components/assess/ContentDataAssess.vue'
import ContentDataAnalyze from '@/components/analyze/ContentDataAnalyze.vue'
import ContentDataPublish from '@/components/publish/ContentDataPublish.vue'

const mockRoute = {
    params: {
        groupId: 'all',
        scope: 'local'
    }
}

const mockAssessStore = {
    getMultiSelect: false,
    getCurrentGroup: 'all',
    getNewsItems: { total_count: 2, items: [] },
    changeCurrentGroup: vi.fn(),
    loadNewsItemsByGroup: vi.fn(),
    voteNewsItemAggregate: vi.fn(),
    importantNewsItemAggregate: vi.fn(),
    readNewsItemAggregate: vi.fn(),
    saveNewsItemAggregate: vi.fn(),
    deleteNewsItemAggregate: vi.fn(),
    select: vi.fn(),
    deselect: vi.fn()
}

const mockAnalyzeStore = {
    getMultiSelectReport: false,
    getCurrentReportItemGroup: '',
    getReportItems: { total_count: 2, items: [] },
    getReportItemTypes: { items: [] },
    loadReportItems: vi.fn(),
    loadReportItemTypes: vi.fn(),
    selectReport: vi.fn(),
    deselectReport: vi.fn()
}

const mockPublishStore = {
    getMultiSelect: false,
    getProducts: { total_count: 2, items: [] },
    loadProducts: vi.fn(),
    select: vi.fn(),
    deselect: vi.fn()
}

const mockGetAllUserProductTypes = vi.fn()

vi.mock('vue-router', () => ({
    useRoute: () => mockRoute
}))

vi.mock('@/stores/assess', () => ({
    useAssessStore: () => mockAssessStore
}))

vi.mock('@/stores/analyze', () => ({
    useAnalyzeStore: () => mockAnalyzeStore
}))

vi.mock('@/stores/publish', () => ({
    usePublishStore: () => mockPublishStore
}))

vi.mock('@/api/user', () => ({
    getAllUserProductTypes: (...args) => mockGetAllUserProductTypes(...args)
}))

const commonStubs = {
    CardAssess: { template: '<div class="card-assess-stub" />', props: ['card'] },
    CardAnalyze: { template: '<div class="card-analyze-stub" />', props: ['card'] },
    CardProduct: { template: '<div class="card-product-stub" />', props: ['card'] },
    CardCompact: { template: '<div class="card-compact-stub" />', props: ['card'] },
    NewsItemDetailDialog: true,
    ReportsListDialog: true,
    NewReportItem: true
}

describe('SSE consumer components', () => {
    beforeEach(() => {
        vi.clearAllMocks()

        mockRoute.params.groupId = 'all'
        mockRoute.params.scope = 'local'

        mockAssessStore.getMultiSelect = false
        mockAssessStore.getCurrentGroup = 'all'
        mockAssessStore.getNewsItems = {
            total_count: 2,
            items: [
                { id: 1, title: 'Item 1' },
                { id: 2, title: 'Item 2' }
            ]
        }
        mockAssessStore.loadNewsItemsByGroup.mockResolvedValue({ data: mockAssessStore.getNewsItems })

        mockAnalyzeStore.getMultiSelectReport = false
        mockAnalyzeStore.getCurrentReportItemGroup = ''
        mockAnalyzeStore.getReportItems = {
            total_count: 2,
            items: [
                { id: 1, report_item_type_id: 10, title: 'Report 1' },
                { id: 2, report_item_type_id: 10, title: 'Report 2' }
            ]
        }
        mockAnalyzeStore.getReportItemTypes = {
            items: [{ id: 10, title: 'Report Type' }]
        }
        mockAnalyzeStore.loadReportItems.mockResolvedValue({ data: mockAnalyzeStore.getReportItems })
        mockAnalyzeStore.loadReportItemTypes.mockResolvedValue({ data: mockAnalyzeStore.getReportItemTypes })

        mockPublishStore.getMultiSelect = false
        mockPublishStore.getProducts = {
            total_count: 2,
            items: [
                { id: 1, product_type_id: 20, title: 'Product 1' },
                { id: 2, product_type_id: 20, title: 'Product 2' }
            ]
        }
        mockPublishStore.loadProducts.mockResolvedValue({ data: mockPublishStore.getProducts })
        mockGetAllUserProductTypes.mockResolvedValue({
            data: {
                items: [{ id: 20, title: 'Product Type' }]
            }
        })
    })

    it('ContentDataAssess reloads on news-items-updated and stops after unmount', async () => {
        vi.useFakeTimers()

        const wrapper = mountWithPlugins(ContentDataAssess, {
            props: { analyze_selector: false },
            global: {
                stubs: commonStubs
            }
        })

        try {
            await flushPromises()
            expect(mockAssessStore.loadNewsItemsByGroup).toHaveBeenCalledTimes(1)

            // SSE refreshes are coalesced behind a short timer, so they need to be waited out.
            window.dispatchEvent(new CustomEvent('news-items-updated', { detail: {} }))
            await vi.advanceTimersByTimeAsync(500)
            await flushPromises()
            expect(mockAssessStore.loadNewsItemsByGroup).toHaveBeenCalledTimes(2)

            wrapper.unmount()
            window.dispatchEvent(new CustomEvent('news-items-updated', { detail: {} }))
            await vi.advanceTimersByTimeAsync(500)
            await flushPromises()
            expect(mockAssessStore.loadNewsItemsByGroup).toHaveBeenCalledTimes(2)
        } finally {
            vi.useRealTimers()
        }
    })

    it('ContentDataAssess coalesces a burst of news-items-updated events into one reload', async () => {
        vi.useFakeTimers()

        const wrapper = mountWithPlugins(ContentDataAssess, {
            props: { analyze_selector: false },
            global: {
                stubs: commonStubs
            }
        })

        try {
            await flushPromises()
            expect(mockAssessStore.loadNewsItemsByGroup).toHaveBeenCalledTimes(1)

            // A collector run emits one event per batch; reloading the whole list for each
            // of them re-renders the cards under the user and moves the scroll position.
            for (let i = 0; i < 10; i++) {
                window.dispatchEvent(new CustomEvent('news-items-updated', { detail: {} }))
                await vi.advanceTimersByTimeAsync(20)
            }
            await vi.advanceTimersByTimeAsync(500)
            await flushPromises()

            expect(mockAssessStore.loadNewsItemsByGroup).toHaveBeenCalledTimes(2)
        } finally {
            wrapper.unmount()
            vi.useRealTimers()
        }
    })

    it('ContentDataAnalyze reloads on report-item-updated and report-items-updated, then stops after unmount', async () => {
        const wrapper = mountWithPlugins(ContentDataAnalyze, {
            props: { remoteReports: false },
            global: {
                stubs: commonStubs
            }
        })

        await flushPromises()
        expect(mockAnalyzeStore.loadReportItems).toHaveBeenCalledTimes(1)
        expect(mockAnalyzeStore.loadReportItemTypes).toHaveBeenCalledTimes(1)

        window.dispatchEvent(new CustomEvent('report-item-updated', { detail: { report_item_id: 1 } }))
        await flushPromises()

        window.dispatchEvent(new CustomEvent('report-items-updated', { detail: {} }))
        await flushPromises()

        expect(mockAnalyzeStore.loadReportItems).toHaveBeenCalledTimes(3)
        expect(mockAnalyzeStore.loadReportItemTypes).toHaveBeenCalledTimes(3)

        wrapper.unmount()
        window.dispatchEvent(new CustomEvent('report-item-updated', { detail: { report_item_id: 1 } }))
        await flushPromises()
        expect(mockAnalyzeStore.loadReportItems).toHaveBeenCalledTimes(3)
    })

    it('ContentDataPublish reloads on product-updated and stops after unmount', async () => {
        let wrapper

        try {
            wrapper = mountWithPlugins(ContentDataPublish, {
                props: { selection: [] },
                global: {
                    stubs: commonStubs
                }
            })

            await flushPromises()

            expect(mockPublishStore.loadProducts).toHaveBeenCalledTimes(1)
            expect(mockGetAllUserProductTypes).toHaveBeenCalledTimes(1)

            window.dispatchEvent(new CustomEvent('product-updated', { detail: {} }))
            await flushPromises()

            const productReloadCalls = mockPublishStore.loadProducts.mock.calls.length
            const productTypeReloadCalls = mockGetAllUserProductTypes.mock.calls.length

            expect(productReloadCalls).toBeGreaterThan(1)
            expect(productTypeReloadCalls).toBeGreaterThan(1)

            wrapper.unmount()
            window.dispatchEvent(new CustomEvent('product-updated', { detail: {} }))
            await flushPromises()

            expect(mockPublishStore.loadProducts).toHaveBeenCalledTimes(productReloadCalls)
            expect(mockGetAllUserProductTypes).toHaveBeenCalledTimes(productTypeReloadCalls)
        } finally {
            wrapper?.unmount()
        }
    })
})
