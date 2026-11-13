import { flushPromises } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mountWithPlugins } from '../helpers/mount-helpers'
import NewProduct from '@/components/publish/NewProduct.vue'
import { getAllUserProductPresets } from '@/api/user'

// Closing the product dialog resets the form for the next product. It used to call VForm.reset(),
// which sets every field's model to null: the title became null, and with a product preset on
// the public web the web checkboxes' setter threw "can't access property length, e is null".
// The form here is Vuetify's own, so a reset of the models would show.

vi.mock('@/api/publish', () => ({
    createProduct: vi.fn(),
    updateProduct: vi.fn(() => Promise.resolve({})),
    publishProduct: vi.fn(),
    previewProduct: vi.fn(),
    getProductById: vi.fn(),
    translateProduct: vi.fn(),
    checkProductLanguage: vi.fn(() => Promise.resolve({ data: null }))
}))

vi.mock('@/api/user', () => ({
    getAllUserProductPresets: vi.fn()
}))

vi.mock('@/api/tags', () => ({
    getEntityTypeTags: vi.fn(() => Promise.resolve({ data: { tags: [] } }))
}))

vi.mock('@/api/state', () => ({
    getEntityTypeStates: vi.fn().mockResolvedValue({ data: { states: [] } })
}))

vi.mock('@/composables/useAuth', () => ({
    useAuth: () => ({ checkPermission: vi.fn().mockReturnValue(true) })
}))

vi.mock('@/utils/window', () => ({
    openBlankTabWithoutOpener: vi.fn(),
    navigateReservedTabOrCurrentWindow: vi.fn()
}))

const VDialogStub = { name: 'VDialog', template: '<div><slot /></div>' }

const PRESET = {
    id: 3,
    name: 'Cyberfeed',
    public_web_enabled: true,
    web_choices: [
        { id: 1, name: 'Cyberfeed' },
        { id: 2, name: 'Archive' }
    ],
    deliveries: []
}

const mounted = []

async function openProduct() {
    const wrapper = mountWithPlugins(NewProduct, {
        global: { stubs: { VDialog: VDialogStub, StateSelector: true, ReportItemSelector: true } }
    })
    mounted.push(wrapper)
    await flushPromises()
    wrapper.vm.openEditDialog(
        {
            id: 1009,
            title: 'Bulletin',
            description: 'Summary',
            product_preset_id: 3,
            state_id: undefined,
            report_items: [],
            links: [],
            language: 'sk',
            translations: {},
            public_web_ids: [],
            public_web_enabled: true
        },
        { modify: true, access: true }
    )
    await flushPromises()
    return wrapper
}

const webBoxes = (wrapper) => wrapper.findAllComponents({ name: 'VCheckbox' }).filter((box) => ['Cyberfeed', 'Archive'].includes(box.text()))

describe('NewProduct closing', () => {
    beforeEach(() => {
        vi.clearAllMocks()
        vi.mocked(getAllUserProductPresets).mockResolvedValue({ data: { items: [PRESET] } })
    })
    afterEach(() => {
        while (mounted.length) mounted.pop().unmount()
    })

    it('resets the form for the next product without nulling its fields', async () => {
        const errors = vi.spyOn(console, 'error')
        const wrapper = await openProduct()
        expect(webBoxes(wrapper)).toHaveLength(2)

        // What the dialog's after-leave runs.
        wrapper.vm.resetForm()
        await flushPromises()

        expect(errors).not.toHaveBeenCalled()
        expect(wrapper.vm.product).toMatchObject({ id: -1, title: '', description: '', public_web_ids: [], public_web_enabled: true })
    })

    it('takes no ticked web, however the checkboxes say so, as kept off the public web', async () => {
        const wrapper = await openProduct()

        wrapper.vm.shownWebIds = null
        await flushPromises()

        expect(wrapper.vm.product).toMatchObject({ public_web_enabled: false, public_web_ids: [] })
    })
})
