import { createI18n } from 'vue-i18n'
import { flushPromises } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'
import { mountWithPlugins } from '../helpers/mount-helpers'
import NewProduct from '@/components/publish/NewProduct.vue'

const productPreset = vi.hoisted(() => ({
    id: 3,
    name: 'التوزيع',
    public_web_enabled: false,
    deliveries: [
        {
            id: 1,
            product_format_id: 7,
            product_format_title: 'JSON',
            publishing_channel_id: 'sftp',
            publishing_channel_name: 'Kanal العربية'
        },
        {
            id: 2,
            product_format_id: 7,
            product_format_title: 'JSON',
            publishing_channel_id: 'mail',
            publishing_channel_name: 'Kanal Deutsch'
        },
        { id: 3, product_format_id: 8, product_format_title: 'PDF', publishing_channel_id: null, publishing_channel_name: null }
    ]
}))

vi.mock('@/api/publish', () => ({
    createProduct: vi.fn(),
    updateProduct: vi.fn(),
    publishProduct: vi.fn(),
    previewProduct: vi.fn()
}))

vi.mock('@/api/user', () => ({
    getAllUserProductPresets: vi.fn().mockResolvedValue({ data: { items: [productPreset] } })
}))

vi.mock('@/api/state', () => ({
    getEntityTypeStates: vi.fn().mockResolvedValue({ data: { states: [] } })
}))

vi.mock('@/composables/useAuth', () => ({
    useAuth: () => ({ checkPermission: () => true })
}))

const VDialogStub = {
    name: 'VDialog',
    template: '<div><slot /></div>'
}

const ConfirmationDialogStub = {
    name: 'ConfirmationDialog',
    template: '<section data-test="publish-confirmation"><slot /></section>'
}

const createMessages = () =>
    createI18n({
        legacy: false,
        locale: 'de',
        messages: {
            de: {
                product: {
                    publish_confirmation_product_preset: '{productPreset} ist die Verteilung',
                    publish_confirmation_deliveries: '{deliveries} sind die Ziele',
                    no_product_preset: 'Keine Verteilung',
                    delivery: '{format} nach {channel}',
                    publish_confirmation_message: 'Jetzt veröffentlichen'
                }
            }
        }
    })

const mountEditor = async () => {
    const wrapper = mountWithPlugins(NewProduct, {
        global: {
            plugins: [createMessages()],
            stubs: {
                VDialog: VDialogStub,
                ConfirmationDialog: ConfirmationDialogStub,
                StateSelector: true,
                ReportItemSelector: true
            }
        }
    })
    await flushPromises()
    return wrapper
}

describe('NewProduct locale-safe publish confirmation', () => {
    it('uses complete reorderable messages and lists each ticked delivery on its own line', async () => {
        const wrapper = await mountEditor()
        wrapper.vm.product.title = 'عنوان المنتج'
        wrapper.vm.selectedProductPreset = productPreset
        wrapper.vm.handleProductPresetChange()
        await wrapper.vm.$nextTick()

        const isolate = (value: string) => `\u2068${value}\u2069`
        const labels = ['Kanal العربية', 'Kanal Deutsch'].map((channel) => `${isolate('JSON')} nach ${isolate(channel)}`)
        const confirmation = wrapper.get('[data-test="publish-confirmation"]')
        const lines = confirmation.findAll('.publish-deliveries > li')

        expect(confirmation.text()).toContain('التوزيع ist die Verteilung')
        expect(confirmation.text()).toContain(`${labels.join('')} sind die Ziele`)
        expect(lines.map((line) => line.text())).toEqual(labels)
        expect(lines.map((line) => line.get('bdi').attributes('dir'))).toEqual(['auto', 'auto'])
        expect(confirmation.findAll('bdi[dir="auto"]').map((node) => node.text())).toEqual(
            expect.arrayContaining(['عنوان المنتج', 'التوزيع', ...labels])
        )
        // The format-only PDF is not a delivery to tick.
        expect(wrapper.findAll('bdi[dir="auto"]').map((node) => node.text())).toEqual(expect.arrayContaining(labels))
        expect(wrapper.text()).not.toContain('PDF nach')
    })

    it('keeps the no-product-preset fallback inside the complete message', async () => {
        const wrapper = await mountEditor()
        const confirmation = wrapper.get('[data-test="publish-confirmation"]')

        expect(confirmation.text()).toContain('Keine Verteilung ist die Verteilung')
        expect(confirmation.findAll('.publish-deliveries > li')).toHaveLength(0)
    })

    it('gives editable server and user text automatic writing direction', async () => {
        const wrapper = await mountEditor()

        expect(
            wrapper
                .findAll('input')
                .slice(0, 2)
                .map((field) => field.attributes('dir'))
        ).toEqual(['auto', 'auto'])
        expect(wrapper.get('textarea').attributes('dir')).toBe('auto')
    })
})
