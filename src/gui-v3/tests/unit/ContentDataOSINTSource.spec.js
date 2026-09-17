import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { mountWithPlugins } from '../helpers/mount-helpers'
import { useConfigStore } from '@/stores/config'
import AuthService from '@/services/auth_service'
import OSINTSourcesView from '@/views/admin/OSINTSourcesView.vue'
import { useOSINTSourceStore } from '@/stores/osint_source'

const { importOSINTSources, exportOSINTSources, getAllOSINTSources, getAllCollectorsNodes, deleteOSINTSource } = vi.hoisted(() => ({
    importOSINTSources: vi.fn(),
    exportOSINTSources: vi.fn(),
    getAllOSINTSources: vi.fn(),
    getAllCollectorsNodes: vi.fn(),
    deleteOSINTSource: vi.fn()
}))

vi.mock('@/api/config', async (importOriginal) => ({
    ...(await importOriginal()),
    importOSINTSources,
    exportOSINTSources,
    getAllOSINTSources,
    getAllCollectorsNodes,
    deleteOSINTSource
}))

vi.mock('@/services/auth_service', () => ({
    default: {
        hasPermission: vi.fn((permission) => permission === 'CONFIG_OSINT_SOURCE_CREATE' || permission === 'CONFIG_OSINT_SOURCE_ACCESS')
    }
}))

const ToolbarFilterStub = {
    name: 'ToolbarFilter',
    props: ['selectedCount', 'showSelectedCount'],
    template:
        '<div class="selected-count"><slot name="prepend" />{{ showSelectedCount ? selectedCount : 0 }} OSINT sources selected<slot name="addbutton" /></div>'
}

const ToolbarGroupStub = {
    name: 'ToolbarGroup',
    emits: ['osint-import', 'osint-export', 'osint-delete', 'select-all'],
    setup() {
        const osintSourceStore = useOSINTSourceStore()
        return {
            canImport: AuthService.hasPermission('CONFIG_OSINT_SOURCE_CREATE'),
            canExport: AuthService.hasPermission('CONFIG_OSINT_SOURCE_ACCESS'),
            toggleSelection: () => osintSourceStore.multiSelectOSINTSource(true)
        }
    },
    template: `
        <div class="toolbar-group-test">
            <button data-action="toggle-selection" @click="toggleSelection">Toggle selection</button>
            <button v-if="canImport" data-action="import" @click="$emit('osint-import')">Import</button>
            <button v-if="canExport" data-action="export" @click="$emit('osint-export')">Export</button>
            <button data-action="select-all" @click="$emit('select-all')">Select all</button>
            <button data-action="delete" @click="$emit('osint-delete')">Delete selected</button>
        </div>
    `
}

// Standing in for the real dialog so a test can answer it; what is under test is what the view
// does with the answer, not how the dialog asks.
const ConfirmationDialogStub = {
    name: 'ConfirmationDialog',
    props: ['modelValue', 'message'],
    emits: ['confirm'],
    template:
        '<div v-if="modelValue" class="confirm-delete"><span class="confirm-message">{{ message }}</span><button class="confirm-yes" @click="$emit(\'confirm\')">Yes</button></div>'
}

const ContentDataOSINTSourceStub = {
    name: 'ContentDataOSINTSource',
    emits: ['selection-change'],
    template: `
        <div class="source-list-test">
            <button data-action="select-source-1" @click="$emit('selection-change', 'source-1', true)">source 1</button>
            <button data-action="select-source-3" @click="$emit('selection-change', 'source-3', true)">source 3</button>
        </div>
    `
}

const VDialogStub = {
    name: 'VDialog',
    props: ['modelValue'],
    template: '<div v-if="modelValue"><slot /></div>'
}

const VFormStub = {
    name: 'VForm',
    methods: {
        validate: vi.fn().mockResolvedValue({ valid: true }),
        resetValidation: vi.fn()
    },
    template: '<form><slot /></form>'
}

const VSelectStub = {
    name: 'VSelect',
    emits: ['update:modelValue'],
    template: '<button class="choose-node" @click.prevent="$emit(\'update:modelValue\', \'node-7\')">node</button>'
}

const VFileInputStub = {
    name: 'VFileInput',
    emits: ['update:modelValue'],
    template: '<button class="choose-file" @click.prevent="$emit(\'update:modelValue\', testFile)">file</button>',
    data: () => ({ testFile: new File(['{}'], 'sources.json', { type: 'application/json' }) })
}

