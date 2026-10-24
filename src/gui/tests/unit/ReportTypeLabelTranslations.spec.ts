import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { mountWithPlugins } from '../helpers/mount-helpers'
import ReportTypeLabelTranslations from '@/components/config/reports/ReportTypeLabelTranslations.vue'

// Label variants of a report type in one language. The AI fills only labels without a
// translation, and nothing is stored until the report type is saved.

vi.mock('@/api/config', () => ({
    translateReportItemTypeLabels: vi.fn()
}))

const makeType = () => ({
    title: 'Vulnerability',
    description: '',
    translations: { cs: { title: 'Zranitelnost' } } as Record<string, Record<string, string>>,
    attribute_groups: [
        {
            id: 1,
            title: 'Main',
            description: 'What happened',
            section_title: '',
            translations: {} as Record<string, Record<string, string>>,
            attribute_group_items: [
                { id: 11, title: 'Description', description: '', translations: {} as Record<string, Record<string, string>> }
            ]
        }
    ]
})

describe('ReportTypeLabelTranslations', () => {
    let configApi: typeof import('@/api/config')

    beforeEach(async () => {
        vi.clearAllMocks()
        configApi = await import('@/api/config')
    })

    it('sends only missing labels and puts the answers in place', async () => {
        vi.mocked(configApi.translateReportItemTypeLabels).mockResolvedValue({
            data: { translations: { 'g0.title': 'Hlavní', 'g0.description': 'Co se stalo', 'g0.i0.title': 'Popis' }, failed: {} }
        } as never)
        const reportType = makeType()
        const wrapper = mountWithPlugins(ReportTypeLabelTranslations, {
            props: { modelValue: reportType, language: 'cs', sourceLanguage: 'en', aiProviderId: 3 }
        })

        await wrapper.find('[data-test="translate-labels"]').trigger('click')
        await flushPromises()

        expect(configApi.translateReportItemTypeLabels).toHaveBeenCalledWith({
            texts: { 'g0.title': 'Main', 'g0.description': 'What happened', 'g0.i0.title': 'Description' },
            source_language: 'en',
            target_language: 'cs',
            ai_provider_id: 3
        })
        expect(reportType.translations['cs']).toEqual({ title: 'Zranitelnost' })
        expect(reportType.attribute_groups[0]!.translations['cs']).toEqual({ title: 'Hlavní', description: 'Co se stalo' })
        expect(reportType.attribute_groups[0]!.attribute_group_items[0]!.translations['cs']).toEqual({ title: 'Popis' })
    })

    it('copies the original shown under a field into it, where there is one', async () => {
        const reportType = makeType()
        const wrapper = mountWithPlugins(ReportTypeLabelTranslations, {
            props: { modelValue: reportType, language: 'cs' }
        })

        // Type name, group name and description, field name: the empty originals have no button.
        const buttons = wrapper.findAll('[data-test="copy-original"]')
        expect(buttons).toHaveLength(4)

        await buttons[1]!.trigger('click')
        await buttons[0]!.trigger('click')

        expect(reportType.attribute_groups[0]!.translations['cs']).toEqual({ title: 'Main' })
        expect(reportType.translations['cs']).toEqual({ title: 'Vulnerability' })
    })

    it('does not copy while the form is read-only', () => {
        const wrapper = mountWithPlugins(ReportTypeLabelTranslations, {
            props: { modelValue: makeType(), language: 'cs', disabled: true }
        })

        const buttons = wrapper.findAll('[data-test="copy-original"]')
        expect(buttons).toHaveLength(4)
        for (const button of buttons) expect(button.attributes('disabled')).toBeDefined()
    })

    it('cannot translate without an AI provider', () => {
        const wrapper = mountWithPlugins(ReportTypeLabelTranslations, {
            props: { modelValue: makeType(), language: 'cs', aiProviderId: null }
        })

        expect(wrapper.find('[data-test="translate-labels"]').attributes('disabled')).toBeDefined()
    })
})
