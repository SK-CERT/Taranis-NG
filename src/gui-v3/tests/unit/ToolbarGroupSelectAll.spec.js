import { describe, it, expect, beforeEach, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { mountWithPlugins } from '../helpers/mount-helpers'
import { useAssessStore } from '@/stores/assess'
import ToolbarGroup from '@/components/common/ToolbarGroup.vue'

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
