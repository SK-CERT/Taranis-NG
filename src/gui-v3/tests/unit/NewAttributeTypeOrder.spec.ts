import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { mountWithPlugins } from '../helpers/mount-helpers'
import NewAttribute from '@/components/config/reports/NewAttribute.vue'

/**
 * The attribute type list is long enough that finding a type in it is a scan, not a glance, so
 * the dialog sorts it. The source list stays in the order the backend enum declares them, which
 * is why the ordering has to be asserted on what the select actually offers.
 */

vi.mock('@/composables/useAuth', () => ({
    useAuth: () => ({ checkPermission: () => true })
}))

vi.mock('@/api/config', () => ({
    createNewAttribute: vi.fn(),
    updateAttribute: vi.fn(),
    getAttributeEnums: vi.fn().mockResolvedValue({ data: { items: [], total_count: 0 } }),
    addAttributeEnum: vi.fn(),
    updateAttributeEnum: vi.fn(),
    deleteAttributeEnum: vi.fn(),
    reloadDictionaries: vi.fn()
}))

const VDialogStub = {
    name: 'VDialog',
    props: ['modelValue'],
    template: '<div><slot /><slot name="activator" :props="{}" /></div>'
}

const mountDialog = () =>
    mountWithPlugins(NewAttribute, {
        props: { editItem: null },
        global: {
            stubs: {
                VDialog: VDialogStub,
                DialogToolbar: true,
                EditableEntityTable: true,
                AttributeConstantCsvImport: true,
                UnsavedChangesDialog: true,
                AddNewButton: true
            }
        }
    })

const typeOptions = (wrapper: ReturnType<typeof mountDialog>): { title: string; value: string }[] =>
    wrapper.findAllComponents({ name: 'VSelect' })[0]?.props('items') as { title: string; value: string }[]

describe('NewAttribute type list', () => {
    beforeEach(() => vi.clearAllMocks())

    it('offers the types in alphabetical order', async () => {
        const wrapper = mountDialog()
        await flushPromises()

        const titles = typeOptions(wrapper).map((option) => option.title)

        expect(titles).toEqual([...titles].sort((a, b) => a.localeCompare(b)))
    })

    it('still offers every backend attribute type', async () => {
        const wrapper = mountDialog()
        await flushPromises()

        const values = typeOptions(wrapper)
            .map((option) => option.value)
            .sort()

        // Mirrors shared/schema/attribute.py AttributeType; sorting must not drop a type.
        expect(values).toEqual(
            [
                'ATTACHMENT',
                'BOOLEAN',
                'CPE',
                'CVE',
                'CVSS',
                'CWE',
                'DATE',
                'DATE_TIME',
                'ENUM',
                'LINK',
                'MULTI_CHOICE',
                'NUMBER',
                'RADIO',
                'RICH_TEXT',
                'STRING',
                'TEXT',
                'TIME',
                'TLP'
            ].sort()
        )
    })
})
