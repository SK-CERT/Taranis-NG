import { describe, it, expect, beforeEach, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { mountWithPlugins } from '../helpers/mount-helpers'
import { useAssessStore } from '@/stores/assess'
import { useAnalyzeStore } from '@/stores/analyze'
import { usePublishStore } from '@/stores/publish'
import ToolbarGroup from '@/components/common/ToolbarGroup.vue'
import { Action } from '@/types/actions'

/**
 * "Select all" fetches the current group's whole filtered list. It has to replace the selection
 * rather than add to it: an item already selected by hand would end up in it twice, and
 * unchecking it would drop only one of the two copies - so it would still be grouped.
 */

vi.mock('vue-router', () => ({
    useRoute: () => ({ params: { groupId: 'group-a' }, path: '/assess/group/group-a' }),
    useRouter: () => ({ push: vi.fn() })
}))

vi.mock('@/composables/useAuth', () => ({
    useAuth: () => ({ checkPermission: () => true })
}))

vi.mock('@/api/assess', () => ({
    selectAllNewsItems: vi.fn(),
    groupAction: vi.fn()
}))

vi.mock('@/api/analyze', () => ({
    getAllReportItemsUnpaginated: vi.fn(),
    deleteReportItem: vi.fn()
}))

vi.mock('@/api/publish', () => ({
    getAllProductsUnpaginated: vi.fn(),
    deleteProduct: vi.fn()
}))

const selectAllButton = (wrapper) =>
    wrapper.findAll('button').find((button) => ['Select All', 'Unselect All'].includes(button.attributes('title')))

const collectNotifications = () => {
    const notifications = []
    const listener = (event) => notifications.push(event.detail)
    window.addEventListener('notification', listener)
    return {
        notifications,
        stop: () => window.removeEventListener('notification', listener)
    }
}

describe('ToolbarGroup select all (assess)', () => {
    let assessApi

    beforeEach(async () => {
        vi.clearAllMocks()
        assessApi = await import('@/api/assess')
    })

    // The action buttons only render once multi-select is on.
    const mountToolbar = async () => {
        const wrapper = mountWithPlugins(ToolbarGroup, { props: { view: 'assess' } })
        const store = useAssessStore()
        store.multiSelect(true)
        await flushPromises()
        return { wrapper, store }
    }

    it('replaces an existing selection instead of adding to it', async () => {
        vi.mocked(assessApi.selectAllNewsItems).mockResolvedValue({
            data: { items: [{ id: 1 }, { id: 2 }] }
        })

        const { wrapper, store } = await mountToolbar()

        // Selected by hand first, the way a user would before reaching for "select all".
        store.select({ type: 'news_item_aggregate', id: 1, item: { id: 1 } })
        await wrapper.vm.$nextTick()

        await selectAllButton(wrapper).trigger('click')
        await flushPromises()

        expect(store.getSelection.map((item) => item.id)).toEqual([1, 2])

        // A single uncheck has to leave nothing behind for the group action to pick up.
        store.deselect({ type: 'news_item_aggregate', id: 1 })
        expect(store.getSelection.map((item) => item.id)).toEqual([2])
    })

    it('marks count-bearing notifications for plural selection', async () => {
        vi.mocked(assessApi.selectAllNewsItems).mockResolvedValue({
            data: { items: [{ id: 1 }, { id: 2 }] }
        })
        const notifications = []
        const collectNotification = (event) => notifications.push(event.detail)
        window.addEventListener('notification', collectNotification)

        try {
            const { wrapper } = await mountToolbar()
            await selectAllButton(wrapper).trigger('click')
            await flushPromises()

            expect(notifications).toContainEqual(
                expect.objectContaining({
                    loc: 'assess.select_all_success',
                    params: { count: '2' },
                    pluralCount: 2
                })
            )
        } finally {
            window.removeEventListener('notification', collectNotification)
        }
    })

    it('offers "select all" again once the selection is cleared from elsewhere', async () => {
        vi.mocked(assessApi.selectAllNewsItems).mockResolvedValue({
            data: { items: [{ id: 1 }, { id: 2 }] }
        })

        const { wrapper, store } = await mountToolbar()

        await selectAllButton(wrapper).trigger('click')
        await flushPromises()
        expect(selectAllButton(wrapper).attributes('title')).toBe('Unselect All')

        // What a group tab switch does.
        store.clearSelection()
        await flushPromises()

        expect(selectAllButton(wrapper).attributes('title')).toBe('Select All')
    })
})

describe('ToolbarGroup notification contracts', () => {
    beforeEach(() => {
        vi.clearAllMocks()
    })

    it('marks analyze and publish select-all counts for plural selection', async () => {
        const analyzeApi = await import('@/api/analyze')
        const publishApi = await import('@/api/publish')
        vi.mocked(analyzeApi.getAllReportItemsUnpaginated).mockResolvedValue({ data: { items: [{ id: 1 }, { id: 2 }] } })
        vi.mocked(publishApi.getAllProductsUnpaginated).mockResolvedValue({ data: { items: [{ id: 3 }, { id: 4 }, { id: 5 }] } })
        const { notifications, stop } = collectNotifications()

        try {
            const analyzeWrapper = mountWithPlugins(ToolbarGroup, { props: { view: 'analyze' } })
            useAnalyzeStore().multiSelectReport(true)
            await flushPromises()
            await selectAllButton(analyzeWrapper).trigger('click')
            await flushPromises()
            analyzeWrapper.unmount()

            const publishWrapper = mountWithPlugins(ToolbarGroup, { props: { view: 'publish' } })
            usePublishStore().multiSelect(true)
            await flushPromises()
            await selectAllButton(publishWrapper).trigger('click')
            await flushPromises()
            publishWrapper.unmount()

            expect(notifications).toContainEqual(
                expect.objectContaining({ loc: 'analyze.select_all_success', params: { count: '2' }, pluralCount: 2 })
            )
            expect(notifications).toContainEqual(
                expect.objectContaining({ loc: 'publish.select_all_success', params: { count: '3' }, pluralCount: 3 })
            )
        } finally {
            stop()
        }
    })

    it('preserves assess grouping guards and the plural processing contract', async () => {
        const assessApi = await import('@/api/assess')
        vi.mocked(assessApi.groupAction).mockResolvedValue({ data: {} })
        const { notifications, stop } = collectNotifications()

        try {
            const wrapper = mountWithPlugins(ToolbarGroup, { props: { view: 'assess' } })
            const store = useAssessStore()

            store.select({ type: 'AGGREGATE', id: 1, item: { id: 1, news_items: [{}] } })
            await wrapper.vm.handleAction(Action.GROUP)
            await wrapper.vm.handleAction(Action.UNGROUP)

            store.select({ type: 'AGGREGATE', id: 2, item: { id: 2 } })
            await wrapper.vm.handleAction(Action.GROUP)
            await flushPromises()

            expect(notifications).toContainEqual(expect.objectContaining({ loc: 'common.select_at_least_two_to_group' }))
            expect(notifications).toContainEqual(expect.objectContaining({ loc: 'common.no_grouped_items_selected' }))
            expect(notifications).toContainEqual(
                expect.objectContaining({
                    id: 'assess-action-progress',
                    loc: 'common.processing_items',
                    params: { count: '2' },
                    pluralCount: 2,
                    timeout: 0
                })
            )
            expect(assessApi.groupAction).toHaveBeenCalledOnce()
            wrapper.unmount()
        } finally {
            stop()
        }
    })

    it.each([
        ['analyze', 'analyze-delete-progress'],
        ['publish', 'publish-delete-progress']
    ])('marks %s deletion counts for plural selection', async (view, progressId) => {
        const analyzeApi = await import('@/api/analyze')
        const publishApi = await import('@/api/publish')
        vi.mocked(analyzeApi.deleteReportItem).mockResolvedValue({ data: {} })
        vi.mocked(publishApi.deleteProduct).mockResolvedValue({ data: {} })
        const { notifications, stop } = collectNotifications()

        try {
            const wrapper = mountWithPlugins(ToolbarGroup, { props: { view } })
            if (view === 'analyze') {
                useAnalyzeStore().selectReport({ id: 7, item: { id: 7 } })
            } else {
                usePublishStore().select({ id: 7, item: { id: 7 } })
            }

            await wrapper.vm.handleDelete()
            await flushPromises()

            expect(notifications).toContainEqual(
                expect.objectContaining({
                    id: progressId,
                    loc: 'common.deleting_items',
                    params: { count: '1' },
                    pluralCount: 1,
                    timeout: 0
                })
            )
            expect(notifications).toContainEqual(
                expect.objectContaining({ id: progressId, loc: 'common.deleted_successfully', timeout: 2000 })
            )
            wrapper.unmount()
        } finally {
            stop()
        }
    })
})

describe('ToolbarGroup select all availability', () => {
    /**
     * The button keeps its place in the toolbar at all times so the row does not change shape when
     * selection mode goes on, but it stays inactive until then - the same way export and delete
     * stay inactive until there is a selection. Selecting everything while the per-row checkboxes
     * were still hidden would leave a count nobody can inspect or narrow down.
     */
    it('is present but inactive before selection mode is turned on', async () => {
        const wrapper = mountWithPlugins(ToolbarGroup, { props: { view: 'assess' } })
        await flushPromises()

        expect(useAssessStore().getMultiSelect).toBe(false)

        const button = selectAllButton(wrapper)
        expect(button).toBeDefined()
        expect(button.attributes('disabled')).toBeDefined()
    })

    it('becomes usable once selection mode is on', async () => {
        const assessApi = await import('@/api/assess')
        vi.mocked(assessApi.selectAllNewsItems).mockResolvedValue({ data: { items: [{ id: 1 }] } })

        const wrapper = mountWithPlugins(ToolbarGroup, { props: { view: 'assess' } })
        const store = useAssessStore()
        store.multiSelect(true)
        await flushPromises()

        expect(selectAllButton(wrapper).attributes('disabled')).toBeUndefined()

        await selectAllButton(wrapper).trigger('click')
        await flushPromises()

        expect(store.getSelection.map((item) => item.id)).toEqual([1])
    })
})
