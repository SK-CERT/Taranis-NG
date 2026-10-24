import { describe, expect, it, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { mountWithPlugins } from '../helpers/mount-helpers'
import NewReportType from '@/components/config/reports/NewReportType.vue'
import { getGlossary } from '@/api/config'

// Edit report item type: a saved type has a Glossary tab with its own entries, offered in the
// type's languages; a new type has none to save them to yet.

vi.mock('@/api/config', () => ({
    getAllAttributes: vi.fn(() => Promise.resolve({ data: { items: [] } })),
    getAllAiProviders: vi.fn(() => Promise.resolve({ data: { items: [] } })),
    createNewReportItemType: vi.fn(),
    updateReportItemType: vi.fn(),
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

const mount = (editItem: Record<string, unknown>) =>
    mountWithPlugins(NewReportType, { props: { editItem }, global: { stubs: { VDialog: VDialogStub } } })

describe('Report type glossary tab', () => {
    it("shows a saved type's own glossary, in the type's languages", async () => {
        const wrapper = mount({ id: 9, title: 'Vulnerability', languages: ['sk'], label_language: 'en', attribute_groups: [] })
        await flushPromises()

        await wrapper.get('[data-test="report-type-glossary-tab"]').trigger('click')
        await flushPromises()

        expect(getGlossary).toHaveBeenCalledWith(9)
        expect(wrapper.findComponent({ name: 'GlossaryTable' }).props()).toMatchObject({ reportItemTypeId: 9, languages: ['sk', 'en'] })
    })

    it('has no glossary tab for a type not saved yet', async () => {
        const wrapper = mount({ title: 'New', languages: ['sk'], label_language: 'en', attribute_groups: [] })
        await flushPromises()

        expect(wrapper.find('[data-test="report-type-label-tabs"]').exists()).toBe(true)
        expect(wrapper.find('[data-test="report-type-glossary-tab"]').exists()).toBe(false)
    })
})
