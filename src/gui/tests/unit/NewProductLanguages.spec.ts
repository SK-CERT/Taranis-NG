import { defineComponent, h } from 'vue'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { mountWithPlugins } from '../helpers/mount-helpers'
import NewProduct from '@/components/publish/NewProduct.vue'
import {
    checkProductLanguage,
    createProduct,
    getProductById,
    previewProduct,
    publishProduct,
    translateProductTitle,
    updateProduct
} from '@/api/publish'
import { useSettingsStore } from '@/stores/settings'
import { openBlankTabWithoutOpener } from '@/utils/window'

// A product has a tab per language of its reports' types next to its own. The open tab is the
// language it is previewed in; publishing names its language; outdated translations need a yes.

vi.mock('@/api/publish', () => ({
    createProduct: vi.fn(),
    updateProduct: vi.fn(() => Promise.resolve({})),
    publishProduct: vi.fn(() => Promise.resolve({ data: { overall_success: true } })),
    previewProduct: vi.fn(() => Promise.resolve({ data: { token: 't' } })),
    getProductById: vi.fn(),
    translateProductTitle: vi.fn(),
    checkProductLanguage: vi.fn()
}))

vi.mock('@/api/user', () => ({
    getAllUserProductTypes: vi.fn().mockResolvedValue({
        data: {
            items: [
                { id: 4, title: 'e-mail' },
                { id: 5, title: 'JSON' }
            ]
        }
    }),
    getAllUserPublishersPresets: vi.fn().mockResolvedValue({ data: { items: [{ id: 8, name: 'Mailing list' }] } })
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
const VFormStub = defineComponent({
    name: 'VForm',
    setup(_, { expose, slots }) {
        expose({ validate: () => Promise.resolve({ valid: true }) })
        return () => h('form', slots['default']?.())
    }
})
const ConfirmationDialogStub = {
    name: 'ConfirmationDialog',
    props: { modelValue: Boolean, titleKey: { type: String, default: '' } },
    emits: ['confirm', 'update:modelValue'],
    template: '<div v-if="modelValue" :data-test="`dialog-${titleKey}`"><slot /></div>'
}

const NO_PROBLEMS = { missing: [], outdated: [], template_language: 'cs' }

async function openProduct() {
    const wrapper = mountWithPlugins(NewProduct, {
        global: {
            stubs: {
                VDialog: VDialogStub,
                VForm: VFormStub,
                ConfirmationDialog: ConfirmationDialogStub,
                StateSelector: true,
                ReportItemSelector: true
            }
        }
    })
    await flushPromises()
    wrapper.vm.openEditDialog(
        {
            id: 12,
            title: 'Bulletin',
            description: '',
            product_type_id: 4,
            state_id: undefined,
            report_items: [
                { id: 1, title: 'A', type_languages: ['cs', 'en', 'sk'] },
                { id: 2, title: 'B', type_languages: ['cs', 'de'] }
            ],
            links: [],
            language: 'cs',
            translations: { en: { title: { value: 'Bulletin (en)', origin: 'ai', version: 1, outdated: true } } }
        },
        { modify: true, access: true }
    )
    await flushPromises()
    return wrapper
}

async function openNewProduct(defaultLanguage: string) {
    const wrapper = mountWithPlugins(NewProduct, {
        global: {
            stubs: {
                VDialog: VDialogStub,
                VForm: VFormStub,
                ConfirmationDialog: ConfirmationDialogStub,
                StateSelector: true,
                ReportItemSelector: true
            }
        }
    })
    const languages = JSON.stringify([
        { id: 'cs', txt: 'Czech' },
        { id: 'en', txt: 'English' }
    ])
    useSettingsStore().settings = [{ key: 'CONTENT_DEFAULT_LANGUAGE', value: defaultLanguage, options: languages }] as never
    await flushPromises()
    wrapper.vm.openDialog()
    await flushPromises()
    return wrapper
}

const tabs = (wrapper: ReturnType<typeof mountWithPlugins>) =>
    wrapper
        .get('[data-test="product-language-tabs"]')
        .findAll('.v-tab')
        .map((tab) => tab.text())

describe('NewProduct languages', () => {
    beforeEach(() => {
        vi.clearAllMocks()
        vi.useFakeTimers({ shouldAdvanceTime: true })
        vi.mocked(checkProductLanguage).mockResolvedValue({ data: NO_PROBLEMS } as never)
    })

    it('starts a new product in the users default language and creates it in that language', async () => {
        vi.mocked(createProduct).mockResolvedValue({ data: 21 } as never)
        vi.mocked(getProductById).mockResolvedValue({ data: { language: 'cs' } } as never)
        const wrapper = await openNewProduct('cs')

        expect(wrapper.vm.product.language).toBe('cs')
        expect(wrapper.get('[data-test="product-source-language"]').text()).toContain('Czech')

        wrapper.vm.product.title = 'Bulletin'
        await wrapper.vm.handleSave()

        expect(vi.mocked(createProduct).mock.calls[0]![0]).toMatchObject({ title: 'Bulletin', language: 'cs' })
    })

    it('leaves a new products language unset without a default', async () => {
        const wrapper = await openNewProduct('')

        expect(wrapper.vm.product.language).toBeNull()
    })

    it('offers its own language and those of its reports types', async () => {
        const wrapper = await openProduct()

        expect(tabs(wrapper)).toEqual(['Czech (original)', 'English', 'Slovak', 'German'])
    })

    it('edits the title of the open tab and saves it as a person wrote it', async () => {
        const wrapper = await openProduct()
        wrapper.vm.activeLanguage = 'en'
        await flushPromises()

        const title = wrapper.get('[data-test="product-title"] input')
        expect((title.element as HTMLInputElement).value).toBe('Bulletin (en)')
        expect(wrapper.find('[data-test="translation-outdated"]').exists()).toBe(true)

        await title.setValue('Weekly bulletin')
        await title.trigger('blur')
        await flushPromises()

        const saved = vi.mocked(updateProduct).mock.calls.at(-1)?.[0] as { title: string; translations: object }
        expect(saved.title).toBe('Bulletin')
        expect(saved.translations).toEqual({ en: { title: 'Weekly bulletin', origin: 'manual' } })
    })

    it('takes a title a person typed as no longer the AIs, before it is saved', async () => {
        const wrapper = await openProduct()
        wrapper.vm.activeLanguage = 'en'
        await flushPromises()
        expect(wrapper.find('[data-test="translation-ai"]').exists()).toBe(true)

        await wrapper.get('[data-test="product-title"] input').setValue('Weekly bulletin')
        await flushPromises()

        expect(wrapper.find('[data-test="translation-ai"]').exists()).toBe(false)
        expect(wrapper.find('[data-test="translation-outdated"]').exists()).toBe(false)
    })

    it('marks the AI title as reviewed: kept as it is, saved as a persons and no longer outdated', async () => {
        const wrapper = await openProduct()
        wrapper.vm.activeLanguage = 'en'
        await flushPromises()

        await wrapper.get('[data-test="translation-review"]').trigger('click')
        await flushPromises()

        const saved = vi.mocked(updateProduct).mock.calls.at(-1)?.[0] as { translations: object }
        expect(saved.translations).toEqual({ en: { title: 'Bulletin (en)', origin: 'manual' } })
        expect(wrapper.find('[data-test="translation-ai"]').exists()).toBe(false)
        expect(wrapper.find('[data-test="translation-outdated"]').exists()).toBe(false)
    })

    it('stores AI titles as the AIs', async () => {
        vi.mocked(translateProductTitle).mockResolvedValue({
            data: { translations: { sk: 'Bulletin (sk)', de: 'Bulletin (de)' }, failed: {} }
        } as never)
        const wrapper = await openProduct()

        await wrapper.get('[data-test="translate-product-titles"]').trigger('click')
        await flushPromises()

        expect(translateProductTitle).toHaveBeenCalledWith({
            title: 'Bulletin',
            source_language: 'cs',
            languages: ['en', 'sk', 'de'],
            report_item_ids: [1, 2]
        })
        const saved = vi.mocked(updateProduct).mock.calls.at(-1)?.[0] as { translations: Record<string, object> }
        expect(saved.translations['sk']).toEqual({ title: 'Bulletin (sk)', origin: 'ai' })
    })

    it('previews in the open tabs language', async () => {
        const wrapper = await openProduct()
        wrapper.vm.activeLanguage = 'sk'
        await flushPromises()

        await wrapper.vm.handlePreview()
        await flushPromises()

        expect(previewProduct).toHaveBeenCalledWith(expect.any(Object), false, '', 'sk')
    })

    it('asks before previewing outdated translations, once per language', async () => {
        vi.mocked(checkProductLanguage).mockResolvedValue({
            data: { ...NO_PROBLEMS, template_language: 'en', outdated: [{ report_item_id: 1, title: 'A', field: 'title' }] }
        } as never)
        const wrapper = await openProduct()
        wrapper.vm.activeLanguage = 'en'
        await vi.advanceTimersByTimeAsync(400)
        await flushPromises()

        await wrapper.vm.handlePreview()
        expect(openBlankTabWithoutOpener).not.toHaveBeenCalled()
        expect(wrapper.find('[data-test="dialog-product.outdated_confirmation"]').text()).toContain('A')

        wrapper
            .findAllComponents({ name: 'ConfirmationDialog' })
            .find((dialog) => dialog.props('titleKey') === 'product.outdated_confirmation')!
            .vm.$emit('confirm')
        await flushPromises()
        expect(previewProduct).toHaveBeenCalledWith(expect.any(Object), false, '', 'en')

        vi.mocked(previewProduct).mockClear()
        await wrapper.vm.handlePreview()
        await flushPromises()
        expect(previewProduct).toHaveBeenCalledTimes(1)
    })

    it('publishes in the language chosen in the publish dialog', async () => {
        const wrapper = await openProduct()
        wrapper.vm.activeLanguage = 'sk'
        await flushPromises()
        wrapper.vm.publisherPresets[0].selected = true

        wrapper.vm.handlePublishConfirmation()
        await flushPromises()
        expect(wrapper.vm.publishLanguage).toBe('sk')
        wrapper.vm.publishLanguage = 'de'
        await wrapper.vm.handlePublish()
        await flushPromises()

        expect(publishProduct).toHaveBeenCalledWith(expect.any(Object), [8], 'de')
    })

    it('drops what the last check said as soon as the product type changes', async () => {
        vi.mocked(checkProductLanguage).mockResolvedValue({ data: { ...NO_PROBLEMS, template_language: 'sk' } } as never)
        const wrapper = await openProduct()
        wrapper.vm.activeLanguage = 'en'
        await vi.advanceTimersByTimeAsync(400)
        await flushPromises()
        expect(wrapper.find('[data-test="notice-templates"]').exists()).toBe(true)

        // The other type's check has not answered yet; the first type's templates are not its.
        wrapper.vm.selectedType = { id: 5, title: 'JSON' }
        await flushPromises()

        expect(wrapper.find('[data-test="notice-templates"]').exists()).toBe(false)
    })

    it('waits for the open tabs check before downloading', async () => {
        vi.mocked(checkProductLanguage).mockImplementation(
            (_product, language) =>
                Promise.resolve({
                    data: {
                        ...NO_PROBLEMS,
                        template_language: language,
                        outdated: language === 'en' ? [{ report_item_id: 1, title: 'A', field: 'title' }] : []
                    }
                }) as never
        )
        const wrapper = await openProduct()
        await vi.advanceTimersByTimeAsync(400)
        await flushPromises()

        // Straight after switching tabs, before that tab's check would have been asked for.
        wrapper.vm.activeLanguage = 'en'
        await wrapper.vm.handleDownload()
        await flushPromises()

        expect(previewProduct).not.toHaveBeenCalled()
        expect(wrapper.find('[data-test="dialog-product.outdated_confirmation"]').text()).toContain('A')
    })

    it('shows what the language falls back on', async () => {
        vi.mocked(checkProductLanguage).mockResolvedValue({
            data: { missing: [{ id: 2, title: 'B' }], outdated: [], template_language: 'cs' }
        } as never)
        const wrapper = await openProduct()
        wrapper.vm.activeLanguage = 'sk'
        await vi.advanceTimersByTimeAsync(400)
        await flushPromises()

        expect(checkProductLanguage).toHaveBeenLastCalledWith(expect.objectContaining({ id: 12 }), 'sk')
        expect(wrapper.get('[data-test="notice-missing"]').text()).toContain('B')
        const templates = wrapper.get('[data-test="notice-templates"]')
        expect(templates.text()).toContain('Czech')
        expect(templates.classes()).toContain('text-warning')
    })

    it('only informs about default templates of no stated language, and is quiet when the tab has its own', async () => {
        vi.mocked(checkProductLanguage).mockImplementation((_product, language) =>
            Promise.resolve({ data: { ...NO_PROBLEMS, template_language: language === 'sk' ? 'sk' : null } } as never)
        )
        const wrapper = await openProduct()
        wrapper.vm.activeLanguage = 'en'
        await vi.advanceTimersByTimeAsync(400)
        await flushPromises()

        const templates = wrapper.get('[data-test="notice-templates"]')
        expect(templates.text()).toContain('default')
        expect(templates.classes()).toContain('text-info')

        wrapper.vm.activeLanguage = 'sk'
        await vi.advanceTimersByTimeAsync(400)
        await flushPromises()
        expect(wrapper.find('[data-test="notice-templates"]').exists()).toBe(false)
    })
})