const mountScreen = (
    items = [
        { id: 'source-1', name: 'Source 1' },
        { id: 'source-3', name: 'Source 3' }
    ]
) => {
    getAllOSINTSources.mockResolvedValue({ data: { total_count: items.length, items } })
    getAllCollectorsNodes.mockResolvedValue({ data: { total_count: 1, items: [{ id: 'node-7', name: 'Node 7' }] } })

    return mountWithPlugins(OSINTSourcesView, {
        global: {
            stubs: {
                ToolbarFilter: ToolbarFilterStub,
                ToolbarGroup: ToolbarGroupStub,
                NewOSINTSource: true,
                ContentDataOSINTSource: ContentDataOSINTSourceStub,
                VDialog: VDialogStub,
                VForm: VFormStub,
                VSelect: VSelectStub,
                VFileInput: VFileInputStub,
                ConfirmationDialog: ConfirmationDialogStub
            }
        }
    })
}

describe('OSINT source bulk actions on OSINTSourcesView', () => {
    beforeEach(() => {
        vi.clearAllMocks()
        AuthService.hasPermission.mockImplementation(
            (permission) => permission === 'CONFIG_OSINT_SOURCE_CREATE' || permission === 'CONFIG_OSINT_SOURCE_ACCESS'
        )
        importOSINTSources.mockResolvedValue({})
        deleteOSINTSource.mockResolvedValue({})
        exportOSINTSources.mockResolvedValue({
            data: new Blob(['{}'], { type: 'application/json' }),
            headers: { 'content-disposition': 'attachment; filename="sources.json"' }
        })
        vi.spyOn(window.URL, 'createObjectURL').mockReturnValue('blob:test')
        vi.spyOn(window.URL, 'revokeObjectURL').mockImplementation(() => {})
        vi.spyOn(window.HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
    })

    it('does not render operations without their permissions', async () => {
        AuthService.hasPermission.mockReturnValue(false)
        const wrapper = mountScreen()
        await flushPromises()

        expect(wrapper.find('[data-action="import"]').exists()).toBe(false)
        expect(wrapper.find('[data-action="export"]').exists()).toBe(false)
    })

    it('exports all sources when the selection is empty', async () => {
        const wrapper = mountScreen()
        await flushPromises()

        await wrapper.find('[data-action="export"]').trigger('click')
        await flushPromises()

        expect(exportOSINTSources).toHaveBeenCalledWith({})
        expect(window.HTMLAnchorElement.prototype.click).toHaveBeenCalledOnce()
    })

    it('exports only the selected source IDs when a selection exists', async () => {
        const wrapper = mountScreen()
        await flushPromises()
        await wrapper.find('[data-action="select-source-1"]').trigger('click')
        await wrapper.find('[data-action="select-source-3"]').trigger('click')

        await wrapper.find('[data-action="export"]').trigger('click')
        await flushPromises()

        expect(exportOSINTSources).toHaveBeenCalledWith({ selection: ['source-1', 'source-3'] })
    })

    it('plural-selects and locale-formats the selected source count', async () => {
        const items = Array.from({ length: 13 }, (_, index) => ({ id: `source-${index}` }))
        const wrapper = mountScreen(items)
        await flushPromises()
        await wrapper.find('[data-action="toggle-selection"]').trigger('click')
        await wrapper.find('[data-action="select-all"]').trigger('click')
        await wrapper.vm.$nextTick()

        expect(wrapper.find('.selected-count').text()).toContain('13 OSINT sources selected')
        expect(useConfigStore().osintSources.items).toHaveLength(13)
        expect(useOSINTSourceStore().selection).toHaveLength(13)
    })

    it('isolates server-provided collector node names', () => {
        const wrapper = mountScreen()

        expect(wrapper.vm.nodeTitle({ id: 'node-7', name: 'Node العربية' })).toBe('\u2068Node العربية\u2069')
    })

    it('reports a direct export request failure without triggering a download', async () => {
        exportOSINTSources.mockRejectedValue(new Error('failed'))
        const notifications = []
        const handler = (event) => notifications.push(event.detail)
        window.addEventListener('notification', handler)
        const wrapper = mountScreen()
        await flushPromises()

        await wrapper.find('[data-action="export"]').trigger('click')
        await flushPromises()
        window.removeEventListener('notification', handler)

        expect(window.HTMLAnchorElement.prototype.click).not.toHaveBeenCalled()
        expect(notifications.at(-1)).toMatchObject({ type: 'error', loc: 'collectors.sources.export_error' })
    })

    it('imports the JSON file into the selected collector node and refreshes the source list', async () => {
        const wrapper = mountScreen()
        await flushPromises()
        const initialLoads = getAllOSINTSources.mock.calls.length

        await wrapper.find('[data-action="import"]').trigger('click')
        await wrapper.find('.choose-node').trigger('click')
        await wrapper.find('.choose-file').trigger('click')
        await wrapper
            .findAll('button')
            .filter((button) => button.text() === 'Import')
            .at(-1)
            .trigger('click')
        await flushPromises()

        expect(importOSINTSources).toHaveBeenCalledOnce()
        const body = importOSINTSources.mock.calls[0][0]
        expect(body).toBeInstanceOf(FormData)
        expect(body.get('collectors_node_id')).toBe('node-7')
        expect(body.get('file')).toBeInstanceOf(File)
        expect(getAllOSINTSources).toHaveBeenCalledTimes(initialLoads + 1)
    })

    it('reports import failures without refreshing the source list', async () => {
        importOSINTSources.mockRejectedValue(new Error('failed'))
        const notifications = []
        const handler = (event) => notifications.push(event.detail)
        window.addEventListener('notification', handler)
        const wrapper = mountScreen()
        await flushPromises()
        const initialLoads = getAllOSINTSources.mock.calls.length

        await wrapper.find('[data-action="import"]').trigger('click')
        await wrapper.find('.choose-node').trigger('click')
        await wrapper.find('.choose-file').trigger('click')
        await wrapper
            .findAll('button')
            .filter((button) => button.text() === 'Import')
            .at(-1)
            .trigger('click')
        await flushPromises()
        window.removeEventListener('notification', handler)

        expect(notifications.at(-1)).toMatchObject({ type: 'error', loc: 'collectors.sources.import_error' })
        expect(getAllOSINTSources).toHaveBeenCalledTimes(initialLoads)
    })

    describe('bulk delete', () => {
        /**
         * Deleting a selection is the one bulk action that cannot be undone, so it asks first and
         * deletes only what was actually selected. The deletes run one at a time because each one
         * has the owning collector node rebuild its schedule.
         */
        const selectTwoAndDelete = async (wrapper) => {
            await wrapper.find('[data-action="select-source-1"]').trigger('click')
            await wrapper.find('[data-action="select-source-3"]').trigger('click')
            await wrapper.find('[data-action="delete"]').trigger('click')
            await flushPromises()
        }

        it('asks before deleting anything', async () => {
            const wrapper = await mountScreen()
            await flushPromises()

            await selectTwoAndDelete(wrapper)

            expect(wrapper.find('.confirm-delete').exists()).toBe(true)
            expect(deleteOSINTSource).not.toHaveBeenCalled()
        })

        it('deletes exactly the selected sources once confirmed, then reloads', async () => {
            const wrapper = await mountScreen()
            await flushPromises()
            getAllOSINTSources.mockClear()

            await selectTwoAndDelete(wrapper)
            await wrapper.find('.confirm-yes').trigger('click')
            await flushPromises()

            expect(deleteOSINTSource).toHaveBeenCalledTimes(2)
            expect(deleteOSINTSource.mock.calls.map(([source]) => source.id)).toEqual(['source-1', 'source-3'])
            expect(getAllOSINTSources).toHaveBeenCalled()
            expect(useOSINTSourceStore().getOSINTSourcesSelection).toEqual([])
        })

        it('does not open the dialog when nothing is selected', async () => {
            const wrapper = await mountScreen()
            await flushPromises()

            await wrapper.find('[data-action="delete"]').trigger('click')
            await flushPromises()

            expect(wrapper.find('.confirm-delete').exists()).toBe(false)
            expect(deleteOSINTSource).not.toHaveBeenCalled()
        })

        it('deletes the rest even when one source fails, and says so', async () => {
            // The others were asked for just as explicitly; abandoning them would leave the
            // operator to work out which half of their selection survived.
            deleteOSINTSource.mockRejectedValueOnce(new Error('gone wrong'))
            const notifications = []
            const listener = (event) => notifications.push(event.detail)
            window.addEventListener('notification', listener)

            try {
                const wrapper = await mountScreen()
                await flushPromises()

                await selectTwoAndDelete(wrapper)
                await wrapper.find('.confirm-yes').trigger('click')
                await flushPromises()

                expect(deleteOSINTSource).toHaveBeenCalledTimes(2)
                expect(notifications).toContainEqual(
                    expect.objectContaining({ type: 'error', loc: 'collectors.sources.delete_selected_error' })
                )
            } finally {
                window.removeEventListener('notification', listener)
            }
        })
    })
})
