import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { flushPromises } from '@vue/test-utils'
import { mountWithPlugins } from '../helpers/mount-helpers'
import ReportItemSelector from '@/components/publish/ReportItemSelector.vue'

/**
 * The REPORT_SELECTOR_READ_ONLY app setting decides whether a report item opened from the
 * product's report-item selector is editable or view-only. The selector passes it down to
 * NewReportItem as `read-only`, so asserting on that prop covers the whole wiring.
 */

const { mockSettings } = vi.hoisted(() => ({ mockSettings: { value: [] } }))

vi.mock('@/stores/settings', () => ({
    useSettingsStore: () => ({
        // Both the settings service (getSettingBoolean) and the component read the store.
        getSettings: mockSettings.value,
        getSetting: (key) => mockSettings.value.find((entry) => entry.key === key)
    })
}))

vi.mock('@/stores/analyze', () => ({
    useAnalyzeStore: () => ({
        getReportItemTypes: { items: [] },
        getSelectionReport: [],
        loadReportItemTypes: vi.fn().mockResolvedValue({}),
        multiSelectReport: vi.fn(),
        selectReport: vi.fn()
    })
}))

vi.mock('@/api/state', () => ({
    getEntityTypeStates: vi.fn().mockResolvedValue({ data: { states: [] } })
}))

const NewReportItemStub = {
    name: 'NewReportItem',
    props: ['showButton', 'readOnly'],
    template: '<div class="new-report-item-stub" />'
}

const stubs = {
    ContentDataAnalyze: { name: 'ContentDataAnalyze', template: '<div />' },
    ToolbarFilterAnalyze: { name: 'ToolbarFilterAnalyze', template: '<div />' },
    CardAnalyze: { name: 'CardAnalyze', template: '<div />' },
    NewReportItem: NewReportItemStub
}

async function mountSelector() {
    const wrapper = mountWithPlugins(ReportItemSelector, { global: { stubs } })
    await flushPromises()
    return wrapper
}

const readOnlyProp = (wrapper) => wrapper.findComponent(NewReportItemStub).props('readOnly')

describe('ReportItemSelector — REPORT_SELECTOR_READ_ONLY', () => {
    beforeEach(() => {
        setActivePinia(createPinia())
        vi.clearAllMocks()
        mockSettings.value = []
    })

    it('opens report items read-only when the setting is true', async () => {
        mockSettings.value = [{ key: 'REPORT_SELECTOR_READ_ONLY', value: 'true' }]
        expect(readOnlyProp(await mountSelector())).toBe(true)
    })

    it('opens report items editable when the setting is false', async () => {
        mockSettings.value = [{ key: 'REPORT_SELECTOR_READ_ONLY', value: 'false' }]
        expect(readOnlyProp(await mountSelector())).toBe(false)
    })

    it('falls back to read-only when the setting is missing', async () => {
        mockSettings.value = [{ key: 'SOME_OTHER_SETTING', value: 'false' }]
        expect(readOnlyProp(await mountSelector())).toBe(true)
    })
})
