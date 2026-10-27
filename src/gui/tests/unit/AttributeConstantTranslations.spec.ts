import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { mountWithPlugins } from '../helpers/mount-helpers'
import AttributeConstantTranslations from '@/components/config/reports/AttributeConstantTranslations.vue'

// Language variants of an attribute's constants: a tab per language of the report types using
// the attribute, saved per constant, and AI translation of what is missing in batches.

vi.mock('@/api/config', () => ({
    getAttributeLanguages: vi.fn(),
    getAttributeEnums: vi.fn(),
    translateAttributeEnums: vi.fn(),
    updateAttributeEnum: vi.fn(() => Promise.resolve({}))
}))

const constants = [
    { id: 10, index: 0, value: 'High', description: 'Act now', translations: { cs: { value: 'Vysoká', description: 'Jednejte' } } },
    { id: 11, index: 1, value: 'Low', description: '', translations: {} }
]

describe('AttributeConstantTranslations', () => {
    let configApi: typeof import('@/api/config')

    beforeEach(async () => {
        vi.clearAllMocks()
        configApi = await import('@/api/config')
        vi.mocked(configApi.getAttributeLanguages).mockResolvedValue({
            data: { languages: ['cs', 'sk'], source_language: 'en', ai_providers: [{ id: 3, name: 'Local' }] }
        } as never)
        vi.mocked(configApi.getAttributeEnums).mockResolvedValue({ data: { items: constants, total_count: 2 } } as never)
    })

    it('lists each constant with its translation in the open language', async () => {
        const wrapper = mountWithPlugins(AttributeConstantTranslations, { props: { attributeId: 5, canUpdate: true } })
        await flushPromises()

        expect(wrapper.vm.languages).toEqual(['cs', 'sk'])
        expect(wrapper.vm.rows.map((row: { translated_value: string }) => row.translated_value)).toEqual(['Vysoká', ''])
        expect(wrapper.text()).toContain('Vysoká')
    })

    it('saves a translation next to the others of the constant', async () => {
        const wrapper = mountWithPlugins(AttributeConstantTranslations, { props: { attributeId: 5, canUpdate: true } })
        await flushPromises()
        wrapper.vm.language = 'sk'
        await flushPromises()

        const row = { ...wrapper.vm.rows[0], translated_value: 'Vysoká (sk)', translated_description: '' }
        wrapper.findComponent({ name: 'EditableEntityTable' }).vm.$emit('save', row, { isNew: false })
        await flushPromises()

        expect(configApi.updateAttributeEnum).toHaveBeenCalledWith(5, 10, [
            {
                value: 'High',
                description: 'Act now',
                translations: { cs: { value: 'Vysoká', description: 'Jednejte' }, sk: { value: 'Vysoká (sk)', description: '' } }
            }
        ])
    })

    it('translates what is missing in batches until nothing is left', async () => {
        vi.mocked(configApi.translateAttributeEnums)
            .mockResolvedValueOnce({ data: { translated: 100, failed: 0, remaining: 20 } } as never)
            .mockResolvedValueOnce({ data: { translated: 20, failed: 0, remaining: 0 } } as never)
        const wrapper = mountWithPlugins(AttributeConstantTranslations, { props: { attributeId: 5, canUpdate: true } })
        await flushPromises()

        await wrapper.find('[data-test="translate-constants"]').trigger('click')
        await flushPromises()

        expect(configApi.translateAttributeEnums).toHaveBeenCalledTimes(2)
        expect(configApi.translateAttributeEnums).toHaveBeenCalledWith(5, { language: 'cs', ai_provider_id: 3, source_language: 'en' })
    })

    it('stops when a batch translates nothing', async () => {
        vi.mocked(configApi.translateAttributeEnums).mockResolvedValue({ data: { translated: 0, failed: 5, remaining: 5 } } as never)
        const wrapper = mountWithPlugins(AttributeConstantTranslations, { props: { attributeId: 5, canUpdate: true } })
        await flushPromises()

        await wrapper.find('[data-test="translate-constants"]').trigger('click')
        await flushPromises()

        expect(configApi.translateAttributeEnums).toHaveBeenCalledTimes(1)
    })

    it('says so when no report type using the attribute has other languages', async () => {
        vi.mocked(configApi.getAttributeLanguages).mockResolvedValue({ data: { languages: [], ai_providers: [] } } as never)
        const wrapper = mountWithPlugins(AttributeConstantTranslations, { props: { attributeId: 5, canUpdate: true } })
        await flushPromises()

        expect(wrapper.text()).toContain('No report type that uses this attribute has other languages.')
        expect(configApi.getAttributeEnums).not.toHaveBeenCalled()
    })
})
