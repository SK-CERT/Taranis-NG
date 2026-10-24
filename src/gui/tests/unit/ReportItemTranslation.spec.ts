import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { mountWithPlugins } from '../helpers/mount-helpers'
import ReportItemTranslation from '@/components/analyze/ReportItemTranslation.vue'

// A language tab of a report: translated names and text values are edited and saved with the
// language; fields that are not translated are shown as in the original, read only.

vi.mock('@/api/analyze', () => ({
    getReportItemData: vi.fn(),
    holdLockReportItem: vi.fn(() => Promise.resolve()),
    lockReportItem: vi.fn(() => Promise.resolve()),
    unlockReportItem: vi.fn(() => Promise.resolve()),
    updateReportItem: vi.fn(() => Promise.resolve({ data: {} })),
    translateReportItem: vi.fn(),
    reviewReportItemTranslations: vi.fn()
}))

vi.mock('@/composables/useAuth', () => ({
    useAuth: () => ({ getUserId: () => 101, checkPermission: () => true })
}))

vi.mock('@/components/common/attribute/AttributeContainer.vue', () => ({
    default: {
        name: 'AttributeContainer',
        props: ['attributeItem', 'edit', 'modify', 'reportItemId', 'readOnly', 'language'],
        template: '<div class="attribute-container-stub" />'
    }
}))

const descriptionItem = {
    id: 11,
    title: 'Description',
    translate: true,
    translations: { en: { title: 'Description (EN)' } },
    attribute: { type: 'TEXT' }
}
const cveItem = { id: 12, title: 'CVE', translate: false, translations: {}, attribute: { type: 'CVE' } }

const makeProps = () => ({
    reportItemId: 7,
    language: 'en',
    title: 'Kritická chyba',
    titlePrefix: 'VULN',
    titleTranslations: {
        title: { value: 'Critical bug', origin: 'manual' as const, version: 2, outdated: false }
    },
    attributeGroups: [
        {
            id: 1,
            title: 'Hlavní',
            attribute_group_items: [
                {
                    attribute_group_item: descriptionItem,
                    values: [
                        {
                            id: 21,
                            value: 'Útočník může',
                            translations: { en: { value: 'An attacker can', origin: 'ai' as const, version: 1, outdated: true } }
                        }
                    ]
                },
                { attribute_group_item: cveItem, values: [{ id: 22, value: 'CVE-2026-1' }] }
            ]
        }
    ],
    reportType: { attribute_groups: [{ id: 1, title: 'Hlavní', translations: { en: { title: 'Main' } } }] },
    canModify: true,
    modify: true,
    canTranslate: true
})

