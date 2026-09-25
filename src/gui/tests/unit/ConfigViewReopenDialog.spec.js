import { describe, it, expect, vi, beforeEach } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { mountWithPlugins } from '../helpers/mount-helpers'

/**
 * Re-opening a config dialog on the SAME row must work.
 *
 * The dialog components watch their `editItem` prop and open on it. Vue only fires
 * that watcher when the reference changes, so a view whose handleEdit does a bare
 * `editItem.value = item` breaks the second open: after closing without saving (which
 * leaves the parent's editItem pointing at that same object) clicking the row again
 * assigns an identical reference, the watcher never fires, and nothing happens.
 *
 * Every view therefore has to null the ref and await nextTick before re-assigning.
 * These specs pin that for the config dialogs; ReportTypesView and
 * OSINTSourceGroupsView already carried the pattern and are covered by the same rule.
 */

vi.mock('@/composables/useAuth', () => ({
    useAuth: () => ({ checkPermission: () => true })
}))

const mockConfigStore = {
    productTypes: { items: [], total_count: 0 },
    publisherPresets: { items: [], total_count: 0 },
    botPresets: { items: [], total_count: 0 },
    osintSources: { items: [], total_count: 0 },
    collectorsNodes: { items: [], total_count: 0 },
    loadProductTypes: vi.fn().mockResolvedValue({}),
    loadPublisherPresets: vi.fn().mockResolvedValue({}),
    loadBotPresets: vi.fn().mockResolvedValue({}),
    loadOSINTSources: vi.fn().mockResolvedValue({}),
    loadCollectorsNodes: vi.fn().mockResolvedValue({})
}

vi.mock('@/stores/config', () => ({
    useConfigStore: () => mockConfigStore
}))

vi.mock('@/api/config', async () => {
    const actual = await vi.importActual('@/api/config')
    return {
        ...actual,
        deleteProductType: vi.fn().mockResolvedValue({}),
        deletePublisherPreset: vi.fn().mockResolvedValue({}),
        deleteBotPreset: vi.fn().mockResolvedValue({})
    }
})

// Stand-in for the real dialog: records every transition into "open", which is what
// the watcher inside the real component keys off.
function makeDialogStub(opens) {
    return {
        name: 'DialogStub',
        props: ['editItem'],
        template: '<div />',
        watch: {
            editItem: {
                immediate: true,
                handler(value) {
                    if (value && Object.keys(value).length > 0) opens.push(value)
                }
            }
        }
    }
}

const cases = [
    { name: 'ProductTypesView', path: '@/views/admin/ProductTypesView.vue', child: 'NewProductType' },
    { name: 'PublisherPresetsView', path: '@/views/admin/PublisherPresetsView.vue', child: 'NewPublisherPreset' },
    { name: 'BotPresetsView', path: '@/views/admin/BotPresetsView.vue', child: 'NewBotPreset' },
    { name: 'OSINTSourcesView', path: '@/views/admin/OSINTSourcesView.vue', child: 'NewOSINTSource' }
]

describe.each(cases)('$name — re-opening the dialog on the same row', ({ path, child }) => {
    beforeEach(() => {
        vi.clearAllMocks()
    })

    it('re-triggers the dialog when the same item is edited twice', async () => {
        const opens = []
        const View = (await import(/* @vite-ignore */ path)).default

        const wrapper = mountWithPlugins(View, {
            global: { stubs: { [child]: makeDialogStub(opens) } }
        })
        await flushPromises()

        const row = { id: 'row-1', title: 'Some row', name: 'Some row' }

        await wrapper.vm.handleEdit(row)
        await flushPromises()
        expect(opens).toHaveLength(1)

        // Closing without saving leaves the parent's editItem pointing at `row`.
        // Selecting the very same row again must still reopen the dialog.
        await wrapper.vm.handleEdit(row)
        await flushPromises()
        expect(opens).toHaveLength(2)
    })
})
