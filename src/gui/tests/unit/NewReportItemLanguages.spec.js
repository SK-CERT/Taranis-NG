import { describe, it, expect, beforeEach, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { mountWithPlugins } from '../helpers/mount-helpers'
import NewReportItem from '@/components/analyze/NewReportItem.vue'

/**
 * A report whose type has languages gets a tab per variant language next to its own. Its own
 * language can be set or changed, and AI translates the whole report in the background.
 */

const mockAnalyzeStore = {
    getReportItemTypes: { items: [] },
    loadReportItemTypes: vi.fn()
}

const mockSettingsStore = {
    getSettings: [
        {
            key: 'CONTENT_DEFAULT_LANGUAGE',
            value: 'cs',
            options: JSON.stringify([
                { id: 'cs', txt: 'Czech' },
                { id: 'en', txt: 'English' }
            ])
        }
    ],
    getSetting: vi.fn(),
    getSettingBoolean: vi.fn()
}

vi.mock('vue-router', () => ({
    useRoute: () => ({ path: '/analyze', params: {} }),
    useRouter: () => ({ push: vi.fn(), replace: vi.fn() })
}))

vi.mock('@/composables/useAuth', () => ({
    useAuth: () => ({ checkPermission: () => true, getUserId: () => 99 })
}))

vi.mock('@/stores/analyze', () => ({
    useAnalyzeStore: () => mockAnalyzeStore
}))

vi.mock('@/stores/settings', () => ({
    useSettingsStore: () => mockSettingsStore
}))

vi.mock('@/components/analyze/NewsItemSelector.vue', () => ({ default: { name: 'NewsItemSelector', template: '<div />' } }))
vi.mock('@/components/analyze/RemoteReportItemSelector.vue', () => ({ default: { name: 'RemoteReportItemSelector', template: '<div />' } }))
vi.mock('@/components/common/StateSelector.vue', () => ({ default: { name: 'StateSelector', props: ['modelValue'], template: '<div />' } }))
vi.mock('@/components/common/attribute/AttributeContainer.vue', () => ({
    default: {
        name: 'AttributeContainer',
        props: ['attributeItem', 'edit', 'modify', 'reportItemId', 'readOnly', 'language'],
        template: '<div class="attribute-container-stub" />'
    }
}))

vi.mock('@/api/state', () => ({ getEntityTypeStates: vi.fn(() => Promise.resolve({ data: { states: [] } })) }))

vi.mock('@/api/analyze', () => ({
    createNewReportItem: vi.fn(),
    updateReportItem: vi.fn(() => Promise.resolve({ data: {} })),
    lockReportItem: vi.fn(() => Promise.resolve()),
    unlockReportItem: vi.fn(() => Promise.resolve()),
    holdLockReportItem: vi.fn(() => Promise.resolve()),
    getReportItem: vi.fn(),
    getReportItemData: vi.fn(),
    getReportItemLocks: vi.fn(() => Promise.resolve({ data: {} })),
    aiGenerate: vi.fn(),
    translateReportItem: vi.fn(),
    setReportItemTags: vi.fn((_id, tagIds) => Promise.resolve({ data: { tags: tagIds } })),
    uploadAttachment: vi.fn()
}))

vi.mock('@/api/tags', () => ({
    getEntityTypeTags: vi.fn(() =>
        Promise.resolve({
            data: {
                tags: [
                    { id: 1, display_name: 'Urgent', color: '#FF0000', icon: 'mdi-fire', system_key: null, sort_order: 0 },
                    {
                        id: 11,
                        display_name: 'translation_partial',
                        color: '#1E88E5',
                        icon: 'mdi-circle-half-full',
                        system_key: 'translation_partial',
                        sort_order: 101
                    },
                    { id: 12, display_name: 'translation_ai', icon: 'mdi-robot', system_key: 'translation_ai', sort_order: 102 },
                    { id: 13, display_name: 'translation_outdated', icon: 'mdi-update', system_key: 'translation_outdated', sort_order: 103 }
                ]
            }
        })
    )
}))

const VDialogStub = { name: 'VDialog', props: ['modelValue'], template: '<div><slot /></div>' }
const VOverlayStub = { name: 'VOverlay', props: ['modelValue'], template: '<div><slot /></div>' }

const reportType = {
    id: 5,
    title: 'Vulnerability',
    languages: ['cs', 'en'],
    translation_ai_provider_id: 3,
    attribute_groups: [
        {
            id: 1,
            title: 'Main',
            attribute_group_items: [
                { id: 11, title: 'Description', min_occurrence: 1, max_occurrence: 1, translate: true, attribute: { type: 'TEXT' } }
            ]
        }
    ]
}

const reportDetail = (language) => ({
    id: 7,
    uuid: 'uuid-7',
    title: 'Kritická chyba',
    title_prefix: 'VULN',
    language,
    report_item_type_id: 5,
    state_id: null,
    news_item_aggregates: [],
    remote_report_items: [],
    translations: { en: { title: { value: 'Critical bug', origin: 'ai', version: 1, outdated: false } } },
    attributes: [{ id: 21, attribute_group_item_id: 11, value: 'Útočník může', translations: {} }]
})

async function openReport(language = 'cs') {
    const analyzeApi = await import('@/api/analyze')
    vi.mocked(analyzeApi.getReportItem).mockResolvedValue({ data: reportDetail(language) })
    const wrapper = mountWithPlugins(NewReportItem, {
        props: { showButton: false },
        global: { stubs: { VDialog: VDialogStub, VOverlay: VOverlayStub } }
    })
    await flushPromises()
    await wrapper.vm.showDetail({ id: 7, modify: true })
    await flushPromises()
    return { wrapper, analyzeApi }
}

describe('NewReportItem languages', () => {
    beforeEach(() => {
        vi.clearAllMocks()
        mockAnalyzeStore.getReportItemTypes = { items: [reportType] }
        mockAnalyzeStore.loadReportItemTypes.mockResolvedValue({})
    })

    it('starts a new report in the users default language and creates it in the one picked', async () => {
        const analyzeApi = await import('@/api/analyze')
        vi.mocked(analyzeApi.createNewReportItem).mockResolvedValue({ data: 8 })
        const wrapper = mountWithPlugins(NewReportItem, {
            props: { showButton: false },
            global: { stubs: { VDialog: VDialogStub, VOverlay: VOverlayStub } }
        })
        await flushPromises()
        wrapper.vm.openDialog([])
        await flushPromises()

        const select = wrapper.findComponent('[data-test="report-source-language"]')
        expect(select.props('modelValue')).toBe('cs')

        select.vm.$emit('update:modelValue', 'en')
        await flushPromises()
        // Nothing to update yet: the language goes with the new report.
        expect(analyzeApi.updateReportItem).not.toHaveBeenCalled()

        wrapper.vm.selected_type = reportType
        wrapper.vm.report_item.title = 'Kernel flaw'
        await flushPromises()
        await wrapper.vm.addReportItem()

        expect(analyzeApi.createNewReportItem).toHaveBeenCalledWith(expect.objectContaining({ title: 'Kernel flaw', language: 'en' }))
    })

    it('offers a tab for each language of the type besides the report language', async () => {
        const { wrapper } = await openReport('cs')

        const tabs = wrapper.find('[data-test="report-language-tabs"]').findAll('.v-tab')
        expect(tabs.map((tab) => tab.text())).toEqual(['Czech (original)', 'English'])
    })

    it('keeps the variant tabs closed while the report language is not set', async () => {
        const { wrapper } = await openReport(null)

        const tabs = wrapper.find('[data-test="report-language-tabs"]').findAll('.v-tab')
        expect(tabs.map((tab) => tab.text())).toEqual(['Original (language not set)', 'Czech', 'English'])
        expect(tabs.slice(1).every((tab) => tab.classes().includes('v-tab--disabled') || tab.attributes('disabled') !== undefined)).toBe(true)
        expect(wrapper.find('[data-test="translate-report"]').exists()).toBe(false)
    })

    it('sets the report language', async () => {
        const { wrapper, analyzeApi } = await openReport(null)

        wrapper.findComponent('[data-test="report-source-language"]').vm.$emit('update:modelValue', 'cs')
        await flushPromises()

        expect(analyzeApi.updateReportItem).toHaveBeenCalledWith(7, { update: true, source_language: 'cs' })
        expect(wrapper.find('[data-test="translate-report"]').exists()).toBe(true)
    })

    it('translates the whole report in the background and shows the progress', async () => {
        const { wrapper, analyzeApi } = await openReport('cs')
        vi.mocked(analyzeApi.translateReportItem).mockResolvedValue({ status: 202, data: { started: true } })

        await wrapper.find('[data-test="translate-report"]').trigger('click')
        await flushPromises()
        expect(analyzeApi.translateReportItem).toHaveBeenCalledWith(7, { languages: ['en'] })
        expect(wrapper.find('[data-test="translation-progress"]').exists()).toBe(true)

        vi.mocked(analyzeApi.getReportItem).mockResolvedValue({ data: reportDetail('cs') })
        window.dispatchEvent(
            new CustomEvent('report-item-updated', { detail: { report_item_id: 7, translated: true, languages: ['en'], results: [{}] } })
        )
        await flushPromises()
        expect(wrapper.find('[data-test="translation-progress"]').exists()).toBe(false)
    })

    it('leaves the original name alone when a translated name changes', async () => {
        const { wrapper, analyzeApi } = await openReport('cs')

        window.dispatchEvent(
            new CustomEvent('report-item-updated', { detail: { report_item_id: 7, user_id: 5, update: true, language: 'en', title: '' } })
        )
        await flushPromises()

        expect(analyzeApi.getReportItemData).not.toHaveBeenCalled()
        expect(wrapper.html()).toContain('Kritická chyba')
    })

    it('puts tags on a saved report right away, and takes the ones another user puts on it', async () => {
        const { wrapper, analyzeApi } = await openReport('cs')
        expect(wrapper.find('[data-test="tag-picker"]').exists()).toBe(true)

        await wrapper.vm.changeTags([1])
        expect(analyzeApi.setReportItemTags).toHaveBeenCalledWith(7, [1])

        window.dispatchEvent(new CustomEvent('report-item-updated', { detail: { report_item_id: 7, user_id: 5, tags: [] } }))
        await flushPromises()
        expect(wrapper.vm.report_tags).toEqual([])
        expect(analyzeApi.getReportItemData).not.toHaveBeenCalled()
    })

    it('marks each language tab with its translation status', async () => {
        // The name has an English translation, the description none yet.
        const { wrapper } = await openReport('cs')

        const english = wrapper.find('[data-test="report-language-tabs"]').findAll('.v-tab').at(1)
        expect(english.find('[data-test="tab-status-translation_partial"]').exists()).toBe(true)
    })

    it('marks a translation outdated as soon as its original changes, and not once it is changed back', async () => {
        const { wrapper } = await openReport('cs')
        const description = wrapper.vm.attribute_groups[0].attribute_group_items[0].values[0]
        description.translations = { en: { value: 'An attacker can', origin: 'manual', version: 1, outdated: false } }
        wrapper.vm.report_item.title_prefix = ''
        await flushPromises()
        const english = () => wrapper.find('[data-test="report-language-tabs"]').findAll('.v-tab').at(1)
        expect(english().find('[data-test="tab-status-translation_ai"]').exists()).toBe(true)

        wrapper.vm.report_item.title = 'Kritická chyba v jádře'
        await flushPromises()
        expect(wrapper.vm.translations.en.title.outdated).toBe(true)
        expect(english().find('[data-test="tab-status-translation_outdated"]').exists()).toBe(true)

        wrapper.vm.report_item.title = 'Kritická chyba'
        description.value = 'Útočník může vzdáleně'
        await flushPromises()
        expect(wrapper.vm.translations.en.title.outdated).toBe(false)
        expect(description.translations.en.outdated).toBe(true)
        expect(english().find('[data-test="tab-status-translation_outdated"]').exists()).toBe(true)
    })

    it('takes fresh translations and tags on a background refresh, without rebuilding the form', async () => {
        const { wrapper, analyzeApi } = await openReport('cs')
        const groups = wrapper.vm.attribute_groups
        const fresh = reportDetail('cs')
        fresh.tags = [1]
        fresh.translations = { en: { title: { value: 'Critical flaw', origin: 'manual', version: 2, outdated: false } } }
        fresh.attributes[0].translations = { en: { value: 'An attacker can', origin: 'manual', version: 1, outdated: false } }
        vi.mocked(analyzeApi.getReportItem).mockResolvedValue({ data: fresh })

        await wrapper.vm.showDetail({ id: 7 }, false)
        await flushPromises()

        expect(wrapper.vm.attribute_groups).toBe(groups)
        expect(wrapper.vm.report_tags).toEqual([1])
        expect(wrapper.vm.translations.en.title.value).toBe('Critical flaw')
        expect(wrapper.vm.attribute_groups[0].attribute_group_items[0].values[0].translations.en.value).toBe('An attacker can')
    })
})
