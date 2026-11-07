import { describe, expect, it, vi, beforeEach } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { mountWithPlugins } from '../helpers/mount-helpers'
import NewReportType from '@/components/config/reports/NewReportType.vue'
import MdiIconPicker from '@/components/common/MdiIconPicker.vue'
import { updateReportItemType } from '@/api/config'

// Edit report item type: the icon beside its name is the one the type and its reports show.

vi.mock('@/api/config', () => ({
    getAllAttributes: vi.fn(() => Promise.resolve({ data: { items: [] } })),
    getAllAiProviders: vi.fn(() => Promise.resolve({ data: { items: [] } })),
    createNewReportItemType: vi.fn(),
    updateReportItemType: vi.fn(() => Promise.resolve({ data: {} })),
    translateReportItemTypeLabels: vi.fn(),
    getGlossary: vi.fn(() => Promise.resolve({ data: { items: [], languages: [] } })),
    createGlossaryEntry: vi.fn(),
    updateGlossaryEntry: vi.fn(),
    deleteGlossaryEntry: vi.fn()
}))

vi.mock('@/composables/useAuth', () => ({
    useAuth: () => ({ checkPermission: () => true })
}))

const VDialogStub = { name: 'VDialog', template: '<div><slot /></div>' }

const mount = async (editItem: Record<string, unknown>) => {
    const wrapper = mountWithPlugins(NewReportType, { props: { editItem }, global: { stubs: { VDialog: VDialogStub } } })
    await flushPromises()
    return wrapper
}

const persist = (wrapper: Awaited<ReturnType<typeof mount>>): Promise<boolean> =>
    (wrapper.vm as unknown as { persist: () => Promise<boolean> }).persist()

describe('Report type icon', () => {
    beforeEach(() => {
        vi.mocked(updateReportItemType).mockClear()
    })

    it('stores no icon until another one than the default is picked', async () => {
        const wrapper = await mount({ id: 9, title: 'Vulnerability', attribute_groups: [] })
        const picker = wrapper.findComponent(MdiIconPicker)
        expect(picker.props('modelValue')).toBe('mdi-file-table-outline')

        expect(await persist(wrapper)).toBe(true)
        expect(vi.mocked(updateReportItemType).mock.calls[0]?.[0]).toMatchObject({ id: 9, icon: null })

        picker.vm.$emit('update:modelValue', 'mdi-bug')
        expect(await persist(wrapper)).toBe(true)
        expect(vi.mocked(updateReportItemType).mock.calls[1]?.[0]).toMatchObject({ id: 9, icon: 'mdi-bug' })
    })

    it("shows the type's own icon beside its name, the label as the button's tooltip", async () => {
        const wrapper = await mount({ id: 9, title: 'Vulnerability', icon: 'mdi-bug', attribute_groups: [] })
        const picker = wrapper.findComponent(MdiIconPicker)

        expect(picker.props('modelValue')).toBe('mdi-bug')
        expect(picker.find('.mdi-icon-picker__label').exists()).toBe(false)
        expect(picker.get('.mdi-icon-picker__trigger').attributes('title')).toBe('Icon')
    })
})
