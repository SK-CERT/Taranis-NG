import { describe, it, expect, beforeEach, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { mountWithPlugins } from '../helpers/mount-helpers'
import NewReportItem from '@/components/analyze/NewReportItem.vue'

/**
 * An attribute whose max_occurrence is 0 holds no values: the report form shows its name and
 * nothing else — no input, no add button, and no expand chevron leading to an empty panel.
 */

const mockCheckPermission = vi.fn(() => true)
const mockGetUserId = vi.fn(() => 99)

const mockAnalyzeStore = {
    getReportItemTypes: { items: [] },
    loadReportItemTypes: vi.fn()
}

const mockSettingsStore = {
    getSetting: vi.fn()
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
    aiGenerate: vi.fn()
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

const EDITABLE_TITLE = 'Editable attribute'
const LABEL_ONLY_TITLE = 'Label only attribute'

// A report type with one ordinary attribute and one label-only attribute (max_occurrence 0).
function makeReportType() {
    return {
        id: 5,
        title: 'Report Type',
        attribute_groups: [
            {
                id: 1,
                title: 'Group',
                attribute_group_items: [
                    {
                        id: 11,
                        title: EDITABLE_TITLE,
                        min_occurrence: 1,
                        max_occurrence: 1,
                        attribute: { type: 'STRING' }
                    },
                    {
                        id: 12,
                        title: LABEL_ONLY_TITLE,
                        min_occurrence: 0,
                        max_occurrence: 0,
                        attribute: { type: 'RADIO' }
                    }
                ]
            }
        ]
    }
}

describe('NewReportItem — label-only attributes (max_occurrence 0)', () => {
    let analyzeApi
    let stateApi

    beforeEach(async () => {
        vi.clearAllMocks()
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
                title_prefix: 'Prefix',
                report_item_type_id: 5,
                state_id: 1,
                news_item_aggregates: [],
                remote_report_items: [],
                attributes: []
            }
        })
        vi.mocked(analyzeApi.getReportItemLocks).mockResolvedValue({ data: {} })
    })

    async function mountOpenedEditor() {
        const wrapper = mountWithPlugins(NewReportItem, {
            props: { showButton: false },
            global: { stubs: { VDialog: VDialogStub, VOverlay: VOverlayStub } }
        })
        await flushPromises()
        await wrapper.vm.showDetail({ id: 7, modify: true })
        await flushPromises()
        return wrapper
    }

    // Each attribute is an inner ".item-panel"; the outer panel is the attribute *group*.
    const panelFor = (wrapper, title) =>
        wrapper
            .findAllComponents({ name: 'VExpansionPanel' })
            .filter((panel) => panel.classes().includes('item-panel'))
            .find((panel) => panel.text().includes(title))

    it('renders the attribute name but no interactive part for a label-only attribute', async () => {
        const wrapper = await mountOpenedEditor()

        const panel = panelFor(wrapper, LABEL_ONLY_TITLE)
        expect(panel).toBeDefined()
        // The name is still shown...
        expect(panel.text()).toContain(LABEL_ONLY_TITLE)
        // ...but nothing to edit, and no chevron opening onto an empty body.
        expect(panel.find('.attribute-container-stub').exists()).toBe(false)
        expect(panel.props('hideActions')).toBe(true)
        expect(panel.props('readonly')).toBe(true)
    })

    it('still renders the interactive part for an ordinary attribute', async () => {
        const wrapper = await mountOpenedEditor()

        const panel = panelFor(wrapper, EDITABLE_TITLE)
        expect(panel).toBeDefined()
        expect(panel.find('.attribute-container-stub').exists()).toBe(true)
        expect(panel.props('hideActions')).toBe(false)
        expect(panel.props('readonly')).toBe(false)
    })

    it('renders exactly one attribute editor for the two configured attributes', async () => {
        const wrapper = await mountOpenedEditor()
        expect(wrapper.findAll('.attribute-container-stub')).toHaveLength(1)
    })
})
