import { describe, it, expect, beforeEach, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { mountWithPlugins } from '../helpers/mount-helpers'
import ContentDataAnalyze from '@/components/analyze/ContentDataAnalyze.vue'
import AnalyzeView from '@/views/users/AnalyzeView.vue'

const mockRoute = { params: { scope: 'group-upstream node' } }
const mockStore = {
    getMultiSelectReport: false,
    getCurrentReportItemGroup: '',
    getReportItems: { total_count: 0, items: [] },
    getReportItemTypes: { items: [] },
    loadReportItems: vi.fn(),
    loadReportItemTypes: vi.fn(),
    selectReport: vi.fn(),
    deselectReport: vi.fn(),
    multiSelectReport: vi.fn()
}

vi.mock('vue-router', () => ({ useRoute: () => mockRoute, onBeforeRouteLeave: vi.fn() }))
vi.mock('@/stores/analyze', () => ({ useAnalyzeStore: () => mockStore }))
vi.mock('@/composables/useAuth', () => ({ useAuth: () => ({ checkPermission: () => true }) }))

const CardAnalyzeStub = {
    name: 'CardAnalyze',
    props: ['card'],
    template: '<button class="report-card-stub" />'
}

const ToolbarStub = {
    name: 'ToolbarFilterAnalyze',
    props: ['showAddButton', 'multiSelect'],
    template: '<div />'
}

const ContentStub = {
    name: 'ContentDataAnalyze',
    props: ['disableActions'],
    template: '<div />'
}

describe('Analyze remote report routing', () => {
    beforeEach(() => {
        vi.clearAllMocks()
        mockRoute.params.scope = 'group-upstream node'
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

    it('hides local creation actions throughout a remote scope', () => {
        const wrapper = mountWithPlugins(AnalyzeView, {
            global: {
                stubs: {
                    ViewLayout: { template: '<div><slot name="panel"/><slot name="content"/></div>' },
                    ToolbarFilterAnalyze: ToolbarStub,
                    ContentDataAnalyze: ContentStub,
                    NewReportItem: true,
                    RemoteReportItem: true
                }
            }
        })

        expect(wrapper.findComponent(ToolbarStub).props('showAddButton')).toBe(false)
        expect(wrapper.findComponent(ContentStub).props('disableActions')).toBe(true)
    })

    it('retains local creation actions in the local scope', () => {
        mockRoute.params.scope = 'local'

        const wrapper = mountWithPlugins(AnalyzeView, {
            global: {
                stubs: {
                    ViewLayout: { template: '<div><slot name="panel"/><slot name="content"/></div>' },
                    ToolbarFilterAnalyze: ToolbarStub,
                    ContentDataAnalyze: ContentStub,
                    NewReportItem: true,
                    RemoteReportItem: true
                }
            }
        })

        expect(wrapper.findComponent(ToolbarStub).props('showAddButton')).toBe(true)
        expect(wrapper.findComponent(ContentStub).props('disableActions')).toBe(false)
    })
})
