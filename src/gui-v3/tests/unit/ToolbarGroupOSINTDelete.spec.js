import { describe, it, expect, beforeEach, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { mountWithPlugins } from '../helpers/mount-helpers'
import { useOSINTSourceStore } from '@/stores/osint_source'
import ToolbarGroup from '@/components/common/ToolbarGroup.vue'

/**
 * Bulk delete on the OSINT sources toolbar.
 *
 * The button sits beside import and export, which are always visible, so it is reachable with
 * nothing selected. That makes "disabled until something is selected" the thing that stops it
 * being a one-click way to delete nothing - or, if the guard were ever dropped in favour of
 * "everything", every source there is. It only ever emits: the confirmation belongs to the view,
 * because the toolbar cannot know how many rows the answer would destroy.
 */

vi.mock('vue-router', () => ({
    useRoute: () => ({ params: {}, path: '/config/collectors' }),
    useRouter: () => ({ push: vi.fn() })
}))

vi.mock('@/composables/useAuth', () => ({
    useAuth: () => ({ checkPermission: () => true })
}))

vi.mock('@/api/assess', () => ({ selectAllNewsItems: vi.fn(), groupAction: vi.fn() }))
vi.mock('@/api/analyze', () => ({ getAllReportItemsUnpaginated: vi.fn(), deleteReportItem: vi.fn() }))
vi.mock('@/api/publish', () => ({ getAllProductsUnpaginated: vi.fn(), deleteProduct: vi.fn() }))

const deleteButton = (wrapper) => wrapper.findAll('button').find((button) => button.attributes('title') === 'Delete selected sources')

const mountToolbar = async () => {
    const wrapper = mountWithPlugins(ToolbarGroup, { props: { view: 'collectors.sources' } })
    await flushPromises()
    return { wrapper, store: useOSINTSourceStore() }
}

describe('ToolbarGroup bulk delete (collectors.sources)', () => {
    beforeEach(() => vi.clearAllMocks())

    it('offers the button beside import and export', async () => {
        const { wrapper } = await mountToolbar()
        expect(deleteButton(wrapper)).toBeDefined()
    })

    it('stays disabled while nothing is selected', async () => {
        const { wrapper } = await mountToolbar()
        expect(deleteButton(wrapper).attributes('disabled')).toBeDefined()
    })

    it('enables once a source is selected and then only emits', async () => {
        const { wrapper, store } = await mountToolbar()

        store.selection = [{ id: 'source-1', type: 'osint-source' }]
        await flushPromises()

        expect(deleteButton(wrapper).attributes('disabled')).toBeUndefined()

        await deleteButton(wrapper).trigger('click')

        expect(wrapper.emitted('osint-delete')).toHaveLength(1)
    })

    it('is not offered on the other views that share this toolbar', async () => {
        const wrapper = mountWithPlugins(ToolbarGroup, { props: { view: 'assess' } })
        await flushPromises()
        expect(deleteButton(wrapper)).toBeUndefined()
    })
})
