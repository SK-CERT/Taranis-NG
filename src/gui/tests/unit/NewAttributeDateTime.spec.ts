import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { mountWithPlugins } from '../helpers/mount-helpers'
import NewAttribute from '@/components/config/reports/NewAttribute.vue'
import { toLocalDateTime } from '@/utils/dateTime'

// Snapshot the request before the dialog resets its reactive form after saving.
const { submitted } = vi.hoisted(() => ({ submitted: vi.fn() }))

vi.mock('@/composables/useAuth', () => ({ useAuth: () => ({ checkPermission: () => true }) }))
vi.mock('@/api/config', () => ({
    createNewAttribute: vi.fn(),
    updateAttribute: vi.fn(async (payload) => {
        submitted({ ...payload })
        return {}
    }),
    getAttributeEnums: vi.fn(),
    addAttributeEnum: vi.fn(),
    updateAttributeEnum: vi.fn(),
    deleteAttributeEnum: vi.fn(),
    reloadDictionaries: vi.fn()
}))

const mountDialog = (type: string, defaultValue: string) =>
    mountWithPlugins(NewAttribute, {
        props: {
            editItem: {
                id: 42,
                name: 'Timestamp',
                description: '',
                type,
                default_value: defaultValue,
                validator: 'NONE',
                validator_parameter: ''
            }
        },
        global: {
            stubs: {
                VDialog: { template: '<div><slot /></div>' },
                DialogToolbar: { name: 'DialogToolbar', emits: ['save'], template: '<div />' },
                UnsavedChangesDialog: true,
                AddNewButton: true,
                EditableEntityTable: true,
                AttributeConstantCsvImport: true
            }
        }
    })

describe('attribute date-time defaults', () => {
    beforeEach(() => vi.clearAllMocks())

    it('shows local input time and submits UTC after an edit', async () => {
        const initial = '2026-07-14T23:30:00Z'
        const wrapper = mountDialog('DATE_TIME', initial)
        await flushPromises()
        const field = wrapper.findAllComponents({ name: 'VTextField' }).find((field) => field.props('label') === 'Default Value')!

        expect(field.props('type')).toBe('datetime-local')
        expect(field.props('modelValue')).toBe(toLocalDateTime(initial))
        await field.vm.$emit('update:modelValue', '2026-07-15T12:45')
        await wrapper.findComponent({ name: 'DialogToolbar' }).vm.$emit('save')
        await flushPromises()

        expect(submitted).toHaveBeenCalledWith(expect.objectContaining({ default_value: new Date(2026, 6, 15, 12, 45).toISOString() }))
        wrapper.unmount()
    })

    it('keeps date-only defaults as calendar dates', async () => {
        const wrapper = mountDialog('DATE', '2026-07-15')
        await flushPromises()
        const field = wrapper.findAllComponents({ name: 'VTextField' }).find((field) => field.props('label') === 'Default Value')!
        expect(field.props('type')).toBe('text')
        expect(field.props('modelValue')).toBe('2026-07-15')
        await field.vm.$emit('update:modelValue', '2026-07-16')
        await wrapper.findComponent({ name: 'DialogToolbar' }).vm.$emit('save')
        await flushPromises()

        expect(submitted).toHaveBeenCalledWith(expect.objectContaining({ default_value: '2026-07-16' }))
        wrapper.unmount()
    })
})
