import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { mountWithPlugins } from '../helpers/mount-helpers'
import NewAttribute from '@/components/config/reports/NewAttribute.vue'

const { checkPermission } = vi.hoisted(() => ({ checkPermission: vi.fn() }))

vi.mock('@/composables/useAuth', () => ({
    useAuth: () => ({ checkPermission })
}))

vi.mock('@/api/config', () => ({
    createNewAttribute: vi.fn(),
    updateAttribute: vi.fn(),
    getAttributeEnums: vi.fn().mockResolvedValue({ data: { items: [], total_count: 0 } }),
    addAttributeEnum: vi.fn().mockResolvedValue({}),
    updateAttributeEnum: vi.fn(),
    deleteAttributeEnum: vi.fn(),
    reloadDictionaries: vi.fn().mockResolvedValue({})
}))

const VDialogStub = {
    name: 'VDialog',
    props: ['modelValue'],
    template: '<div v-if="modelValue"><slot /><slot name="activator" :props="{}" /></div>'
}

const DialogToolbarStub = {
    name: 'DialogToolbar',
    props: ['title', 'saving', 'showSave'],
    template: '<div class="dialog-toolbar" />'
}

const EditableEntityTableStub = {
    name: 'EditableEntityTable',
    props: ['items', 'loading', 'disabled'],
    template: '<div class="constants-table"><slot name="form" :item="{}" /></div>'
}

const CsvImportStub = {
    name: 'AttributeConstantCsvImport',
    props: ['modelValue', 'show', 'busy', 'error'],
    emits: ['import', 'update:modelValue'],
    template: '<button v-if="show" class="csv-import" @click="$emit(\'import\', payload)">csv</button>',
    data: () => ({
        payload: {
            items: [{ value: 'CVE-2026-1', description: 'Example' }],
            replaceExisting: true
        }
    })
}

const editItem = {
    id: 42,
    name: 'CVE',
    description: 'CVE dictionary',
    type: 'CVE',
    default_value: '',
    validator: 'NONE',
    validator_parameter: ''
}

const mountDialog = () =>
    mountWithPlugins(NewAttribute, {
        props: { editItem },
        global: {
            stubs: {
                VDialog: VDialogStub,
                DialogToolbar: DialogToolbarStub,
                EditableEntityTable: EditableEntityTableStub,
                AttributeConstantCsvImport: CsvImportStub,
                UnsavedChangesDialog: true,
                AddNewButton: true
            }
        }
    })

describe('NewAttribute dictionary administration', () => {
    beforeEach(async () => {
        vi.clearAllMocks()
        const api = await import('@/api/config')
        vi.mocked(api.getAttributeEnums).mockResolvedValue({ data: { items: [], total_count: 0 } } as never)
        vi.mocked(api.addAttributeEnum).mockResolvedValue({} as never)
        vi.mocked(api.reloadDictionaries).mockResolvedValue({} as never)
    })

    it('gates reload by update permission and import by the existing create endpoint permission', async () => {
        checkPermission.mockReturnValue(true)
        const wrapper = mountDialog()
        await flushPromises()

        expect(wrapper.find('.csv-import').exists()).toBe(true)
        expect(wrapper.text()).toContain('Reload CVE Dictionary')

        checkPermission.mockImplementation((permission: string) => permission === 'CONFIG_ATTRIBUTE_UPDATE')
        const updateOnly = mountDialog()
        await flushPromises()
        expect(updateOnly.find('.csv-import').exists()).toBe(false)
        expect(updateOnly.text()).toContain('Reload CVE Dictionary')

        checkPermission.mockReturnValue(false)
        const unauthorized = mountDialog()
        await flushPromises()
        expect(unauthorized.text()).not.toContain('Reload CVE Dictionary')
    })

    it('reloads the selected dictionary and refreshes its constants', async () => {
        checkPermission.mockReturnValue(true)
        const api = await import('@/api/config')
        const wrapper = mountDialog()
        await flushPromises()

        const reloadButton = wrapper.findAllComponents({ name: 'VBtn' }).find((button) => button.text() === 'Reload CVE Dictionary')
        if (!reloadButton) throw new Error('Reload button was not rendered')
        await reloadButton.trigger('click')
        await flushPromises()

        expect(api.reloadDictionaries).toHaveBeenCalledWith('cve')
        expect(api.getAttributeEnums).toHaveBeenCalledWith(expect.objectContaining({ attribute_id: 42, offset: 0 }))
    })

    it('imports constants with replace mode through the existing enum endpoint', async () => {
        checkPermission.mockReturnValue(true)
        const api = await import('@/api/config')
        const wrapper = mountDialog()
        await flushPromises()

        await wrapper.find('.csv-import').trigger('click')
        await flushPromises()

        expect(api.addAttributeEnum).toHaveBeenCalledWith(42, {
            items: [{ value: 'CVE-2026-1', description: 'Example' }],
            delete_existing: true
        })
    })

    it('surfaces backend reload errors in the dialog', async () => {
        checkPermission.mockImplementation((permission: string) => permission === 'CONFIG_ATTRIBUTE_UPDATE')
        const api = await import('@/api/config')
        vi.mocked(api.reloadDictionaries).mockRejectedValue({ response: { data: { error: 'CVE source is unavailable' } } })
        const wrapper = mountDialog()
        await flushPromises()

        const reloadButton = wrapper.findAllComponents({ name: 'VBtn' }).find((button) => button.text() === 'Reload CVE Dictionary')
        if (!reloadButton) throw new Error('Reload button was not rendered')
        await reloadButton.trigger('click')
        await flushPromises()

        expect(wrapper.text()).toContain('CVE source is unavailable')
    })
})
