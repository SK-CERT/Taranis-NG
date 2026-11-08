import { describe, it, expect, beforeEach, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { mountWithPlugins } from '../helpers/mount-helpers'
import NewReportItem from '@/components/analyze/NewReportItem.vue'

/**
 * A CVD Report is filled from a CVE's published record: only the fields that hold nothing. A
 * report being written is filled in the form; a saved one by core, and the form reloads it.
 */

const mockAnalyzeStore = {
    getReportItemTypes: { items: [] },
    loadReportItemTypes: vi.fn()
}

const mockSettingsStore = {
    getSettings: [{ key: 'CONTENT_DEFAULT_LANGUAGE', value: 'en', options: JSON.stringify([{ id: 'en', txt: 'English' }]) }],
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
vi.mock('@/api/tags', () => ({ getEntityTypeTags: vi.fn(() => Promise.resolve({ data: { tags: [] } })) }))

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
    getCvdStatus: vi.fn(() => Promise.resolve({ data: { organizations: [CERT], gna_configured: true, cna_configured: false } })),
    reserveCveId: vi.fn(),
    rejectCveId: vi.fn(),
    getCveRecordCvd: vi.fn(),
    fillCvdFromCve: vi.fn()
}))

const VDialogStub = { name: 'VDialog', props: ['modelValue'], template: '<div><slot /></div>' }
const VOverlayStub = { name: 'VOverlay', props: ['modelValue'], template: '<div><slot /></div>' }

const CERT = { id: 3, name: 'CERT', gna_id: 65535, gna_configured: true, cna_configured: false }
const CNA_ONLY = { id: 4, name: 'Partner CERT', gna_id: null, gna_configured: false, cna_configured: true }
const statusOf = (...organizations) => ({
    organizations,
    gna_configured: organizations.some((organization) => organization.gna_configured),
    cna_configured: organizations.some((organization) => organization.cna_configured)
})
const CVE_ID = 'CVE-2026-1000042'
const item = (id, title, type, min = 0) => ({ id, title, min_occurrence: min, max_occurrence: 1000, attribute: { type } })
const cvdType = {
    id: 6,
    title: 'CVD Report',
    system_key: 'cvd',
    locked: true,
    enabled: true,
    languages: [],
    attribute_groups: [
        {
            id: 1,
            title: 'Record',
            attribute_group_items: [item(30, 'Record type', 'RADIO', 1), item(31, 'CVE', 'CVE'), item(36, 'Related records', 'RELATIONSHIP')]
        },
        {
            id: 2,
            title: 'Vulnerability',
            attribute_group_items: [item(32, 'Description', 'RICH_TEXT', 1), item(33, 'CWE', 'CWE'), item(34, 'Solutions', 'RICH_TEXT')]
        },
        { id: 3, title: 'Resources', attribute_group_items: [item(35, 'References', 'REFERENCE', 1)] }
    ]
}
const otherType = { id: 5, title: 'Vulnerability', languages: [], attribute_groups: [] }

const IMPORTED = {
    cve_id: CVE_ID,
    title: 'Login bypass in Example Portal',
    fields: {
        cve: [{ value: CVE_ID, value_description: null }],
        description: [{ value: '<p>The portal lets anyone log in.</p>', value_description: null }],
        cwe: [{ value: '287', value_description: 'Improper Authentication' }],
        solutions: [{ value: '<p>Update to 1.4.2.</p>', value_description: null }],
        references: [
            { value: '{"url":"https://example.com/a"}', value_description: null },
            { value: '{"url":"https://example.com/b"}', value_description: null }
        ]
    },
    skipped: []
}

const notifications = []
window.addEventListener('notification', (event) => notifications.push(event.detail))

function mount() {
    return mountWithPlugins(NewReportItem, {
        props: { showButton: false },
        global: { stubs: { VDialog: VDialogStub, VOverlay: VOverlayStub } }
    })
}

async function startReport(type = cvdType) {
    const wrapper = mount()
    await flushPromises()
    wrapper.vm.openDialog([])
    await flushPromises()
    const typeSelect = wrapper
        .findAllComponents({ name: 'VCombobox' })
        .find((select) => (select.props('items') ?? []).some((entry) => entry?.id === type.id))
    typeSelect.vm.$emit('update:modelValue', type)
    await flushPromises()
    return wrapper
}

const values = (wrapper, title) =>
    wrapper.vm.attribute_groups.flatMap((group) => group.attribute_group_items).find((entry) => entry.attribute_group_item.title === title)
        .values

async function fill(wrapper, cveId) {
    await wrapper.find('[data-test="report-item-cvd-fill"]').trigger('click')
    if (cveId !== undefined) {
        wrapper.findComponent('[data-test="report-item-cvd-fill-cve"]').vm.$emit('update:modelValue', cveId)
        await flushPromises()
    }
    await wrapper.find('[data-test="report-item-cvd-fill-confirm"]').trigger('click')
    await flushPromises()
}

