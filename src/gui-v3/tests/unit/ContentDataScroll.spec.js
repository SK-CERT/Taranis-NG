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

const mockGetAllProductTypes = vi.fn()

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

vi.mock('@/api/config', () => ({
    getAllProductTypes: (...args) => mockGetAllProductTypes(...args)
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

describe('Content data scroll guards', () => {
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
        mockGetAllProductTypes.mockResolvedValue({
            data: {
                items: [{ id: 20, title: 'Product Type' }]
            }
        })
    })

    it('ContentDataAssess stops append loading when all news items are already loaded', async () => {
        const wrapper = mountWithPlugins(ContentDataAssess, {
            props: { analyze_selector: false },
            global: {
                stubs: commonStubs
            }
        })

        try {
            await flushPromises()

            expect(mockAssessStore.loadNewsItemsByGroup).toHaveBeenCalledTimes(1)

            await wrapper.vm.updateData(true, false)
            await flushPromises()

            expect(mockAssessStore.loadNewsItemsByGroup).toHaveBeenCalledTimes(1)
        } finally {
            wrapper.unmount()
        }
    })

    it('ContentDataAnalyze stops append loading when all report items are already loaded', async () => {
        vi.useFakeTimers()
        const wrapper = mountWithPlugins(ContentDataAnalyze, {
            props: { remoteReports: false },
            global: {
                stubs: commonStubs
            }
        })

        try {
            await flushPromises()
            await vi.runAllTimersAsync()
            await flushPromises()

            expect(mockAnalyzeStore.loadReportItems).toHaveBeenCalledTimes(1)
            expect(mockAnalyzeStore.loadReportItemTypes).toHaveBeenCalledTimes(1)

            await wrapper.vm.updateData(true, false)
            await flushPromises()

            expect(mockAnalyzeStore.loadReportItems).toHaveBeenCalledTimes(1)
            expect(mockAnalyzeStore.loadReportItemTypes).toHaveBeenCalledTimes(1)
        } finally {
            wrapper.unmount()
            vi.useRealTimers()
        }
    })

    it('ContentDataPublish stops append loading when all products are already loaded', async () => {
        vi.useFakeTimers()
        const wrapper = mountWithPlugins(ContentDataPublish, {
            props: { selection: [] },
            global: {
                stubs: commonStubs
            }
        })

        try {
            await flushPromises()
            await vi.runAllTimersAsync()
            await flushPromises()

            expect(mockPublishStore.loadProducts).toHaveBeenCalledTimes(1)
            expect(mockGetAllProductTypes).toHaveBeenCalledTimes(1)

            await wrapper.vm.updateData(true, false)
            await flushPromises()

            expect(mockPublishStore.loadProducts).toHaveBeenCalledTimes(1)
            expect(mockGetAllProductTypes).toHaveBeenCalledTimes(1)
        } finally {
            wrapper.unmount()
            vi.useRealTimers()
        }
    })
})
