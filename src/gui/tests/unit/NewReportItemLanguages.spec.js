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
    uploadAttachment: vi.fn(),
    getCvdStatus: vi.fn(() => Promise.resolve({ data: { organizations: [], gna_configured: false, cna_configured: false } })),
    reserveCveId: vi.fn(),
    rejectCveId: vi.fn()
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

    describe('a CVD Report', () => {
        const cvdType = { id: 6, title: 'CVD Report', system_key: 'cvd', locked: true, enabled: true, languages: [], attribute_groups: [] }
        // The author's organizations a CVD Report can belong to: CERT is a GNA and a CNA.
        const CERT = { id: 3, name: 'CERT', gna_id: 65535, gna_configured: true, cna_configured: true }
        const PARTNER = { id: 4, name: 'Partner CERT', gna_id: null, gna_configured: false, cna_configured: true }
        const statusOf = (...organizations) => ({
            organizations,
            gna_configured: organizations.some((organization) => organization.gna_configured),
            cna_configured: organizations.some((organization) => organization.cna_configured)
        })
        // The report's organization as core describes it.
        const ofCert = (fields = {}) => ({ organization_id: 3, cvd_organization: { ...CERT, ...fields } })

        async function startCvdReport(status = statusOf(CERT)) {
            const analyzeApi = await import('@/api/analyze')
            vi.mocked(analyzeApi.getCvdStatus).mockResolvedValue({ data: status })
            mockAnalyzeStore.getReportItemTypes = { items: [reportType, cvdType] }
            const wrapper = mountWithPlugins(NewReportItem, {
                props: { showButton: false },
                global: { stubs: { VDialog: VDialogStub, VOverlay: VOverlayStub } }
            })
            await flushPromises()
            wrapper.vm.openDialog([])
            await flushPromises()
            const typeSelect = wrapper
                .findAllComponents({ name: 'VCombobox' })
                .find((select) => (select.props('items') ?? []).some((item) => item?.id === cvdType.id))
            typeSelect.vm.$emit('update:modelValue', cvdType)
            await flushPromises()
            return wrapper
        }

        async function openCvdReport(detail = {}, status = statusOf(CERT)) {
            const analyzeApi = await import('@/api/analyze')
            vi.mocked(analyzeApi.getCvdStatus).mockResolvedValue({ data: status })
            vi.mocked(analyzeApi.getReportItem).mockResolvedValue({
                data: {
                    ...reportDetail('en'),
                    report_item_type_id: 6,
                    gcve_id: 'GCVE-65535-2026-0001',
                    attributes: [],
                    ...ofCert(),
                    ...detail
                }
            })
            mockAnalyzeStore.getReportItemTypes = { items: [reportType, cvdType] }
            const wrapper = mountWithPlugins(NewReportItem, {
                props: { showButton: false },
                global: { stubs: { VDialog: VDialogStub, VOverlay: VOverlayStub } }
            })
            await flushPromises()
            await wrapper.vm.showDetail({ id: 7, modify: true })
            await flushPromises()
            return { wrapper, analyzeApi }
        }

        it('is written in English, which cannot be changed', async () => {
            const wrapper = await startCvdReport()
            const language = wrapper.findComponent('[data-test="report-source-language"]')

            expect(language.props('modelValue')).toBe('en')
            expect(language.props('disabled')).toBe(true)
            expect(wrapper.find('[data-test="report-item-cvd-unset"]').exists()).toBe(false)
        })

        it("warns while none of the author's organizations can publish it: no GNA number and no CVE Services account", async () => {
            const wrapper = await startCvdReport(statusOf())

            expect(wrapper.find('[data-test="report-item-cvd-unset"]').exists()).toBe(true)
        })

        it('needs only one of them', async () => {
            const wrapper = await startCvdReport(statusOf(PARTNER))

            expect(wrapper.find('[data-test="report-item-cvd-unset"]').exists()).toBe(false)
        })

        it("belongs to the author's only organization that can publish it", async () => {
            const wrapper = await startCvdReport()

            expect(wrapper.find('[data-test="report-item-cvd-organization"]').exists()).toBe(false)
            expect(wrapper.vm.cvd_organization_id).toBe(3)
        })

        it('is given one of them by a member of several', async () => {
            const wrapper = await startCvdReport(statusOf(CERT, PARTNER))
            const picker = wrapper.findComponent('[data-test="report-item-cvd-organization"]')

            expect(picker.props('items').map((item) => [item.title, item.value])).toEqual([
                ['CERT (GNA 65535)', 3],
                ['Partner CERT', 4]
            ])
            expect(wrapper.vm.cvd_organization_id).toBeNull()
        })

        it('names its organization, fixed once it holds an identifier', async () => {
            const { wrapper } = await openCvdReport({}, statusOf(CERT, PARTNER))

            expect(wrapper.get('[data-test="report-item-cvd-organization-chip"]').text()).toBe('CERT')
            expect(wrapper.find('[data-test="report-item-cvd-organization"]').exists()).toBe(false)
        })

        it("moves to another of the author's organizations while it holds no identifier", async () => {
            const { wrapper, analyzeApi } = await openCvdReport({ gcve_id: null }, statusOf(CERT, PARTNER))
            vi.mocked(analyzeApi.updateReportItem).mockResolvedValue({ data: { cvd_organization: PARTNER } })

            wrapper.findComponent('[data-test="report-item-cvd-organization"]').vm.$emit('update:modelValue', 4)
            await flushPromises()

            expect(analyzeApi.updateReportItem).toHaveBeenCalledWith(7, { update: true, organization_id: 4 })
        })

        it('shows the GCVE identifier it was given', async () => {
            const { wrapper } = await openCvdReport()

            expect(wrapper.get('[data-test="report-item-gcve-id"]').text()).toBe('GCVE-65535-2026-0001')
        })

        it('reserves a CVE ID through CVE Services and shows it', async () => {
            const { wrapper, analyzeApi } = await openCvdReport()
            const reserved = { cve_id: 'CVE-2026-1234', state: 'RESERVED' }
            vi.mocked(analyzeApi.reserveCveId).mockResolvedValue({ data: { cve_status: reserved } })
            // The report as core holds it afterwards, read again to show the CVE field.
            vi.mocked(analyzeApi.getReportItem).mockResolvedValue({
                data: { ...reportDetail('en'), report_item_type_id: 6, attributes: [], cve_status: reserved, ...ofCert() }
            })

            await wrapper.get('[data-test="report-item-reserve-cve"]').trigger('click')
            await flushPromises()

            expect(analyzeApi.reserveCveId).toHaveBeenCalledWith(7)
            expect(wrapper.get('[data-test="report-item-cve-id"]').text()).toContain('CVE-2026-1234')
            expect(wrapper.get('[data-test="report-item-cve-id"]').text()).toContain('Reserved')
            expect(wrapper.find('[data-test="report-item-reserve-cve"]').exists()).toBe(false)
        })

        it("offers no reservation without the CVE Services account of the report's organization", async () => {
            const { wrapper } = await openCvdReport(ofCert({ cna_configured: false }))

            expect(wrapper.find('[data-test="report-item-reserve-cve"]').exists()).toBe(false)
        })

        it('shows a published record that lags behind the report, and what CVE Services said', async () => {
            const { wrapper } = await openCvdReport({
                cve_status: {
                    cve_id: 'CVE-2026-1234',
                    state: 'PUBLISHED',
                    out_of_date: true,
                    last_error: 'CVE JSON schema validation FAILED.'
                }
            })
            const chip = wrapper.get('[data-test="report-item-cve-id"]')

            expect(chip.text()).toContain('Out of date')
            expect(chip.attributes('title')).toBe('CVE JSON schema validation FAILED.')
        })

        it('rejects the CVE ID with the reason given', async () => {
            const { wrapper, analyzeApi } = await openCvdReport({ cve_status: { cve_id: 'CVE-2026-1234', state: 'RESERVED' } })
            const rejected = { cve_id: 'CVE-2026-1234', state: 'REJECTED', rejected_reason: 'Not a vulnerability' }
            vi.mocked(analyzeApi.rejectCveId).mockResolvedValue({ data: { cve_status: rejected } })
            vi.mocked(analyzeApi.getReportItem).mockResolvedValue({
                data: { ...reportDetail('en'), report_item_type_id: 6, attributes: [], cve_status: rejected, ...ofCert() }
            })

            await wrapper.get('[data-test="report-item-reject-cve"]').trigger('click')
            await flushPromises()
            const confirm = wrapper.get('[data-test="report-item-reject-cve-confirm"]')
            expect(confirm.attributes('disabled')).toBeDefined()
            await wrapper.get('[data-test="report-item-reject-cve-reason"] textarea').setValue('Not a vulnerability')
            await confirm.trigger('click')
            await flushPromises()

            expect(analyzeApi.rejectCveId).toHaveBeenCalledWith(7, 'Not a vulnerability')
            expect(wrapper.get('[data-test="report-item-cve-id"]').text()).toContain('Rejected')
            // A rejected ID frees the report for another one.
            expect(wrapper.find('[data-test="report-item-reserve-cve"]').exists()).toBe(true)
        })

        it('says what CVE Services refused', async () => {
            const { wrapper, analyzeApi } = await openCvdReport()
            vi.mocked(analyzeApi.reserveCveId).mockRejectedValue({
                response: { status: 502, data: { error: 'CVE Services refused the credentials' } }
            })
            const notifications = []
            const listener = (event) => notifications.push(event.detail)
            window.addEventListener('notification', listener)

            await wrapper.get('[data-test="report-item-reserve-cve"]').trigger('click')
            await flushPromises()
            window.removeEventListener('notification', listener)

            expect(notifications).toContainEqual({ type: 'error', message: 'CVE Services refused the credentials' })
            expect(wrapper.find('[data-test="report-item-cve-id"]').exists()).toBe(false)
        })
    })
})
