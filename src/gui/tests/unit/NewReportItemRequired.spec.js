import { describe, it, expect, beforeEach, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { mountWithPlugins } from '../helpers/mount-helpers'
import NewReportItem from '@/components/analyze/NewReportItem.vue'

/**
 * A field that needs at least one value (min occurrence 1 or more) is required: the form marks it,
 * frames it while it is empty and lists the empty ones at the top. Nothing is blocked.
 */

const mockCheckPermission = vi.fn(() => true)
const mockGetUserId = vi.fn(() => 99)

const mockAnalyzeStore = {
    getReportItemTypes: { items: [] },
    loadReportItemTypes: vi.fn()
}

const mockSettingsStore = {
    getSetting: vi.fn(),
    getSettingBoolean: vi.fn()
}

vi.mock('vue-router', () => ({
    useRoute: () => ({ path: '/analyze', params: {} }),
    useRouter: () => ({ push: vi.fn(), replace: vi.fn() })
}))

vi.mock('@/composables/useAuth', () => ({
    useAuth: () => ({ checkPermission: mockCheckPermission, getUserId: mockGetUserId })
}))

vi.mock('@/stores/analyze', () => ({
    useAnalyzeStore: () => mockAnalyzeStore
}))

vi.mock('@/stores/settings', () => ({
    useSettingsStore: () => mockSettingsStore
}))

vi.mock('@/components/analyze/NewsItemSelector.vue', () => ({
    default: { name: 'NewsItemSelector', template: '<div />' }
}))

vi.mock('@/components/analyze/RemoteReportItemSelector.vue', () => ({
    default: { name: 'RemoteReportItemSelector', template: '<div />' }
}))

vi.mock('@/components/common/StateSelector.vue', () => ({
    default: { name: 'StateSelector', props: ['modelValue'], template: '<div />' }
}))

vi.mock('@/components/common/attribute/AttributeContainer.vue', () => ({
    default: {
        name: 'AttributeContainer',
        props: ['attributeItem', 'edit', 'modify', 'reportItemId', 'readOnly'],
        template: '<div class="attribute-container-stub" />'
    }
}))

vi.mock('@/api/state', () => ({
    getEntityTypeStates: vi.fn()
}))

vi.mock('@/api/analyze', () => ({
    createNewReportItem: vi.fn(),
    updateReportItem: vi.fn(),
    lockReportItem: vi.fn(),
    unlockReportItem: vi.fn(),
    holdLockReportItem: vi.fn(),
    getReportItem: vi.fn(),
    getReportItemData: vi.fn(),
    getReportItemLocks: vi.fn(),
    aiGenerate: vi.fn(),
    uploadAttachment: vi.fn()
}))

const VDialogStub = {
    name: 'VDialog',
    props: ['modelValue', 'fullscreen', 'persistent'],
    template: '<div class="v-dialog-stub"><slot /></div>'
}

const VOverlayStub = {
    name: 'VOverlay',
    props: ['modelValue'],
    template: '<div class="v-overlay-stub"><slot /></div>'
}

// A type with a filled required field, an empty required one and an optional one.
function makeReportType() {
    return {
        id: 5,
        title: 'Report Type',
        attribute_groups: [
            {
                id: 1,
                title: 'Group',
                attribute_group_items: [
                    { id: 11, title: 'Summary', description: '', min_occurrence: 1, max_occurrence: 1, attribute: { type: 'STRING' } },
                    { id: 12, title: 'Details', description: '', min_occurrence: 1, max_occurrence: 1, attribute: { type: 'RICH_TEXT' } },
                    { id: 13, title: 'Notes', description: '', min_occurrence: 0, max_occurrence: 5, attribute: { type: 'STRING' } }
                ]
            }
        ]
    }
}

describe('NewReportItem — required fields', () => {
    let analyzeApi
    let stateApi

    beforeEach(async () => {
        vi.clearAllMocks()
        localStorage.removeItem('TNGVericalView')
        mockCheckPermission.mockReturnValue(true)
        mockAnalyzeStore.getReportItemTypes = { items: [makeReportType()] }
        mockAnalyzeStore.loadReportItemTypes.mockResolvedValue({ data: mockAnalyzeStore.getReportItemTypes })
        mockSettingsStore.getSetting.mockReturnValue(null)

        analyzeApi = await import('@/api/analyze')
        stateApi = await import('@/api/state')

        vi.mocked(stateApi.getEntityTypeStates).mockResolvedValue({
            data: { states: [{ id: 1, is_default: true, icon: 'mdi-check', color: 'success' }] }
        })
        vi.mocked(analyzeApi.getReportItem).mockResolvedValue({
            data: {
                id: 7,
                uuid: 'uuid-7',
                title: 'Title',
                title_prefix: '',
                report_item_type_id: 5,
                state_id: 1,
                news_item_aggregates: [],
                remote_report_items: [],
                attributes: [
                    {
                        id: 21,
                        attribute_group_item_id: 11,
                        value: 'Filled in',
                        value_description: '',
                        user: { name: 'Analyst' },
                        locked: false
                    },
                    { id: 22, attribute_group_item_id: 12, value: '<p></p>', value_description: '', user: { name: 'Analyst' }, locked: false }
                ]
            }
        })
        vi.mocked(analyzeApi.getReportItemLocks).mockResolvedValue({ data: {} })
    })

    async function mountOpenedEditor(modify = true) {
        const wrapper = mountWithPlugins(NewReportItem, {
            props: { showButton: false },
            global: { stubs: { VDialog: VDialogStub, VOverlay: VOverlayStub } }
        })
        await flushPromises()
        await wrapper.vm.showDetail({ id: 7, modify })
        await flushPromises()
        return wrapper
    }

    const panelFor = (wrapper, title) =>
        wrapper
            .findAllComponents({ name: 'VExpansionPanel' })
            .filter((panel) => panel.classes().includes('item-panel'))
            .find((panel) => panel.text().includes(title))

    it('marks the required fields', async () => {
        const wrapper = await mountOpenedEditor()

        expect(panelFor(wrapper, 'Summary').find('[data-test="report-item-required-mark"]').exists()).toBe(true)
        expect(panelFor(wrapper, 'Details').find('[data-test="report-item-required-mark"]').exists()).toBe(true)
        expect(panelFor(wrapper, 'Notes').find('[data-test="report-item-required-mark"]').exists()).toBe(false)
    })

    it('frames and lists only the required fields that are still empty', async () => {
        const wrapper = await mountOpenedEditor()

        const reminder = wrapper.get('[data-test="report-item-required-missing"]')
        expect(reminder.findAll('[data-test="report-item-required-missing-field"]').map((chip) => chip.text())).toEqual(['Details'])
        expect(panelFor(wrapper, 'Details').classes()).toContain('item-panel--missing')
        expect(panelFor(wrapper, 'Summary').classes()).not.toContain('item-panel--missing')
    })

    it('reminds no one who cannot change the report', async () => {
        mockCheckPermission.mockReturnValue(false)
        const wrapper = await mountOpenedEditor(false)

        expect(wrapper.find('[data-test="report-item-required-missing"]').exists()).toBe(false)
    })
})
