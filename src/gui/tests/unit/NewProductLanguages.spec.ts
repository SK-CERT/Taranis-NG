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
    translateProduct,
    updateProduct
} from '@/api/publish'
import { getReportItem } from '@/api/analyze'
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
    translateProduct: vi.fn(),
    checkProductLanguage: vi.fn()
}))

vi.mock('@/api/analyze', () => ({
    getReportItem: vi.fn()
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

vi.mock('@/api/tags', () => ({
    getEntityTypeTags: vi.fn(() =>
        Promise.resolve({
            data: {
                tags: [
                    { id: 1, display_name: 'Urgent', color: '#FF0000', icon: 'mdi-fire', system_key: null, sort_order: 0 },
                    {
                        id: 11,
                        display_name: 'translation_outdated',
                        color: '#FB8C00',
                        icon: 'mdi-alert',
                        system_key: 'translation_outdated',
                        sort_order: 102
                    }
                ]
            }
        })
    )
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

async function openProduct(overrides: Record<string, unknown> = {}) {
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
            translations: { en: { title: { value: 'Bulletin (en)', origin: 'ai', version: 1, outdated: true } } },
            ...overrides
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
        expect(saved.translations).toEqual({ en: { title: { value: 'Weekly bulletin', origin: 'manual' } } })
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
        expect(saved.translations).toEqual({ en: { title: { value: 'Bulletin (en)', origin: 'manual' } } })
        expect(wrapper.find('[data-test="translation-ai"]').exists()).toBe(false)
        expect(wrapper.find('[data-test="translation-outdated"]').exists()).toBe(false)
        expect(wrapper.vm.tabStatuses['en']).toBe('translation_done')
    })

    it('edits the description of the open tab as a translation, keeping the original', async () => {
        const wrapper = await openProduct({ description: 'Souhrn týdne' })
        wrapper.vm.activeLanguage = 'en'
        await flushPromises()

        const description = wrapper.get('[data-test="product-description"] textarea')
        expect((description.element as HTMLTextAreaElement).value).toBe('')
        await description.setValue('Summary of the week')
        await description.trigger('blur')
        await flushPromises()

        const saved = vi.mocked(updateProduct).mock.calls.at(-1)?.[0] as { description: string; translations: Record<string, object> }
        expect(saved.description).toBe('Souhrn týdne')
        expect(saved.translations['en']).toEqual({
            title: { value: 'Bulletin (en)', origin: 'ai' },
            description: { value: 'Summary of the week', origin: 'manual' }
        })
        // Partly translated until the title, outdated, is brought up to date.
        expect(wrapper.vm.tabStatuses['en']).toBe('translation_outdated')
    })

    it('translates what is missing or outdated into every language, title and description, and keeps what a person wrote', async () => {
        vi.mocked(translateProduct).mockImplementation((({ texts, languages }: { texts: Record<string, string>; languages: string[] }) =>
            Promise.resolve({
                data: {
                    translations: Object.fromEntries(
                        languages.map((language) => [
                            language,
                            Object.fromEntries(Object.entries(texts).map(([field, text]) => [field, `[${language}] ${text}`]))
                        ])
                    ),
                    failed: {}
                }
            })) as never)
        const wrapper = await openProduct({
            description: 'Souhrn',
            translations: {
                en: { title: { value: 'Bulletin (en)', origin: 'ai', version: 1, outdated: true } },
                sk: { title: { value: 'Bulletin (sk)', origin: 'manual', version: 2, outdated: false } }
            }
        })

        await wrapper.get('[data-test="translate-product"]').trigger('click')
        await flushPromises()

        // Language after language, each with what it is missing.
        expect(vi.mocked(translateProduct).mock.calls.map(([request]) => [request.texts, request.languages])).toEqual([
            [{ title: 'Bulletin', description: 'Souhrn' }, ['en']],
            [{ description: 'Souhrn' }, ['sk']],
            [{ title: 'Bulletin', description: 'Souhrn' }, ['de']]
        ])
        const saved = vi.mocked(updateProduct).mock.calls.at(-1)?.[0] as { translations: Record<string, object> }
        expect(saved.translations['sk']).toEqual({
            title: { value: 'Bulletin (sk)', origin: 'manual' },
            description: { value: '[sk] Souhrn', origin: 'ai' }
        })
        expect(saved.translations['en']).toEqual({
            title: { value: '[en] Bulletin', origin: 'ai' },
            description: { value: '[en] Souhrn', origin: 'ai' }
        })
        expect(wrapper.vm.tabStatuses['de']).toBe('translation_ai')
    })

    it('shows the progress of the whole product, language by language, and says when it is done', async () => {
        const notifications: CustomEvent[] = []
        window.addEventListener('notification', (event) => notifications.push(event as CustomEvent))
        let finish: (value: unknown) => void = () => {}
        vi.mocked(translateProduct)
            .mockImplementationOnce(() => new Promise((resolve) => (finish = resolve)) as never)
            .mockResolvedValue({ data: { translations: {}, failed: {} } } as never)
        const wrapper = await openProduct()

        await wrapper.get('[data-test="translate-product"]').trigger('click')
        await flushPromises()
        expect(wrapper.get('[data-test="product-translation-progress"]').text()).toBe('Translating: 0 of 3 languages done')

        finish({ data: { translations: { en: { title: 'Bulletin (AI)' } }, failed: {} } })
        await flushPromises()
        expect(wrapper.find('[data-test="product-translation-progress"]').exists()).toBe(false)
        expect(vi.mocked(updateProduct).mock.calls).toHaveLength(3)
        expect(notifications.at(-1)?.detail).toEqual({ type: 'success', loc: 'report_item.translation.finished' })
    })

    it('translates the open tab, and marks its AI translations as reviewed at once', async () => {
        const notifications: CustomEvent[] = []
        window.addEventListener('notification', (event) => notifications.push(event as CustomEvent))
        vi.mocked(translateProduct).mockResolvedValue({
            data: { translations: { de: { title: 'Bulletin (de)', description: 'Inhalt' } }, failed: {} }
        } as never)
        const wrapper = await openProduct({ description: 'Souhrn' })
        wrapper.vm.activeLanguage = 'de'
        await flushPromises()

        expect(wrapper.get('[data-test="product-translation-header"]').text()).toContain('Translate into German')
        expect(wrapper.find('[data-test="review-product-language"]').exists()).toBe(false)
        await wrapper.get('[data-test="translate-product-language"]').trigger('click')
        await flushPromises()
        expect(translateProduct).toHaveBeenLastCalledWith({
            texts: { title: 'Bulletin', description: 'Souhrn' },
            source_language: 'cs',
            languages: ['de'],
            report_item_ids: [1, 2]
        })

        await wrapper.get('[data-test="review-product-language"]').trigger('click')
        await flushPromises()
        const saved = vi.mocked(updateProduct).mock.calls.at(-1)?.[0] as { translations: Record<string, object> }
        expect(saved.translations['de']).toEqual({
            title: { value: 'Bulletin (de)', origin: 'manual' },
            description: { value: 'Inhalt', origin: 'manual' }
        })
        expect(notifications.at(-1)?.detail).toEqual({ type: 'success', loc: 'report_item.translation.reviewed', params: { count: 2 } })
        expect(wrapper.find('[data-test="review-product-language"]').exists()).toBe(false)
    })

    it('shows a report changed while the product is open on its card, and stays unchanged itself', async () => {
        const wrapper = await openProduct()
        const status = { en: 'translation_missing', sk: 'translation_missing' }
        vi.mocked(getProductById).mockResolvedValue({
            data: {
                report_items: [
                    { id: 1, title: 'A', type_languages: ['cs', 'en', 'sk'], language: 'cs', translation_status: status },
                    { id: 2, title: 'B renamed' }
                ]
            }
        } as never)
        await vi.advanceTimersByTimeAsync(400)
        await flushPromises()
        const checksBefore = vi.mocked(checkProductLanguage).mock.calls.length
        const updated = (id: number) =>
            new CustomEvent('report-item-updated', { detail: { report_item_id: id, user_id: 101, source_language: 'cs' } })

        // A report the product does not have is none of its business.
        window.dispatchEvent(updated(99))
        await vi.advanceTimersByTimeAsync(600)
        expect(getProductById).not.toHaveBeenCalled()

        // Several updates in a row cause as many refreshes as one (other specs' dialogs listen too).
        window.dispatchEvent(updated(1))
        window.dispatchEvent(updated(1))
        expect(getProductById).not.toHaveBeenCalled()
        await vi.advanceTimersByTimeAsync(600)
        await flushPromises()
        const afterBurst = vi.mocked(getProductById).mock.calls.length
        window.dispatchEvent(updated(1))
        await vi.advanceTimersByTimeAsync(600)
        await flushPromises()
        expect(vi.mocked(getProductById).mock.calls.length).toBe(2 * afterBurst)

        expect(wrapper.vm.reportItems[0]).toMatchObject({ id: 1, language: 'cs', translation_status: status })
        expect(wrapper.vm.reportItems[1]).toMatchObject({ id: 2, title: 'B' })
        expect(wrapper.vm.hasUnsavedChanges()).toBe(false)
        expect(updateProduct).not.toHaveBeenCalled()
        // The notices are asked again: the report's language changed what they say.
        expect(vi.mocked(checkProductLanguage).mock.calls.length).toBeGreaterThan(checksBefore)
    })

    it('takes a changed report from its detail while the product is not saved yet', async () => {
        const wrapper = await openNewProduct('cs')
        wrapper.vm.reportItems = [{ id: 7, title: 'Old', language: null }]
        await flushPromises()
        vi.mocked(getReportItem).mockResolvedValue({
            data: {
                title: 'New',
                title_prefix: '',
                language: 'cs',
                tags: [],
                translation_status: { en: 'translation_missing' },
                translations: { en: { title: { value: 'New (en)' } } }
            }
        } as never)

        window.dispatchEvent(new CustomEvent('report-item-updated', { detail: { report_item_id: 7, user_id: 101 } }))
        await vi.advanceTimersByTimeAsync(600)
        await flushPromises()

        expect(getReportItem).toHaveBeenCalledWith('7')
        expect(wrapper.vm.reportItems[0]).toMatchObject({
            id: 7,
            title: 'New',
            language: 'cs',
            translation_status: { en: 'translation_missing' },
            title_translations: { en: { title: 'New (en)' } }
        })
    })

    it('says so when every language is already translated', async () => {
        const notifications: CustomEvent[] = []
        window.addEventListener('notification', (event) => notifications.push(event as CustomEvent))
        const current = { value: 'x', origin: 'manual', version: 1, outdated: false }
        const wrapper = await openProduct({ translations: { en: { title: current }, sk: { title: current }, de: { title: current } } })

        await wrapper.get('[data-test="translate-product"]').trigger('click')
        await flushPromises()

        expect(translateProduct).not.toHaveBeenCalled()
        expect(notifications.at(-1)?.detail).toEqual({ type: 'info', loc: 'product.nothing_to_translate' })
    })

    it('translates one text into the open tab, asking before it replaces a persons', async () => {
        vi.mocked(translateProduct).mockResolvedValue({ data: { translations: { sk: { title: 'Bulletin (AI)' } }, failed: {} } } as never)
        const wrapper = await openProduct({
            description: 'Souhrn',
            translations: { sk: { title: { value: 'Bulletin (sk)', origin: 'manual', version: 2, outdated: false } } }
        })
        wrapper.vm.activeLanguage = 'sk'
        await flushPromises()

        await wrapper.get('[data-test="translate-product-title"]').trigger('click')
        await flushPromises()
        expect(wrapper.find('[data-test="dialog-report_item.translation.overwrite_title"]').exists()).toBe(true)
        expect(translateProduct).not.toHaveBeenCalled()

        await wrapper.vm.runPendingField()
        await flushPromises()
        expect(translateProduct).toHaveBeenLastCalledWith({
            texts: { title: 'Bulletin' },
            source_language: 'cs',
            languages: ['sk'],
            report_item_ids: [1, 2]
        })

        // The description has no translation yet: no question asked.
        await wrapper.get('[data-test="translate-product-description"]').trigger('click')
        await flushPromises()
        expect(vi.mocked(translateProduct).mock.calls.at(-1)?.[0].texts).toEqual({ description: 'Souhrn' })
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

        expect(checkProductLanguage).toHaveBeenLastCalledWith(
            expect.objectContaining({ id: -1, product_type_id: 4, report_items: [{ id: 1 }, { id: 2 }] }),
            'sk'
        )
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

    it('saves the tags put on a saved product with it', async () => {
        const wrapper = await openProduct()
        expect(wrapper.find('[data-test="tag-picker"]').exists()).toBe(true)

        wrapper.vm.changeTags([1])
        await flushPromises()

        expect(vi.mocked(updateProduct).mock.calls.at(-1)?.[0]).toMatchObject({ id: 12, tag_ids: [1] })
    })

    it('marks a language tab whose title is outdated', async () => {
        const wrapper = await openProduct()

        const english = wrapper.get('[data-test="product-language-tabs"]').findAll('.v-tab').at(1)!
        expect(english.find('[data-test="tab-status-translation_outdated"]').exists()).toBe(true)
    })

    it('marks a translation outdated as soon as its original changes, and not once it is changed back', async () => {
        const wrapper = await openProduct({
            translations: { en: { title: { value: 'Bulletin (en)', origin: 'manual', version: 1, outdated: false } } }
        })
        const english = () => wrapper.get('[data-test="product-language-tabs"]').findAll('.v-tab').at(1)!
        expect(english().find('[data-test="tab-status-translation_outdated"]').exists()).toBe(false)

        wrapper.vm.product.title = 'Weekly bulletin'
        await flushPromises()
        expect(english().find('[data-test="tab-status-translation_outdated"]').exists()).toBe(true)
        expect(wrapper.vm.fieldState('en', 'title')?.outdated).toBe(true)

        wrapper.vm.product.title = 'Bulletin'
        await flushPromises()
        expect(english().find('[data-test="tab-status-translation_outdated"]').exists()).toBe(false)
    })

    it('takes an AI translation made here as checked against the original it translated', async () => {
        const wrapper = await openProduct()
        wrapper.vm.product.title = 'Weekly bulletin'
        vi.mocked(translateProduct).mockResolvedValueOnce({ data: { translations: { en: { title: 'Weekly bulletin (en)' } } } } as never)

        await wrapper.vm.translateInto('en', ['title'])
        await flushPromises()

        expect(wrapper.vm.fieldState('en', 'title')).toMatchObject({ origin: 'ai', outdated: false })
    })
})
