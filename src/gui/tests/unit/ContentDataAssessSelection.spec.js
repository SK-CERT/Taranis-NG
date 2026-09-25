import { describe, it, expect, beforeEach, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { mountWithPlugins } from '../helpers/mount-helpers'
import ContentDataAssess from '@/components/assess/ContentDataAssess.vue'

/**
 * The full card keeps the selection in step itself; the compact card only emits its checkbox and
 * relies on this component. That listener was missing, so in compact mode ticking a card changed
 * nothing in the store - and after "select all", unchecking one left it selected, which meant the
 * group action still merged it.
 */

const mockRoute = {
    params: {
        groupId: 'group-a'
    },
    query: {}
}

const mockAssessStore = {
    getMultiSelect: true,
    getCurrentGroup: 'group-a',
    getNewsItems: { total_count: 0, items: [] },
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

vi.mock('vue-router', () => ({
    useRoute: () => mockRoute
}))

vi.mock('@/stores/assess', () => ({
    useAssessStore: () => mockAssessStore
}))

/** Stands in for both card layouts: only the compact one emits the event. */
const cardStub = {
    props: ['card', 'preselected'],
    template: '<div class="card-stub" @click="$emit(\'selection-change\', !preselected)" />',
    emits: ['selection-change']
}

const commonStubs = {
    CardAssess: cardStub,
    CardCompact: cardStub,
    NewsItemDetailDialog: true,
    ReportsListDialog: true,
    NewReportItem: true
}

const items = [
    { id: 1, title: 'One' },
    { id: 2, title: 'Two' }
]

describe('ContentDataAssess compact-mode selection', () => {
    beforeEach(() => {
        vi.clearAllMocks()
        mockAssessStore.loadNewsItemsByGroup.mockResolvedValue({
            data: { total_count: items.length, items }
        })
    })

    const mountAssess = (selection = []) =>
        mountWithPlugins(ContentDataAssess, {
            props: { analyze_selector: false, selection },
            global: { stubs: commonStubs }
        })

    it('selects the aggregate when a compact card is ticked', async () => {
        const wrapper = mountAssess()
        await flushPromises()

        await wrapper.findAll('.card-stub')[1].trigger('click')

        expect(mockAssessStore.select).toHaveBeenCalledWith({
            type: 'news_item_aggregate',
            id: 2,
            item: expect.objectContaining({ id: 2 })
        })
        expect(mockAssessStore.deselect).not.toHaveBeenCalled()
    })

    it('deselects the aggregate when an already selected compact card is unticked', async () => {
        const wrapper = mountAssess([{ id: 2 }])
        await flushPromises()

        await wrapper.findAll('.card-stub')[1].trigger('click')

        expect(mockAssessStore.deselect).toHaveBeenCalledWith({ type: 'news_item_aggregate', id: 2 })
        expect(mockAssessStore.select).not.toHaveBeenCalled()
    })
})
