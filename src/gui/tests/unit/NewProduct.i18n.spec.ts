import { createI18n } from 'vue-i18n'
import { flushPromises } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'
import { mountWithPlugins } from '../helpers/mount-helpers'
import NewProduct from '@/components/publish/NewProduct.vue'

const publisherNames = vi.hoisted(() => ['Publisher العربية', 'Publisher Deutsch'])

vi.mock('@/api/publish', () => ({
    createProduct: vi.fn(),
    updateProduct: vi.fn(),
    publishProduct: vi.fn(),
    previewProduct: vi.fn()
}))

vi.mock('@/api/user', () => ({
    getAllUserProductTypes: vi.fn().mockResolvedValue({ data: { items: [{ id: 3, title: 'نوع المنتج' }] } }),
    getAllUserPublishersPresets: vi.fn().mockResolvedValue({
        data: { items: publisherNames.map((name, index) => ({ id: index + 1, name })) }
    })
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
                    publish_confirmation_type: '{type} ist die Produktart',
                    publish_confirmation_publishers: '{publishers} sind die Ziele',
                    no_type: 'Keine Produktart',
                    no_publisher_in_dialog: 'Keine Veröffentlichungsziele',
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
    it('uses complete reorderable messages and an active-locale publisher list', async () => {
        const wrapper = await mountEditor()
        wrapper.vm.product.title = 'عنوان المنتج'
        wrapper.vm.selectedType = { id: 3, title: 'نوع المنتج' }
        wrapper.vm.publisherPresets.forEach((preset: { selected: boolean }) => {
            preset.selected = true
        })
        await wrapper.vm.$nextTick()

        const isolate = (value: string) => `\u2068${value}\u2069`
        const expectedList = new Intl.ListFormat('de', { style: 'long', type: 'conjunction' }).format(publisherNames.map(isolate))
        const confirmation = wrapper.get('[data-test="publish-confirmation"]')

        expect(confirmation.text()).toContain('نوع المنتج ist die Produktart')
        expect(confirmation.text()).toContain(`${expectedList} sind die Ziele`)
        expect(wrapper.vm.selectedPublisherPresetList).toBe(expectedList)
        expect(confirmation.findAll('bdi[dir="auto"]').map((node) => node.text())).toEqual(
            expect.arrayContaining(['عنوان المنتج', 'نوع المنتج', expectedList])
        )
        expect(wrapper.findAll('bdi[dir="auto"]').map((node) => node.text())).toEqual(expect.arrayContaining(publisherNames))
    })

    it('keeps the no-type and no-publisher fallbacks inside the complete messages', async () => {
        const wrapper = await mountEditor()
        const confirmation = wrapper.get('[data-test="publish-confirmation"]')

        expect(confirmation.text()).toContain('Keine Produktart ist die Produktart')
        expect(confirmation.text()).toContain('Keine Veröffentlichungsziele sind die Ziele')
        expect(wrapper.vm.selectedPublisherPresetList).toBe('')
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