describe('NewReportItem filled from a CVE', () => {
    let analyzeApi

    beforeEach(async () => {
        vi.clearAllMocks()
        notifications.length = 0
        analyzeApi = await import('@/api/analyze')
        vi.mocked(analyzeApi.getCvdStatus).mockResolvedValue({ data: statusOf(CERT) })
        mockAnalyzeStore.getReportItemTypes = { items: [otherType, cvdType] }
        mockAnalyzeStore.loadReportItemTypes.mockResolvedValue({})
    })

    it('is offered for a CVD Report only', async () => {
        expect((await startReport(otherType)).find('[data-test="report-item-cvd-fill"]').exists()).toBe(false)
        expect((await startReport()).find('[data-test="report-item-cvd-fill"]').exists()).toBe(true)
    })

    it('fills the empty fields of a report being written, and keeps what it holds', async () => {
        vi.mocked(analyzeApi.getCveRecordCvd).mockResolvedValue({ data: IMPORTED })
        const wrapper = await startReport()
        // The required Description starts with an empty value; Solutions holds the analyst's text.
        const description = { id: -1, index: 0, value: '<p></p>', user: null }
        values(wrapper, 'Description').push(description)
        values(wrapper, 'Solutions').push({ id: -1, index: 0, value: '<p>Ours.</p>', user: null })

        await fill(wrapper, ' cve-2026-1000042 ')

        expect(analyzeApi.getCveRecordCvd).toHaveBeenCalledWith(CVE_ID)
        expect(analyzeApi.fillCvdFromCve).not.toHaveBeenCalled()
        expect(values(wrapper, 'Description')).toHaveLength(1)
        expect(values(wrapper, 'Description')[0].value).toBe('<p>The portal lets anyone log in.</p>')
        expect(values(wrapper, 'Solutions').map((value) => value.value)).toEqual(['<p>Ours.</p>'])
        expect(values(wrapper, 'CVE').map((value) => value.value)).toEqual([CVE_ID])
        expect(values(wrapper, 'CWE').map((value) => [value.value, value.value_description])).toEqual([['287', 'Improper Authentication']])
        const references = values(wrapper, 'References')
        expect(references.map((value) => value.value)).toEqual(['{"url":"https://example.com/a"}', '{"url":"https://example.com/b"}'])
        // Each new reference gets a citation key of its own.
        expect(new Set(references.map((value) => value.value_description)).size).toBe(2)
        expect(references.every((value) => /^[a-z0-9]{4,12}$/.test(value.value_description))).toBe(true)
        expect(wrapper.vm.report_item.title).toBe('Login bypass in Example Portal')
        expect(notifications.at(-1)).toEqual({
            type: 'success',
            loc: 'report_item.cvd_fill.done',
            params: { cve: CVE_ID, filled: 4, kept: 1, skipped: 0 }
        })
    })

    it('keeps a title the analyst wrote', async () => {
        vi.mocked(analyzeApi.getCveRecordCvd).mockResolvedValue({ data: IMPORTED })
        const wrapper = await startReport()
        wrapper.vm.report_item.title = 'Our title'

        await fill(wrapper, CVE_ID)

        expect(wrapper.vm.report_item.title).toBe('Our title')
    })

    it('fills a saved report through core and reloads it, from the CVE its field holds', async () => {
        vi.mocked(analyzeApi.getReportItem).mockResolvedValue({
            data: {
                id: 7,
                uuid: 'uuid-7',
                title: 'Login bypass',
                title_prefix: '',
                language: 'en',
                report_item_type_id: 6,
                state_id: null,
                news_item_aggregates: [],
                remote_report_items: [],
                translations: {},
                gcve_id: 'GCVE-65535-2026-0001',
                organization_id: 3,
                cvd_organization: CERT,
                attributes: [{ id: 41, attribute_group_item_id: 31, value: CVE_ID, translations: {} }]
            }
        })
        vi.mocked(analyzeApi.fillCvdFromCve).mockResolvedValue({
            data: { filled: ['Description', 'CWE'], kept: ['CVE'], skipped: ['CVSS: bad'] }
        })
        const wrapper = mount()
        await flushPromises()
        await wrapper.vm.showDetail({ id: 7, modify: true })
        await flushPromises()

        await wrapper.find('[data-test="report-item-cvd-fill"]').trigger('click')
        const field = wrapper.findComponent('[data-test="report-item-cvd-fill-cve"]')
        expect(field.props('modelValue')).toBe(CVE_ID)
        expect(field.props('readonly')).toBe(true)
        vi.mocked(analyzeApi.getReportItem).mockClear()
        await wrapper.find('[data-test="report-item-cvd-fill-confirm"]').trigger('click')
        await flushPromises()

        expect(analyzeApi.fillCvdFromCve).toHaveBeenCalledWith(7, CVE_ID)
        expect(analyzeApi.getCveRecordCvd).not.toHaveBeenCalled()
        expect(analyzeApi.getReportItem).toHaveBeenCalled()
        expect(notifications.at(-1)).toEqual({
            type: 'warning',
            loc: 'report_item.cvd_fill.done_skipped',
            params: { cve: CVE_ID, filled: 2, kept: 1, skipped: 1 }
        })
    })

    it('says why a CVE cannot fill the report', async () => {
        vi.mocked(analyzeApi.getCveRecordCvd).mockRejectedValue({
            response: { data: { error: 'CVE Services has no published record of CVE-2026-0001' } }
        })
        const wrapper = await startReport()

        await fill(wrapper, 'CVE-2026-0001')

        expect(notifications.at(-1)).toEqual({ type: 'error', message: 'CVE Services has no published record of CVE-2026-0001' })
        expect(values(wrapper, 'CVE')).toEqual([])
    })

    it('asks only for a CVE ID', async () => {
        const wrapper = await startReport()
        await wrapper.find('[data-test="report-item-cvd-fill"]').trigger('click')

        wrapper.findComponent('[data-test="report-item-cvd-fill-cve"]').vm.$emit('update:modelValue', 'GCVE-1-2026-0001')
        await flushPromises()

        expect(wrapper.findComponent('[data-test="report-item-cvd-fill-confirm"]').props('disabled')).toBe(true)
    })

    describe('its GCVE-only and CVE-only parts', () => {
        async function openSaved({ organization = CERT, recordType = 'advisory', cveStatus = null } = {}) {
            vi.mocked(analyzeApi.getReportItem).mockResolvedValue({
                data: {
                    id: 7,
                    uuid: 'uuid-7',
                    title: 'Login bypass',
                    title_prefix: '',
                    language: 'en',
                    report_item_type_id: 6,
                    state_id: null,
                    news_item_aggregates: [],
                    remote_report_items: [],
                    translations: {},
                    gcve_id: organization.gna_configured ? 'GCVE-65535-2026-0001' : null,
                    organization_id: organization.id,
                    cvd_organization: organization,
                    cve_status: cveStatus,
                    attributes: [{ id: 40, attribute_group_item_id: 30, value: recordType, translations: {} }]
                }
            })
            vi.mocked(analyzeApi.getCvdStatus).mockResolvedValue({ data: statusOf(organization) })
            const wrapper = mount()
            await flushPromises()
            await wrapper.vm.showDetail({ id: 7, modify: true })
            await flushPromises()
            return wrapper
        }
        const shown = (wrapper, fieldId) => wrapper.find(`[data-field-id="${fieldId}"]`).element.style.display !== 'none'

        it('marks the GCVE-only fields for an organization with a GNA', async () => {
            const wrapper = await startReport()

            expect(wrapper.findAll('[data-test="report-item-gcve-only"]')).toHaveLength(2)
            expect([shown(wrapper, 30), shown(wrapper, 36), shown(wrapper, 31)]).toEqual([true, true, true])
        })

        it('hides them from an organization with only a CNA account', async () => {
            vi.mocked(analyzeApi.getCvdStatus).mockResolvedValue({ data: statusOf(CNA_ONLY) })
            const wrapper = await startReport()

            // Record type and Related records are the GCVE record's; the CVE field feeds both records.
            expect([shown(wrapper, 30), shown(wrapper, 36), shown(wrapper, 31)]).toEqual([false, false, true])
            const saved = await openSaved({ organization: CNA_ONLY })
            expect([shown(saved, 30), shown(saved, 36), shown(saved, 31)]).toEqual([false, false, true])
        })

        it('offers a CVE ID for an advisory only', async () => {
            const both = { ...CERT, cna_configured: true }

            expect((await openSaved({ organization: both })).find('[data-test="report-item-reserve-cve"]').exists()).toBe(true)
            expect(
                (await openSaved({ organization: both, recordType: 'comment' })).find('[data-test="report-item-reserve-cve"]').exists()
            ).toBe(false)
        })

        it('offers the CVE actions to an organization with a CNA account only', async () => {
            const reserved = { cve_id: 'CVE-2026-1234', state: 'RESERVED' }

            const gnaOnly = await openSaved({ cveStatus: reserved })
            expect(gnaOnly.find('[data-test="report-item-reserve-cve"]').exists()).toBe(false)
            expect(gnaOnly.find('[data-test="report-item-reject-cve"]').exists()).toBe(false)

            const cna = await openSaved({ organization: { ...CERT, cna_configured: true }, cveStatus: reserved })
            expect(cna.find('[data-test="report-item-reject-cve"]').exists()).toBe(true)
        })
    })
})
