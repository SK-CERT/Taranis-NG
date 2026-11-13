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
        getSetting: (key, defValue = '') => {
            const setting = mockSettings.value.find((entry) => entry.key === key)
            return setting ? setting.value : defValue
        },
        getSettingBoolean: (key, defValue = false) => {
            const setting = mockSettings.value.find((entry) => entry.key === key)
            const value = setting ? setting.value : defValue ? 'true' : 'false'
            return value.toLowerCase().trim() === 'true'
        }
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
    CardAnalyze: { name: 'CardAnalyze', props: ['card', 'showRemoveAction'], template: '<div class="card-stub">{{ card.id }}</div>' },
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

describe('ReportItemSelector — report order', () => {
    const reports = () => [
        { id: 11, title: 'First' },
        { id: 12, title: 'Second' },
        { id: 13, title: 'Third' }
    ]

    async function mountWith(props) {
        const wrapper = mountWithPlugins(ReportItemSelector, { props, global: { stubs } })
        await flushPromises()
        return wrapper
    }

    const shown = (wrapper) => wrapper.findAll('.card-stub').map((card) => Number(card.text()))
    const handedOn = (wrapper) =>
        wrapper
            .emitted('items-changed')
            .at(-1)[0]
            .map((item) => item.id)
    const buttons = (wrapper, direction) => wrapper.findAll(`[data-test="report-move-${direction}"]`)

    beforeEach(() => {
        setActivePinia(createPinia())
        vi.clearAllMocks()
        mockSettings.value = []
    })

    it('moves a report up and down and hands the new order on', async () => {
        const wrapper = await mountWith({ values: reports(), modify: true })

        await buttons(wrapper, 'up')[2].trigger('click')
        expect(handedOn(wrapper)).toEqual([11, 13, 12])
        expect(shown(wrapper)).toEqual([11, 13, 12])

        await buttons(wrapper, 'down')[0].trigger('click')
        expect(handedOn(wrapper)).toEqual([13, 11, 12])
        expect(shown(wrapper)).toEqual([13, 11, 12])
    })

    it('cannot move the first report up or the last one down', async () => {
        const wrapper = await mountWith({ values: reports(), modify: true })

        expect(buttons(wrapper, 'up').map((button) => button.attributes('disabled') !== undefined)).toEqual([true, false, false])
        expect(buttons(wrapper, 'down').map((button) => button.attributes('disabled') !== undefined)).toEqual([false, false, true])
    })

    it('puts a dragged report where it is dropped', async () => {
        const wrapper = await mountWith({ values: reports(), modify: true })
        const rows = wrapper.findAll('[data-test="report-order-row"]')
        const dataTransfer = { setData: vi.fn(), effectAllowed: '', dropEffect: '' }

        await rows[0].find('[data-test="report-drag-handle"]').trigger('dragstart', { dataTransfer })
        await rows[2].trigger('dragover', { dataTransfer })
        await rows[2].trigger('drop')

        expect(handedOn(wrapper)).toEqual([12, 13, 11])
    })

    it('offers no reordering to whoever may not change the product, nor for a single report', async () => {
        const readOnly = await mountWith({ values: reports(), modify: false })
        expect(readOnly.find('[data-test="report-drag-handle"]').exists()).toBe(false)
        expect(shown(readOnly)).toEqual([11, 12, 13])

        const single = await mountWith({ values: reports().slice(0, 1), modify: true })
        expect(buttons(single, 'up')).toHaveLength(0)
    })
})
