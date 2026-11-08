import { flushPromises } from '@vue/test-utils'
import { defineComponent, h } from 'vue'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mountWithPlugins } from '../helpers/mount-helpers'
import NewReportType from '@/components/config/reports/NewReportType.vue'
import NewProductPreset from '@/components/config/product-presets/NewProductPreset.vue'
import CardCompact from '@/components/common/CardCompact.vue'
import { getProductPresetOptions, updateProductPreset, updateReportItemType } from '@/api/config'

// The CVD Report type and the GCVE Advisory preset ship with Taranis: they can only be
// switched on or off, so their dialogs show every other control disabled.

vi.mock('@/api/config', () => ({
    getAllAttributes: vi.fn(() => Promise.resolve({ data: { items: [] } })),
    getAllAiProviders: vi.fn(() => Promise.resolve({ data: { items: [] } })),
    createNewReportItemType: vi.fn(),
    updateReportItemType: vi.fn(() => Promise.resolve({ data: {} })),
    translateReportItemTypeLabels: vi.fn(),
    getGlossary: vi.fn(() => Promise.resolve({ data: { items: [], languages: [] } })),
    createGlossaryEntry: vi.fn(),
    updateGlossaryEntry: vi.fn(),
    deleteGlossaryEntry: vi.fn(),
    createProductPreset: vi.fn(),
    updateProductPreset: vi.fn(() => Promise.resolve({ data: { id: 7 } })),
    getProductPresetOptions: vi.fn()
}))

vi.mock('@/composables/useAuth', () => ({
    useAuth: () => ({ checkPermission: () => true })
}))

const VDialogStub = { name: 'VDialog', template: '<div><slot name="activator" :props="{}" /><slot /></div>' }
const VFormStub = defineComponent({
    name: 'VForm',
    props: { disabled: Boolean },
    setup(_, { expose, slots }) {
        expose({ validate: () => Promise.resolve({ valid: true }), reset: () => {}, resetValidation: () => {} })
        return () => h('form', slots['default']?.())
    }
})

const CVD_TYPE = {
    id: 3,
    title: 'CVD Report',
    description: 'Coordinated Vulnerability Disclosure, published as a GCVE record',
    system_key: 'cvd',
    locked: true,
    enabled: true,
    languages: [],
    label_language: 'en',
    attribute_groups: [{ id: 1, title: 'Record', description: '', section_title: '', index: 0, attribute_group_items: [] }]
}

const GCVE_PRESET = {
    id: 7,
    name: 'GCVE Advisory',
    description: 'CVD Reports published as GCVE records',
    system_key: 'gcve',
    locked: true,
    enabled: true,
    public_web_enabled: true,
    public_web_ids: [1],
    deliveries: []
}

const mounted = []
const mountDialog = async (component, editItem) => {
    const wrapper = mountWithPlugins(component, {
        props: { editItem },
        global: { stubs: { VDialog: VDialogStub, VForm: VFormStub, UnsavedChangesDialog: true } }
    })
    mounted.push(wrapper)
    await flushPromises()
    return wrapper
}

// The inputs other than the on/off switch, and whether each is disabled. Left out: the icon
// picker's search and the attribute table's add dialog (both only open from a disabled button,
// rendered here because the stubs render every slot), and the hidden inputs of selects.
const otherInputs = (wrapper, enabledSwitch) => {
    const skipped = [
        wrapper.get(`[data-test="${enabledSwitch}"]`).element,
        ...wrapper.findAll('[data-test$="-icon"]').map((picker) => picker.element),
        ...wrapper.findAllComponents({ name: 'AttributeTable' }).map((table) => table.element)
    ]
    return wrapper
        .findAll('input, textarea')
        .filter((input) => input.element.type !== 'hidden' && !skipped.some((element) => element.contains(input.element)))
        .map((input) => input.element.disabled)
}