describe('ReportItemTranslation', () => {
    let analyzeApi: typeof import('@/api/analyze')

    beforeEach(async () => {
        vi.clearAllMocks()
        analyzeApi = await import('@/api/analyze')
    })

    it('labels groups and fields in its language and edits only translated fields', async () => {
        const wrapper = mountWithPlugins(ReportItemTranslation, { props: makeProps() })
        await flushPromises()

        expect(wrapper.text()).toContain('Main')
        expect(wrapper.text()).toContain('Description (EN)')
        const containers = wrapper.findAllComponents({ name: 'AttributeContainer' })
        expect(containers).toHaveLength(2)
        expect(containers[0]!.props('language')).toBe('en')
        expect(containers[0]!.props('attributeItem').values[0]).toMatchObject({ id: 21, value: 'An attacker can', version: 1 })
        expect(containers[1]!.props('language')).toBeUndefined()
        expect(containers[1]!.props('readOnly')).toBe(true)
        expect(wrapper.find('[data-test="translation-ai"]').exists()).toBe(true)
        expect(wrapper.find('[data-test="translation-outdated"]').exists()).toBe(true)
    })

    it('saves a translated name with its language and locks it per language', async () => {
        const wrapper = mountWithPlugins(ReportItemTranslation, { props: makeProps() })
        await flushPromises()
        const field = wrapper.findComponent('[data-test="translation-title"]')
        const input = field.find('input')

        await input.trigger('focus')
        await input.setValue('Critical flaw')
        await input.trigger('blur')
        await flushPromises()

        expect(analyzeApi.lockReportItem).toHaveBeenCalledWith(7, { field_id: 'title:en' })
        expect(analyzeApi.updateReportItem).toHaveBeenCalledWith(7, { update: true, language: 'en', title: 'Critical flaw' })
        expect(analyzeApi.unlockReportItem).toHaveBeenCalledWith(7, { field_id: 'title:en' })
    })

    it('asks before letting AI replace a translation a person wrote', async () => {
        const translations = { translations: { en: {} }, attributes: {} }
        vi.mocked(analyzeApi.translateReportItem).mockResolvedValue({ data: { results: [{}], translations } } as never)
        const wrapper = mountWithPlugins(ReportItemTranslation, { props: makeProps() })
        await flushPromises()

        const buttons = wrapper.findAll('button[title="Translate with AI"]')
        // Name prefix (no translation), name (manual), description value (AI).
        await buttons[1]!.trigger('click')
        await flushPromises()
        expect(analyzeApi.translateReportItem).not.toHaveBeenCalled()

        wrapper.findComponent({ name: 'ConfirmationDialog' }).vm.$emit('confirm')
        await flushPromises()
        expect(analyzeApi.translateReportItem).toHaveBeenCalledWith(7, { languages: ['en'], fields: ['title'], overwrite_manual: true })
        expect(wrapper.emitted('translations-updated')?.[0]).toEqual([translations])
    })

    it('lets AI replace its own translation without asking', async () => {
        vi.mocked(analyzeApi.translateReportItem).mockResolvedValue({ data: { results: [{}] } } as never)
        const wrapper = mountWithPlugins(ReportItemTranslation, { props: makeProps() })
        await flushPromises()

        const buttons = wrapper.findAll('button[title="Translate with AI"]')
        await buttons[2]!.trigger('click')
        await flushPromises()

        expect(analyzeApi.translateReportItem).toHaveBeenCalledWith(7, { languages: ['en'], fields: ['21'], overwrite_manual: false })
    })

    it('asks the parent to translate the whole language', async () => {
        const wrapper = mountWithPlugins(ReportItemTranslation, { props: makeProps() })
        await flushPromises()

        await wrapper.find('[data-test="translate-language"]').trigger('click')

        expect(wrapper.emitted('translate-language')?.[0]).toEqual(['en'])
    })

    it('marks one AI translation as reviewed and takes the stored translations', async () => {
        const stored = {
            translations: {},
            attributes: { '21': { en: { value: 'An attacker can', origin: 'manual', version: 2, outdated: false } } }
        }
        vi.mocked(analyzeApi.reviewReportItemTranslations).mockResolvedValue({
            data: { reviewed: ['21'], skipped_locked: [], translations: stored }
        } as never)
        const wrapper = mountWithPlugins(ReportItemTranslation, { props: makeProps() })
        await flushPromises()

        // Only the AI translation offers it; the name a person wrote does not.
        const buttons = wrapper.findAll('[data-test="translation-review"]')
        expect(buttons).toHaveLength(1)
        await buttons[0]!.trigger('click')
        await flushPromises()

        expect(analyzeApi.reviewReportItemTranslations).toHaveBeenCalledWith(7, { language: 'en', fields: ['21'] })
        expect(wrapper.emitted('translations-updated')).toEqual([[stored]])
    })

    it('marks every AI translation of the language as reviewed at once', async () => {
        const notifications: CustomEvent[] = []
        window.addEventListener('notification', (event) => notifications.push(event as CustomEvent))
        vi.mocked(analyzeApi.reviewReportItemTranslations).mockResolvedValue({
            data: { reviewed: ['title', '21'], skipped_locked: [], translations: { translations: {}, attributes: {} } }
        } as never)
        const props = makeProps()
        props.titleTranslations.title = { value: 'Critical bug', origin: 'ai' as never, version: 1, outdated: false }
        const wrapper = mountWithPlugins(ReportItemTranslation, { props })
        await flushPromises()

        expect(wrapper.vm.unreviewedKeys).toEqual(['title', '21'])
        await wrapper.get('[data-test="review-language"]').trigger('click')
        await flushPromises()

        expect(analyzeApi.reviewReportItemTranslations).toHaveBeenCalledWith(7, { language: 'en' })
        expect(notifications.at(-1)?.detail).toEqual({ type: 'success', loc: 'report_item.translation.reviewed', params: { count: 2 } })
    })

    it('does not offer a review of a field somebody else is editing, and says when one was skipped', async () => {
        const notifications: CustomEvent[] = []
        window.addEventListener('notification', (event) => notifications.push(event as CustomEvent))
        vi.mocked(analyzeApi.reviewReportItemTranslations).mockResolvedValue({
            data: { reviewed: [], skipped_locked: ['21'], translations: { translations: {}, attributes: {} } }
        } as never)
        const wrapper = mountWithPlugins(ReportItemTranslation, { props: { ...makeProps(), locks: { '21:en': { user_id: 5 } } } })
        await flushPromises()

        expect(wrapper.find('[data-test="translation-review"]').exists()).toBe(false)
        await wrapper.vm.review()
        await flushPromises()

        expect(notifications.at(-1)?.detail).toEqual({ type: 'warning', loc: 'report_item.translation.review_locked' })
    })

    it('offers no review to somebody who cannot change the report', async () => {
        const wrapper = mountWithPlugins(ReportItemTranslation, { props: { ...makeProps(), canModify: false } })
        await flushPromises()

        expect(wrapper.find('[data-test="translation-review"]').exists()).toBe(false)
        expect(wrapper.find('[data-test="review-language"]').exists()).toBe(false)
    })
})
