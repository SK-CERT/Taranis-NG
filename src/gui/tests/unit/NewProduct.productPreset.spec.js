import { flushPromises } from '@vue/test-utils'
import { defineComponent, h } from 'vue'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mountWithPlugins } from '../helpers/mount-helpers'
import NewProduct from '@/components/publish/NewProduct.vue'
import { createProduct, getProductById, previewProduct, publishProduct, updateProduct } from '@/api/publish'
import { getAllUserProductPresets } from '@/api/user'
import { getCvdStatus } from '@/api/analyze'
import { openBlankTabWithoutOpener } from '@/utils/window'

vi.mock('@/api/publish', () => ({
    createProduct: vi.fn(),
    updateProduct: vi.fn(),
    publishProduct: vi.fn(),
    previewProduct: vi.fn(),
    getProductById: vi.fn()
}))

vi.mock('@/api/analyze', async (importOriginal) => ({ ...(await importOriginal()), getCvdStatus: vi.fn() }))

vi.mock('@/api/user', () => ({
    getAllUserProductPresets: vi.fn()
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

const VDialogStub = {
    name: 'VDialog',
    template: '<div><slot /></div>'
}

const VFormStub = defineComponent({
    name: 'VForm',
    setup(_, { expose, slots }) {
        expose({ validate: () => Promise.resolve({ valid: true }) })
        return () => h('form', slots['default']?.())
    }
})

const VMenuStub = {
    name: 'VMenu',
    template: '<div class="menu-stub"><slot name="activator" :props="{}" /><slot /></div>'
}

const delivery = (id, formatId, formatTitle, channelId, channelName) => ({
    id,
    product_format_id: formatId,
    product_format_title: formatTitle,
    publishing_channel_id: channelId,
    publishing_channel_name: channelName
})

// JSON over SFTP, one e-mail to two addresses, a Mastodon post that is only previewed.
const ADVISORY = {
    id: 3,
    name: 'Vulnerability advisory',
    public_web_enabled: true,
    public_web_names: ['Cyberfeed'],
    deliveries: [
        delivery(11, 2, 'JSON', 'sftp', 'va2am dev'),
        delivery(12, 1, 'e-mail CZ', 'mail-1', 'VAMP'),
        delivery(13, 1, 'e-mail CZ', 'mail-2', 'jen JARA'),
        delivery(14, 4, 'Mastodon post CZ', null, null)
    ]
}

const PREVIEW_ONLY = {
    id: 4,
    name: 'Drafts',
    public_web_enabled: false,
    deliveries: [delivery(21, 4, 'Mastodon post CZ', null, null)]
}

// Unmounted after each test: a mounted dialog keeps listening for window events.
const mounted = []

function mountNewProduct() {
    const wrapper = mountWithPlugins(NewProduct, {
        global: {
            stubs: {
                VDialog: VDialogStub,
                VForm: VFormStub,
                VMenu: VMenuStub,
                ConfirmationDialog: true,
                StateSelector: true,
                ReportItemSelector: true
            }
        }
    })
    mounted.push(wrapper)
    return wrapper
}

async function chooseProductPreset(wrapper, productPreset) {
    wrapper.vm.selectedProductPreset = productPreset
    wrapper.vm.handleProductPresetChange()
    await flushPromises()
}

describe('NewProduct product presets', () => {
    const notifications = []
    const recordNotification = (event) => notifications.push(event.detail)

    beforeEach(() => {
        vi.clearAllMocks()
        notifications.length = 0
        window.addEventListener('notification', recordNotification)
        vi.mocked(getAllUserProductPresets).mockResolvedValue({ data: { items: [ADVISORY, PREVIEW_ONLY] } })
    })

    afterEach(() => {
        window.removeEventListener('notification', recordNotification)
        mounted.splice(0).forEach((wrapper) => wrapper.unmount())
    })

    it('offers the CVE Record and GCVE Advisory presets only where an organization can publish them', async () => {
        const GCVE_ADVISORY = { id: 8, name: 'GCVE Advisory', system_key: 'gcve', public_web_enabled: true, deliveries: [] }
        const CVE_RECORD = { id: 9, name: 'CVE Record', system_key: 'cve', public_web_enabled: false, deliveries: [] }
        vi.mocked(getAllUserProductPresets).mockResolvedValue({ data: { items: [ADVISORY, GCVE_ADVISORY, CVE_RECORD] } })
        // A GNA, no CNA account.
        vi.mocked(getCvdStatus).mockResolvedValue({ data: { organizations: [], gna_configured: true, cna_configured: false } })
        const wrapper = mountNewProduct()
        await flushPromises()

        expect(wrapper.vm.selectableProductPresets.map((preset) => preset.name)).toEqual(['Vulnerability advisory', 'GCVE Advisory'])

        // A product already made with it keeps it.
        wrapper.vm.product.product_preset_id = 9
        expect(wrapper.vm.selectableProductPresets.map((preset) => preset.name)).toContain('CVE Record')
    })

    it('ticks every channel of the chosen product preset and leaves format-only ones out', async () => {
        const wrapper = mountNewProduct()
        await flushPromises()

        await chooseProductPreset(wrapper, ADVISORY)

        expect(wrapper.vm.product.product_preset_id).toBe(3)
        expect(wrapper.vm.tickedDeliveryIds).toEqual([11, 12, 13])
        expect(wrapper.text()).toContain('JSON')
        expect(wrapper.text()).toContain('va2am dev')
        expect(wrapper.text()).toContain('jen JARA')
        expect(wrapper.text()).not.toContain('Mastodon post CZ →')
        expect(wrapper.vm.publicWebNote).toContain('Cyberfeed')
        expect(wrapper.vm.canPublish).toBe(true)
    })

    it('publishes to the ticked deliveries only', async () => {
        vi.mocked(publishProduct).mockResolvedValue({
            data: {
                overall_success: true,
                results: [
                    { delivery_id: 11, success: true },
                    { delivery_id: 13, success: true }
                ]
            }
        })
        const wrapper = mountNewProduct()
        await flushPromises()
        await chooseProductPreset(wrapper, ADVISORY)
        wrapper.vm.tickedDeliveryIds = [11, 13]

        await wrapper.vm.handlePublish()

        expect(publishProduct).toHaveBeenCalledOnce()
        const [product, deliveryIds] = vi.mocked(publishProduct).mock.calls[0]
        expect(product.product_preset_id).toBe(3)
        expect(product).not.toHaveProperty('product_format_id')
        expect(product.public_web_ids).toEqual([])
        expect(deliveryIds).toEqual([11, 13])
        expect(notifications).toEqual([{ type: 'success', loc: 'product.publish_successful' }])
    })

    it('names the deliveries that failed when the others went out', async () => {
        vi.mocked(publishProduct).mockRejectedValue({
            response: {
                status: 500,
                data: {
                    overall_success: false,
                    results: [
                        { delivery_id: 11, success: true },
                        { delivery_id: 12, success: false },
                        { delivery_id: 13, success: true }
                    ]
                }
            }
        })
        const wrapper = mountNewProduct()
        await flushPromises()
        await chooseProductPreset(wrapper, ADVISORY)

        await wrapper.vm.handlePublish()

        expect(notifications).toHaveLength(1)
        expect(notifications[0].loc).toBe('product.publish_failed_deliveries')
        expect(notifications[0].params.deliveries).toContain('VAMP')
        expect(notifications[0].params.deliveries).not.toContain('jen JARA')
        expect(wrapper.vm.showError).toBe(false)
    })

    it('names a ticked delivery core did not report, e.g. one an admin has since changed', async () => {
        vi.mocked(publishProduct).mockResolvedValue({
            data: {
                overall_success: true,
                results: [
                    { delivery_id: 11, success: true },
                    { delivery_id: 13, success: true }
                ]
            }
        })
        const wrapper = mountNewProduct()
        await flushPromises()
        await chooseProductPreset(wrapper, ADVISORY)

        await wrapper.vm.handlePublish()

        expect(notifications).toHaveLength(1)
        expect(notifications[0].loc).toBe('product.publish_failed_deliveries')
        expect(notifications[0].params.deliveries).toContain('VAMP')
        expect(notifications[0].params.deliveries).not.toContain('jen JARA')
    })

    it('refuses to publish with nothing ticked', async () => {
        const wrapper = mountNewProduct()
        await flushPromises()
        await chooseProductPreset(wrapper, ADVISORY)
        wrapper.vm.tickedDeliveryIds = []

        wrapper.vm.handlePublishConfirmation()

        expect(notifications).toEqual([{ type: 'error', loc: 'product.no_delivery_selected' }])
        expect(publishProduct).not.toHaveBeenCalled()
    })

    it('says a product preset without channels sends nowhere and offers no Publish', async () => {
        const wrapper = mountNewProduct()
        await flushPromises()

        await chooseProductPreset(wrapper, PREVIEW_ONLY)

        expect(wrapper.vm.canPublish).toBe(false)
        expect(wrapper.text()).toContain('This product sends to no channel yet')
        expect(wrapper.vm.publicWebNote).toBe('')
    })

    it('previews the format picked from the menu when the product preset has several', async () => {
        vi.mocked(openBlankTabWithoutOpener).mockReturnValue({ close: vi.fn() })
        vi.mocked(previewProduct).mockResolvedValue({ data: { token: 'ticket' } })
        const wrapper = mountNewProduct()
        await flushPromises()
        await chooseProductPreset(wrapper, ADVISORY)

        expect(wrapper.vm.formats.map((format) => format.title)).toEqual(['JSON', 'e-mail CZ', 'Mastodon post CZ'])
        const items = wrapper.findAll('[data-test="preview-formats"] .v-list-item')
        expect(items.map((item) => item.text())).toEqual(['JSON', 'e-mail CZ', 'Mastodon post CZ'])

        await items[2].trigger('click')
        await flushPromises()

        expect(previewProduct).toHaveBeenCalledWith(expect.objectContaining({ product_preset_id: 3 }), false, '', 4, null)
    })

    it('shows a plain preview button for a single format', async () => {
        const wrapper = mountNewProduct()
        await flushPromises()

        await chooseProductPreset(wrapper, PREVIEW_ONLY)

        expect(wrapper.find('[data-test="preview-formats"]').exists()).toBe(false)
    })

    it('saves a new product with its product preset', async () => {
        vi.mocked(createProduct).mockResolvedValue({ data: 42 })
        const wrapper = mountNewProduct()
        await flushPromises()
        wrapper.vm.product.title = 'Advisory'
        await chooseProductPreset(wrapper, ADVISORY)

        await wrapper.vm.handleSave()

        expect(vi.mocked(createProduct).mock.calls[0][0]).toMatchObject({ title: 'Advisory', product_preset_id: 3 })
    })

    it('finds the product preset of a product opened before the product presets loaded', async () => {
        let resolveProductPresets
        vi.mocked(getAllUserProductPresets).mockReturnValue(
            new Promise((resolve) => {
                resolveProductPresets = resolve
            })
        )
        vi.mocked(getProductById).mockResolvedValue({
            data: { id: 5, title: 'Bulletin', description: '', product_preset_id: 3, state_id: 1, report_items: [], links: [] }
        })
        const wrapper = mountNewProduct()
        window.dispatchEvent(new CustomEvent('show-product-edit', { detail: { id: 5, modify: true, access: true } }))
        await flushPromises()
        expect(wrapper.vm.selectedProductPreset).toBeNull()

        resolveProductPresets({ data: { items: [ADVISORY, PREVIEW_ONLY] } })
        await flushPromises()

        expect(wrapper.vm.selectedProductPreset?.id).toBe(3)
        expect(wrapper.vm.tickedDeliveryIds).toEqual([11, 12, 13])
    })

    it.each([
        ['gcve', 'GCVE Advisory'],
        ['cve', 'CVE Record']
    ])('makes a %s product English and offers it CVD Reports only', async (systemKey, name) => {
        const shipped = { id: 9, name, system_key: systemKey, public_web_enabled: systemKey === 'gcve', deliveries: [] }
        vi.mocked(getAllUserProductPresets).mockResolvedValue({ data: { items: [ADVISORY, shipped] } })
        const wrapper = mountNewProduct()
        await flushPromises()
        wrapper.vm.product.language = 'cs'

        await chooseProductPreset(wrapper, shipped)

        expect(wrapper.vm.product.language).toBe('en')
        expect(wrapper.findComponent('[data-test="product-source-language"]').props('disabled')).toBe(true)
        expect(wrapper.findComponent({ name: 'ReportItemSelector' }).props('reportTypeKey')).toBe('cvd')

        // Any other product preset: every report, and the language is the author's to pick.
        await chooseProductPreset(wrapper, ADVISORY)
        expect(wrapper.findComponent({ name: 'ReportItemSelector' }).props('reportTypeKey')).toBeNull()
        expect(wrapper.findComponent('[data-test="product-source-language"]').props('disabled')).toBe(false)
    })

    it('says why core refused a state change, goes back to the state the product is in, and reads its reports again', async () => {
        // A CVE Record whose publication CVE Services refused part way: one record went out.
        const CVE_RECORD = { id: 9, name: 'CVE Record', system_key: 'cve', public_web_enabled: false, deliveries: [] }
        vi.mocked(getAllUserProductPresets).mockResolvedValue({ data: { items: [ADVISORY, CVE_RECORD] } })
        const report = { id: 21, title: 'Login bypass', cve_status: null }
        vi.mocked(getProductById).mockResolvedValueOnce({
            data: { id: 5, title: 'Login bypass', description: '', product_preset_id: 9, state_id: 2, report_items: [report], links: [] }
        })
        const wrapper = mountNewProduct()
        window.dispatchEvent(new CustomEvent('show-product-edit', { detail: { id: 5, modify: true, access: true } }))
        await flushPromises()
        const reason = 'CVE Services refused 1 record(s). Sent: CVE-2026-1234. CVE-2026-1235: schema validation failed'
        vi.mocked(updateProduct).mockRejectedValueOnce({ response: { status: 400, data: { error: reason } } })
        vi.mocked(getProductById).mockResolvedValueOnce({
            data: { id: 5, report_items: [{ ...report, cve_status: { cve_id: 'CVE-2026-1234', state: 'PUBLISHED' } }] }
        })

        // What the state selector does when "published" is picked.
        wrapper.vm.handleStateChange(1)
        await flushPromises()

        expect(notifications).toContainEqual({ type: 'error', message: reason })
        expect(wrapper.vm.product.state_id).toBe(2)
        expect(wrapper.vm.reportItems[0].cve_status).toEqual({ cve_id: 'CVE-2026-1234', state: 'PUBLISHED' })
    })
})

describe('NewProduct public webs', () => {
    // On every web: the product can be left out of some.
    const FEEDS = {
        ...ADVISORY,
        id: 6,
        public_web_names: [],
        web_choices: [
            { id: 3, name: 'Archive' },
            { id: 1, name: 'Cyberfeed' }
        ]
    }
    const ONE_WEB = { ...ADVISORY, web_choices: [{ id: 1, name: 'Cyberfeed' }] }

    const webBoxes = (wrapper) => wrapper.findAll('[data-test="product-webs"] input[type="checkbox"]')

    beforeEach(() => {
        vi.clearAllMocks()
        vi.mocked(getAllUserProductPresets).mockResolvedValue({ data: { items: [FEEDS, ONE_WEB] } })
    })

    afterEach(() => {
        mounted.splice(0).forEach((wrapper) => wrapper.unmount())
    })

    it('shows the product on every web of its product preset until one is unticked', async () => {
        const wrapper = mountNewProduct()
        await flushPromises()
        await chooseProductPreset(wrapper, FEEDS)

        expect(wrapper.vm.shownWebIds).toEqual([3, 1])
        expect(webBoxes(wrapper).map((box) => box.element.checked)).toEqual([true, true])

        await webBoxes(wrapper)[0].setValue(false)
        expect(wrapper.vm.product.public_web_ids).toEqual([1])

        await webBoxes(wrapper)[0].setValue(true)
        expect(wrapper.vm.product.public_web_ids).toEqual([])
        expect(wrapper.vm.product.public_web_enabled).toBe(true)
    })

    it('keeps the product off the public web with every web unticked, and on it again with one ticked', async () => {
        const wrapper = mountNewProduct()
        await flushPromises()
        await chooseProductPreset(wrapper, FEEDS)

        await webBoxes(wrapper)[0].setValue(false)
        await webBoxes(wrapper)[1].setValue(false)
        expect(wrapper.vm.product).toMatchObject({ public_web_enabled: false, public_web_ids: [] })
        expect(webBoxes(wrapper).map((box) => box.element.checked)).toEqual([false, false])

        await webBoxes(wrapper)[1].setValue(true)
        expect(wrapper.vm.product).toMatchObject({ public_web_enabled: true, public_web_ids: [1] })
    })

    it('saves the webs an edit leaves the product on, and keeps them unknown until loaded', async () => {
        const wrapper = mountNewProduct()
        await flushPromises()
        wrapper.vm.openEditDialog({ id: 5, title: 'Bulletin', product_preset_id: 6, state_id: 1, modify: true, access: true })
        expect(wrapper.vm.product.public_web_ids).toBeUndefined()
        expect(wrapper.vm.product.public_web_enabled).toBeUndefined()

        wrapper.vm.openEditDialog(
            { id: 5, title: 'Bulletin', product_preset_id: 6, state_id: 1, public_web_ids: [3] },
            { modify: true, access: true }
        )
        await flushPromises()
        expect(wrapper.vm.shownWebIds).toEqual([3])

        await webBoxes(wrapper)[1].setValue(true)
        await flushPromises()
        expect(vi.mocked(updateProduct).mock.calls.at(-1)[0]).toMatchObject({ id: 5, public_web_ids: [] })
    })

    it('puts a product moved to another product preset on all of its webs', async () => {
        const wrapper = mountNewProduct()
        await flushPromises()
        await chooseProductPreset(wrapper, FEEDS)
        await webBoxes(wrapper)[0].setValue(false)
        await webBoxes(wrapper)[1].setValue(false)

        await chooseProductPreset(wrapper, ONE_WEB)

        expect(wrapper.vm.product).toMatchObject({ public_web_enabled: true, public_web_ids: [] })
        // A single web is shown too, and can be unticked like any other.
        expect(webBoxes(wrapper).map((box) => box.element.checked)).toEqual([true])
        expect(wrapper.find('[data-test="product-webs"]').text()).toContain('Cyberfeed')
        await webBoxes(wrapper)[0].setValue(false)
        expect(wrapper.vm.product.public_web_enabled).toBe(false)
    })
})
