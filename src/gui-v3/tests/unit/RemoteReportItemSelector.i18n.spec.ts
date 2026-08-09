/* eslint-disable vue/one-component-per-file -- focused harness uses small inline child stubs */
import { defineComponent, h } from 'vue'
import { flushPromises } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mountWithPlugins } from '../helpers/mount-helpers'
import RemoteReportItemSelector from '@/components/analyze/RemoteReportItemSelector.vue'

const { analyzeStore, contentUpdateData, contentUpdateFilter, getReportItemData, updateReportItem } = vi.hoisted(() => ({
    analyzeStore: {
        getReportItemGroups: ['مجموعة بعيدة', 'Remote node'],
        getCurrentReportItemGroup: null as string | null,
        getSelectionReport: [] as unknown[],
        loadReportItemGroups: vi.fn().mockResolvedValue(undefined),
        changeCurrentReportItemGroup: vi.fn().mockResolvedValue(undefined),
        multiSelectReport: vi.fn()
    },
    contentUpdateData: vi.fn(),
    contentUpdateFilter: vi.fn(),
    getReportItemData: vi.fn(),
    updateReportItem: vi.fn().mockResolvedValue(undefined)
}))

vi.mock('@/stores/analyze', () => ({ useAnalyzeStore: () => analyzeStore }))
vi.mock('@/composables/useAuth', () => ({
    useAuth: () => ({ checkPermission: () => true, getUserId: () => 99 })
}))
vi.mock('@/api/analyze', () => ({ getReportItemData, updateReportItem }))

const ContentDataStub = defineComponent({
    name: 'ContentDataAnalyze',
    setup(_, { expose }) {
        expose({ updateData: contentUpdateData, updateFilter: contentUpdateFilter })
        return () => null
    }
})

const ToolbarStub = defineComponent({
    name: 'ToolbarFilterAnalyze',
    emits: ['update-filter'],
    setup(_, { emit, expose }) {
        expose({ updateDataCount: vi.fn() })
        return () => h('button', { class: 'emit-filter', onClick: () => emit('update-filter', { query: 'needle' }) }, 'filter')
    }
})

const CardAnalyzeStub = defineComponent({
    name: 'CardAnalyze',
    props: { card: { type: Object, required: true } },
    template: '<div class="selected-card">{{ card.id }}</div>'
})

const passthroughStub = (name: string) => defineComponent({ name, template: '<div><slot /></div>' })

const mountSelector = () =>
    mountWithPlugins(RemoteReportItemSelector, {
        props: {
            values: [{ id: 'remote-existing', title: 'Existing' }],
            edit: true,
            modify: true,
            reportItemId: 10
        },
        global: {
            stubs: {
                VContainer: passthroughStub('VContainer'),
                VDialog: passthroughStub('VDialog'),
                VCard: passthroughStub('VCard'),
                VToolbar: passthroughStub('VToolbar'),
                VToolbarTitle: passthroughStub('VToolbarTitle'),
                VRow: passthroughStub('VRow'),
                VCol: passthroughStub('VCol'),
                VList: passthroughStub('VList'),
                VListItem: passthroughStub('VListItem'),
                VSpacer: true,
                ContentDataAnalyze: ContentDataStub,
                ToolbarFilterAnalyze: ToolbarStub,
                CardAnalyze: CardAnalyzeStub,
                RemoteReportItem: true
            }
        }
    })

describe('RemoteReportItemSelector logical and bidi rendering', () => {
    beforeEach(() => {
        vi.clearAllMocks()
        analyzeStore.getReportItemGroups = ['مجموعة بعيدة', 'Remote node']
        analyzeStore.getCurrentReportItemGroup = null
        analyzeStore.getSelectionReport = []
        analyzeStore.loadReportItemGroups.mockResolvedValue(undefined)
        analyzeStore.changeCurrentReportItemGroup.mockResolvedValue(undefined)
        updateReportItem.mockResolvedValue(undefined)
    })

    it('uses logical layout, isolates group names, and preserves filter/group selection', async () => {
        const wrapper = mountSelector()
        await flushPromises()

        expect(wrapper.find('.selected-items-container').classes()).toContain('ms-4')
        expect(wrapper.find('.selected-items-container').classes()).not.toContain('ml-4')
        expect(wrapper.find('[style*="border-inline-end"]').exists()).toBe(true)
        expect(wrapper.find('[style*="border-right"]').exists()).toBe(false)
        expect(wrapper.findAll('bdi[dir="auto"]').map((node) => node.text())).toEqual(['مجموعة بعيدة', 'Remote node'])

        await wrapper.get('.emit-filter').trigger('click')
        expect(contentUpdateFilter).toHaveBeenCalledWith({ query: 'needle' })

        const groupLinks = wrapper.findAllComponents({ name: 'VListItem' })
        await groupLinks[1]!.trigger('click')
        expect(analyzeStore.changeCurrentReportItemGroup).toHaveBeenLastCalledWith('Remote node')
        expect(contentUpdateData).toHaveBeenCalledWith(false, false)
        wrapper.unmount()
    })

    it('preserves selection update and remote SSE fetch/event contracts', async () => {
        analyzeStore.getSelectionReport = [
            { item: { id: 'remote-existing' } },
            { item: { id: 'remote-new', title: 'Remote new' } },
            { item: { title: 'malformed' } }
        ]
        const wrapper = mountSelector()
        await flushPromises()

        const buttons = wrapper.findAllComponents({ name: 'VBtn' })
        await buttons[0]!.trigger('click')
        const addButton = wrapper.findAllComponents({ name: 'VBtn' }).find((button) => button.text() === 'Add')
        if (!addButton) throw new Error('Add button was not rendered')
        await addButton.trigger('click')
        await flushPromises()

        expect(updateReportItem).toHaveBeenCalledWith(10, {
            add: true,
            report_item_id: 10,
            remote_report_item_ids: ['remote-new']
        })
        expect(wrapper.emitted('remote-report-items-changed')?.at(-1)).toEqual([null])
        expect(analyzeStore.multiSelectReport).toHaveBeenNthCalledWith(1, true)
        expect(analyzeStore.multiSelectReport).toHaveBeenLastCalledWith(false)

        getReportItemData.mockResolvedValueOnce({ data: { remote_report_items: [{ id: 'remote-sse' }] } })
        window.dispatchEvent(
            new CustomEvent('report-item-updated', {
                detail: { add: true, report_item_id: 10, user_id: 7 }
            })
        )
        await flushPromises()

        expect(getReportItemData).toHaveBeenCalledWith(10, { add: true, report_item_id: 10, user_id: 7 })
        await vi.waitFor(() =>
            expect(wrapper.findAll('.selected-card').map((card) => card.text())).toEqual(['remote-existing', 'remote-new', 'remote-sse'])
        )
        wrapper.unmount()
    })
})
