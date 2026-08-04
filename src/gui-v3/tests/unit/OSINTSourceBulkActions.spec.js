import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { mountWithPlugins } from '../helpers/mount-helpers'
import OSINTSourceBulkActions from '@/components/config/collectors/OSINTSourceBulkActions.vue'

const { importOSINTSources, exportOSINTSources } = vi.hoisted(() => ({
    importOSINTSources: vi.fn(),
    exportOSINTSources: vi.fn()
}))

vi.mock('@/api/config', () => ({
    importOSINTSources,
    exportOSINTSources
}))

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
    props: ['modelValue'],
    emits: ['update:modelValue'],
    template: '<button class="choose-node" @click.prevent="$emit(\'update:modelValue\', \'node-7\')">node</button>'
}

const VFileInputStub = {
    name: 'VFileInput',
    props: ['modelValue'],
    emits: ['update:modelValue'],
    template: '<button class="choose-file" @click.prevent="$emit(\'update:modelValue\', testFile)">file</button>',
    data: () => ({ testFile: new File(['{}'], 'sources.json', { type: 'application/json' }) })
}

const mountActions = (props = {}) =>
    mountWithPlugins(OSINTSourceBulkActions, {
        props: {
            canImport: true,
            canExport: true,
            nodes: [{ id: 'node-7', name: 'Node 7' }],
            selectedIds: [],
            sourceCount: 3,
            ...props
        },
        global: {
            stubs: {
                VDialog: VDialogStub,
                VForm: VFormStub,
                VSelect: VSelectStub,
                VFileInput: VFileInputStub
            }
        }
    })

const buttonWithText = (wrapper, text) => wrapper.findAllComponents({ name: 'VBtn' }).find((button) => button.text() === text)
const lastButtonWithText = (wrapper, text) =>
    wrapper
        .findAllComponents({ name: 'VBtn' })
        .filter((button) => button.text() === text)
        .at(-1)

describe('OSINT source bulk actions', () => {
    beforeEach(() => {
        vi.clearAllMocks()
        importOSINTSources.mockResolvedValue({})
        exportOSINTSources.mockResolvedValue({
            data: new Blob(['{}'], { type: 'application/json' }),
            headers: { 'content-disposition': 'attachment; filename="sources.json"' }
        })
        vi.spyOn(window.URL, 'createObjectURL').mockReturnValue('blob:test')
        vi.spyOn(window.URL, 'revokeObjectURL').mockImplementation(() => {})
        vi.spyOn(window.HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
    })

    it('does not render operations without their permissions', () => {
        const wrapper = mountActions({ canImport: false, canExport: false })

        expect(buttonWithText(wrapper, 'Import')).toBeUndefined()
        expect(buttonWithText(wrapper, 'Export')).toBeUndefined()
    })

    it('exports all sources when the selection is empty', async () => {
        const wrapper = mountActions()

        await buttonWithText(wrapper, 'Export').trigger('click')
        await flushPromises()

        expect(exportOSINTSources).toHaveBeenCalledWith({})
        expect(window.HTMLAnchorElement.prototype.click).toHaveBeenCalledOnce()
    })

    it('exports only the selected source IDs when a selection exists', async () => {
        const wrapper = mountActions({ selectedIds: ['source-1', 'source-3'] })

        await buttonWithText(wrapper, 'Export').trigger('click')
        await flushPromises()

        expect(exportOSINTSources).toHaveBeenCalledWith({ selection: ['source-1', 'source-3'] })
    })

    it('reports a direct export request failure without triggering a download', async () => {
        exportOSINTSources.mockRejectedValue(new Error('failed'))
        const notifications = []
        const handler = (event) => notifications.push(event.detail)
        window.addEventListener('notification', handler)
        const wrapper = mountActions()

        await buttonWithText(wrapper, 'Export').trigger('click')
        await flushPromises()
        window.removeEventListener('notification', handler)

        expect(window.HTMLAnchorElement.prototype.click).not.toHaveBeenCalled()
        expect(notifications.at(-1)).toMatchObject({ type: 'error', loc: 'collectors.sources.export_error' })
    })

    it('imports the JSON file into the selected collector node and requests a refresh', async () => {
        const wrapper = mountActions()

        await lastButtonWithText(wrapper, 'Import').trigger('click')
        await wrapper.find('.choose-node').trigger('click')
        await wrapper.find('.choose-file').trigger('click')
        await lastButtonWithText(wrapper, 'Import').trigger('click')
        await flushPromises()

        expect(importOSINTSources).toHaveBeenCalledOnce()
        const body = importOSINTSources.mock.calls[0][0]
        expect(body).toBeInstanceOf(FormData)
        expect(body.get('collectors_node_id')).toBe('node-7')
        expect(body.get('file')).toBeInstanceOf(File)
        expect(wrapper.emitted('import-complete')).toHaveLength(1)
        expect(wrapper.emitted('load-nodes')).toHaveLength(1)
    })

    it('reports failures and does not emit import completion', async () => {
        importOSINTSources.mockRejectedValue(new Error('failed'))
        const notifications = []
        const handler = (event) => notifications.push(event.detail)
        window.addEventListener('notification', handler)
        const wrapper = mountActions()

        await buttonWithText(wrapper, 'Import').trigger('click')
        await wrapper.find('.choose-node').trigger('click')
        await wrapper.find('.choose-file').trigger('click')
        await lastButtonWithText(wrapper, 'Import').trigger('click')
        await flushPromises()
        window.removeEventListener('notification', handler)

        expect(wrapper.emitted('import-complete')).toBeUndefined()
        expect(notifications.at(-1)).toMatchObject({ type: 'error', loc: 'collectors.sources.import_error' })
    })
})