describe('shipped report type', () => {
    beforeEach(() => vi.clearAllMocks())
    afterEach(() => mounted.splice(0).forEach((wrapper) => wrapper.unmount()))

    it('says it is shipped, and leaves only its switch to change', async () => {
        const wrapper = await mountDialog(NewReportType, CVD_TYPE)

        expect(wrapper.find('[data-test="report-type-locked"]').exists()).toBe(true)
        expect(wrapper.get('[data-test="report-type-enabled"] input').element.disabled).toBe(false)
        const disabled = otherInputs(wrapper, 'report-type-enabled')
        expect(disabled.length).toBeGreaterThan(3)
        expect(disabled.every(Boolean)).toBe(true)
        expect(wrapper.findComponent({ name: 'MdiIconPicker' }).props('disabled')).toBe(true)
        expect(wrapper.findComponent({ name: 'AttributeTable' }).props('disabled')).toBe(true)
    })

    it('saves it switched off', async () => {
        const wrapper = await mountDialog(NewReportType, CVD_TYPE)

        await wrapper.get('[data-test="report-type-enabled"] input').setValue(false)
        expect(await wrapper.vm.persist()).toBe(true)

        expect(vi.mocked(updateReportItemType).mock.calls[0][0]).toMatchObject({ id: 3, enabled: false })
    })

    it('leaves a type of ones own editable', async () => {
        const wrapper = await mountDialog(NewReportType, { ...CVD_TYPE, system_key: null, locked: false, title: 'Advisory' })

        expect(wrapper.find('[data-test="report-type-locked"]').exists()).toBe(false)
        expect(otherInputs(wrapper, 'report-type-enabled').some((disabled) => !disabled)).toBe(true)
    })
})

describe('shipped product preset', () => {
    beforeEach(() => {
        vi.clearAllMocks()
        vi.mocked(getProductPresetOptions).mockResolvedValue({
            data: { formats: [], channels: [], public_webs: [{ id: 1, name: 'Example web' }] }
        })
    })
    afterEach(() => mounted.splice(0).forEach((wrapper) => wrapper.unmount()))

    it('says it is shipped, and leaves only its switch to change', async () => {
        const wrapper = await mountDialog(NewProductPreset, GCVE_PRESET)

        expect(wrapper.find('[data-test="product-preset-locked"]').exists()).toBe(true)
        expect(wrapper.get('[data-test="product-preset-enabled"] input').element.disabled).toBe(false)
        const disabled = otherInputs(wrapper, 'product-preset-enabled')
        expect(disabled.length).toBeGreaterThan(2)
        expect(disabled.every(Boolean)).toBe(true)
        expect(wrapper.find('[data-test="add-format"]').attributes('disabled')).toBeDefined()
        expect(wrapper.findComponent({ name: 'MdiIconPicker' }).props('disabled')).toBe(true)
    })

    it('saves it switched off, although it delivers nowhere', async () => {
        const wrapper = await mountDialog(NewProductPreset, GCVE_PRESET)

        await wrapper.get('[data-test="product-preset-enabled"] input').setValue(false)
        expect(await wrapper.vm.persist()).toBe(true)

        expect(vi.mocked(updateProductPreset).mock.calls[0][0]).toMatchObject({ id: 7, enabled: false })
    })
})

describe('shipped cards', () => {
    const mountCard = (card) =>
        mountWithPlugins(CardCompact, {
            props: { card },
            global: { stubs: { ConfirmationDialog: true } }
        })

    it('marks a shipped card, and one switched off, and offers no delete', () => {
        const wrapper = mountCard({ id: 3, title: 'CVD Report', locked: true, enabled: false })

        expect(wrapper.find('[data-test="card-locked"]').exists()).toBe(true)
        expect(wrapper.get('[data-test="card-disabled"]').text()).toBe('Switched off')
        const remove = wrapper.findComponent({ name: 'ActionButton' })
        if (remove.exists()) expect(remove.props('disabled')).toBe(true)
    })

    it('marks neither on a card of ones own', () => {
        const wrapper = mountCard({ id: 4, title: 'Advisory' })

        expect(wrapper.find('[data-test="card-locked"]').exists()).toBe(false)
        expect(wrapper.find('[data-test="card-disabled"]').exists()).toBe(false)
    })
})
