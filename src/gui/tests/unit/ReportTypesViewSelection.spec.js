import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { mountWithPlugins } from '../helpers/mount-helpers'
import { useConfigStore } from '@/stores/config'
import { useUserStore } from '@/stores/user'
import { useReportTypesStore } from '@/stores/report_types'
import ReportTypesView from '@/views/admin/ReportTypesView.vue'

vi.mock('@/api/config', () => ({
    getAllReportItemTypes: vi.fn().mockResolvedValue({ data: { total_count: 0, items: [] } }),
    deleteReportItemType: vi.fn(),
    exportReportTypes: vi.fn(),
    importReportTypes: vi.fn()
}))

vi.mock('vue-router', () => ({
    useRoute: () => ({ params: {}, path: '/config/reports/types' }),
    useRouter: () => ({ push: vi.fn() })
}))

vi.mock('@/components/common/ToolbarFilter.vue', () => ({
    default: {
        template: '<div><slot name="prepend" /></div>'
    }
}))

vi.mock('@/components/config/reports/NewReportType.vue', () => ({
    default: {
        template: '<div />'
    }
}))

describe('ReportTypesView selection mode', () => {
    beforeEach(() => {
        vi.clearAllMocks()
    })

    it('shows and hides per-card checkboxes when the toolbar toggle is pressed', async () => {
        const wrapper = mountWithPlugins(ReportTypesView, {
            global: {
                stubs: {
                    ContentData: {
                        template:
                            '<div><div v-for="item in items" :key="item.id" class="test-card" :data-multi="String(multiSelectActive)" /></div>',
                        props: { items: Array, multiSelectActive: Boolean, selectedIds: Array },
                        emits: ['selection-change']
                    }
                }
            }
        })
        // Seed the store only after mount - `mountWithPlugins` installs a fresh Pinia, so calling
        // useConfigStore() beforehand registers the store on an orphaned instance the component
        // never sees.
        await flushPromises()
        const configStore = useConfigStore()
        configStore.loadReportItemTypesConfig = vi.fn().mockImplementation(async () => {
            configStore.$patch((state) => {
                state.reportItemTypesConfig = {
                    total_count: 2,
                    items: [
                        { id: 1, title: 'First report', tag: 'mdi-file' },
                        { id: 2, title: 'Second report', tag: 'mdi-file' }
                    ]
                }
            })
        })
        await configStore.loadReportItemTypesConfig({})
        useUserStore().setUser({ permissions: ['CONFIG_REPORT_TYPE_ACCESS'] })

        const toolbarStore = useReportTypesStore()

        const toggle = () => wrapper.find('button[title="Toggle report type selection mode"]')
        expect(wrapper.html()).toContain('data-multi="false"')

        await toggle().trigger('click')
        await flushPromises()
        expect(toolbarStore.getReportTypesMultiSelect).toBe(true)
        expect(wrapper.html()).toContain('data-multi="true"')

        await toggle().trigger('click')
        await flushPromises()
        expect(toolbarStore.getReportTypesMultiSelect).toBe(false)
        expect(wrapper.html()).toContain('data-multi="false"')

        wrapper.unmount()
    })

    it('fills and empties the checkbox selection on toolbar select-all / clear-selection', async () => {
        const wrapper = mountWithPlugins(ReportTypesView, {
            global: {
                stubs: {
                    // Real ToolbarGroup so its `select-all`/`clear-selection` emits are exercised.
                    ContentData: {
                        template: '<div />',
                        props: ['items', 'multiSelectActive', 'selectedIds']
                    }
                }
            }
        })
        await flushPromises()
        const configStore = useConfigStore()
        configStore.reportItemTypesConfig = {
            total_count: 2,
            items: [
                { id: 1, title: 'First report', tag: 'mdi-file' },
                { id: 2, title: 'Second report', tag: 'mdi-file' }
            ]
        }
        useUserStore().setUser({ permissions: ['CONFIG_REPORT_TYPE_ACCESS'] })

        const store = useReportTypesStore()
        store.multiSelectReportType(true)
        await flushPromises()

        const toolbar = wrapper.findComponent({ name: 'ToolbarGroup' })
        toolbar.vm.$emit('select-all')
        await flushPromises()
        expect(store.getReportTypesSelection.map((item) => item.id)).toEqual([1, 2])

        toolbar.vm.$emit('clear-selection')
        await flushPromises()
        expect(store.getReportTypesSelection).toEqual([])
        // Clearing the selection must not drop the view out of selection mode.
        expect(store.getReportTypesMultiSelect).toBe(true)

        wrapper.unmount()
    })
})
