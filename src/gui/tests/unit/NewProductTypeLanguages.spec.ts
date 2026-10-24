import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { mountWithPlugins } from '../helpers/mount-helpers'
import NewProductType from '@/components/config/presenters/NewProductType.vue'
import { updateProductType } from '@/api/config'

// A product type names the language of its default templates and adds other languages, each
// with only the template paths; a template a language leaves empty is the default one.

const presenter = {
    id: 'p1',
    type: 'MESSAGE_PRESENTER',
    parameters: [
        { id: 1, key: 'TITLE_TEMPLATE_PATH', name: 'Title template', default_value: '' },
        { id: 2, key: 'BODY_TEMPLATE_PATH', name: 'Body template', default_value: '' },
        { id: 3, key: 'SENDER', name: 'Sender', default_value: '' }
    ]
}

// No templates at all: nothing about it depends on a language.
const jsonPresenter = {
    id: 'p2',
    type: 'JSON_PRESENTER',
    parameters: [{ id: 4, key: 'JSON_INDENT', name: 'JSON indent', default_value: '4' }]
}

vi.mock('@/api/config', () => ({
    createNewProductType: vi.fn(() => Promise.resolve({})),
    updateProductType: vi.fn(() => Promise.resolve({})),
    getAllPresentersNodes: vi.fn(() =>
        Promise.resolve({ data: { items: [{ id: 'n1', name: 'Node', presenters: [presenter, jsonPresenter] }] } })
    )
}))

vi.mock('@/stores/config', () => ({
    useConfigStore: () => ({ reportItemTypesConfig: { items: [] }, loadReportItemTypesConfig: vi.fn(() => Promise.resolve()) })
}))

vi.mock('@/composables/useAuth', () => ({
    useAuth: () => ({ checkPermission: () => true })
}))

const VDialogStub = { name: 'VDialog', template: '<div><slot /></div>' }

const editItem = {
    id: 7,
    title: 'e-mail',
    description: 'Mail',
    presenter_id: 'p1',
    parameter_values: [
        { value: 'title_cz.txt', parameter: presenter.parameters[0] },
        { value: 'body_cz.txt', parameter: presenter.parameters[1] },
        { value: 'cert@example.test', parameter: presenter.parameters[2] }
    ],
    language: 'cs',
    language_templates: { sk: { BODY_TEMPLATE_PATH: 'body_sk.txt' } }
}

async function openEditor(item: object = editItem) {
    const wrapper = mountWithPlugins(NewProductType, { props: { editItem: null }, global: { stubs: { VDialog: VDialogStub } } })
    await flushPromises()
    await wrapper.setProps({ editItem: item })
    await flushPromises()
    return wrapper
}

describe('NewProductType languages', () => {
    beforeEach(() => vi.clearAllMocks())

    it('shows only the template paths of a language, with the default ones as placeholders', async () => {
        const wrapper = await openEditor()
        const tabs = wrapper.get('[data-test="product-type-language-tabs"]').findAll('.v-tab')
        expect(tabs.map((tab) => tab.text())).toEqual(['Default', 'Slovak'])

        wrapper.vm.parameterTab = 'sk'
        await flushPromises()

        const fields = wrapper.get('[data-test="language-templates"]').findAll('input')
        expect(fields).toHaveLength(2)
        expect((fields[0]!.element as HTMLInputElement).placeholder).toBe('title_cz.txt')
        expect((fields[1]!.element as HTMLInputElement).value).toBe('body_sk.txt')
    })

    it('saves the template language and the overrides of each language', async () => {
        const wrapper = await openEditor()
        wrapper.vm.addTemplateLanguage('en')
        wrapper.vm.setLanguageTemplate('TITLE_TEMPLATE_PATH', 'title_en.txt')
        await flushPromises()

        await wrapper.vm.persist()

        const payload = vi.mocked(updateProductType).mock.calls[0]![0] as { language: string; language_templates: object }
        expect(payload.language).toBe('cs')
        expect(payload.language_templates).toEqual({
            sk: { BODY_TEMPLATE_PATH: 'body_sk.txt' },
            en: { TITLE_TEMPLATE_PATH: 'title_en.txt' }
        })
    })

    it('drops a removed language', async () => {
        const wrapper = await openEditor()
        wrapper.vm.removeTemplateLanguage('sk')
        await flushPromises()

        expect(wrapper.vm.localItem.language_templates).toEqual({})
        expect(wrapper.vm.parameterTab).toBe('default')
    })

    it('asks nothing about template languages for a presenter without templates', async () => {
        const wrapper = await openEditor({
            id: 8,
            title: 'JSON',
            description: 'Data',
            presenter_id: 'p2',
            parameter_values: [{ value: '2', parameter: jsonPresenter.parameters[0] }],
            language: 'cs',
            language_templates: {}
        })

        expect(wrapper.find('[data-test="product-type-language-tabs"]').exists()).toBe(false)
        expect(wrapper.find('[data-test="product-type-template-language"]').exists()).toBe(false)
        expect(wrapper.find('[data-test="add-template-language"]').exists()).toBe(false)

        await wrapper.vm.persist()

        const payload = vi.mocked(updateProductType).mock.calls[0]![0] as { language: string | null; language_templates: object }
        expect(payload.language).toBeNull()
        expect(payload.language_templates).toEqual({})
    })
})
