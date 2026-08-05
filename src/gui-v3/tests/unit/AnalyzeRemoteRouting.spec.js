import { describe, it, expect, beforeEach, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { mountWithPlugins } from '../helpers/mount-helpers'
import ContentDataAnalyze from '@/components/analyze/ContentDataAnalyze.vue'

const mockRoute = { params: { scope: 'group-upstream-node' } }
const mockStore = {
    getMultiSelectReport: false,
    getCurrentReportItemGroup: '',
    getReportItems: { total_count: 0, items: [] },
    getReportItemTypes: { items: [] },
    loadReportItems: vi.fn(),
    loadReportItemTypes: vi.fn(),
    selectReport: vi.fn(),
    deselectReport: vi.fn()
}

vi.mock('vue-router', () => ({ useRoute: () => mockRoute }))
vi.mock('@/stores/analyze', () => ({ useAnalyzeStore: () => mockStore }))

const CardAnalyzeStub = {
    name: 'CardAnalyze',
    props: ['card'],
    template: '<button class="report-card-stub" />'
}

describe('Analyze remote report routing', () => {
    beforeEach(() => {
        vi.clearAllMocks()
        mockStore.getReportItems = {
            total_count: 1,
            items: [{ id: 7, title: 'Remote report', report_item_type_id: 2, remote_user: 'upstream node', access: true }]
        }
        mockStore.getReportItemTypes = { items: [{ id: 2, title: 'Advisory' }] }
        mockStore.loadReportItems.mockResolvedValue({ data: mockStore.getReportItems })
        mockStore.loadReportItemTypes.mockResolvedValue({ data: mockStore.getReportItemTypes })
    })

    it('emits the dedicated read-only viewer event for synchronized reports', async () => {
        const wrapper = mountWithPlugins(ContentDataAnalyze, {
            global: { stubs: { CardAnalyze: CardAnalyzeStub, CardCompact: CardAnalyzeStub, TransitionGroup: false } }
        })
        await flushPromises()

        wrapper.findComponent(CardAnalyzeStub).vm.$emit('show-detail', mockStore.getReportItems.items[0])

        expect(wrapper.emitted('show-remote-report-item-detail')?.[0]?.[0]).toMatchObject({ id: 7 })
        expect(wrapper.emitted('show-report-item-detail')).toBeUndefined()
        expect(mockStore.loadReportItems).toHaveBeenCalledWith(expect.objectContaining({ group: 'upstream node' }))
    })
})
