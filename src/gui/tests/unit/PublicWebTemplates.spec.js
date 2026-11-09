import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { mountWithPlugins } from '../helpers/mount-helpers'
import NewPublicWebTemplate from '@/components/config/public-web/NewPublicWebTemplate.vue'
import DialogToolbar from '@/components/common/dialogs/DialogToolbar.vue'
import { createPublicWebTemplate, getAllProductPresets } from '@/api/config'

vi.mock('@/api/config', () => ({
    createPublicWebTemplate: vi.fn(),
    updatePublicWebTemplate: vi.fn().mockResolvedValue({ data: {} }),
    getAllProductPresets: vi.fn().mockResolvedValue({
        data: {
            items: [
                { id: 1, name: 'Vulnerability bulletin' },
                { id: 2, name: 'Disinformation overview' }
            ]
        }
    }),
    getAllReportItemTypes: vi.fn().mockResolvedValue({
        data: {
            items: [
                { id: 8, title: 'Vulnerability Report', attribute_groups: [] },
                {
                    id: 9,
                    title: 'Disinformation from public source',
                    attribute_groups: [{ attribute_group_items: [{ title: 'Source (link)' }, { title: 'Quote' }] }]
                }
            ]
        }
    }),
    getBuiltinPublicWebTemplates: vi.fn().mockResolvedValue({
        data: {
            items: [
                { name: 'builtin/item_generic.html', source: '<div>generic</div>' },
                { name: 'builtin/product_base.html', source: '{% block detail %}{% endblock %}' }
            ]
        }
    })
}))

vi.mock('@/composables/useAuth', () => ({
    useAuth: () => ({ checkPermission: () => true })
}))

// The activator really opens the dialog, so its open-time loading runs as in the app.
const VDialogStub = {
    name: 'VDialog',
    props: ['modelValue'],
    emits: ['update:modelValue'],
    template:
        '<div><slot name="activator" :props="{ onClick: () => $emit(\'update:modelValue\', true) }" /><div v-if="modelValue"><slot /></div></div>'
}

const VMenuStub = {
    name: 'VMenu',
    template: '<div><slot name="activator" :props="{}" /><slot /></div>'
}

const stubs = { VDialog: VDialogStub, VMenu: VMenuStub }
const mounted = []

// Product preset 1 has a template for every web and one for the Cyberfeed web.
const TAKEN = [
    {
        id: 3,
        name: 'Bulletin page',
        product_preset_id: 1,
        report_item_type_id: null,
        source: '',
        require_tlp_clear: true,
        public_web_ids: []
    },
    {
        id: 4,
        name: 'Cyberfeed bulletin',
        product_preset_id: 1,
        report_item_type_id: null,
        source: '',
        require_tlp_clear: true,
        public_web_ids: [5]
    }
]
const WEBS = [
    { id: 5, name: 'Cyberfeed' },
    { id: 6, name: 'Partners' }
]

async function openNewTemplate() {
    const wrapper = mountWithPlugins(NewPublicWebTemplate, { props: { templates: TAKEN, publicWebs: WEBS }, global: { stubs } })
    mounted.push(wrapper)
    await wrapper.find('button').trigger('click')
    await flushPromises()
    return wrapper
}

const select = (wrapper, dataTest) =>
    wrapper.findAllComponents({ name: 'VSelect' }).find((component) => component.attributes('data-test') === dataTest)

describe('NewPublicWebTemplate', () => {
    beforeEach(() => vi.clearAllMocks())
    afterEach(() => {
        while (mounted.length) mounted.pop().unmount()
    })

    it('offers the TLP switch for product templates only', async () => {
        const wrapper = await openNewTemplate()
        expect(wrapper.find('[data-test="template-require-tlp"]').exists()).toBe(true)

        select(wrapper, 'template-kind').vm.$emit('update:modelValue', 'item')
        await flushPromises()

        expect(wrapper.find('[data-test="template-require-tlp"]').exists()).toBe(false)
    })

    it('offers every product preset, and the webs no other template of it is for', async () => {
        const wrapper = await openNewTemplate()
        expect(select(wrapper, 'template-target').props('items')).toEqual([
            { id: 1, title: 'Vulnerability bulletin' },
            { id: 2, title: 'Disinformation overview' }
        ])

        select(wrapper, 'template-target').vm.$emit('update:modelValue', 1)
        await flushPromises()

        const webs = select(wrapper, 'template-webs')
        expect(webs.props('items')).toEqual(WEBS)
        expect(WEBS.map((web) => webs.props('itemProps')(web))).toEqual([{ disabled: true, subtitle: "Already in 'Cyberfeed bulletin'" }, {}])
        // Every web (none chosen) is taken too; Partners alone is not.
        const [everyWebRule] = webs.props('rules')
        expect(everyWebRule([])).toBe("'Bulletin page' is already its template for every web: choose the webs this one is for.")
        expect(everyWebRule([6])).toBe(true)

        // Another product preset has no template yet: every web is free.
        select(wrapper, 'template-target').vm.$emit('update:modelValue', 2)
        await flushPromises()
        expect(webs.props('rules')[0]([])).toBe(true)
        expect(webs.props('itemProps')(WEBS[0])).toEqual({})
    })

    it('still offers the report item types when the product presets are refused', async () => {
        vi.spyOn(console, 'error').mockImplementation(() => undefined)
        vi.mocked(getAllProductPresets).mockRejectedValueOnce({ response: { status: 403 } })
        const wrapper = await openNewTemplate()
        select(wrapper, 'template-kind').vm.$emit('update:modelValue', 'item')
        await flushPromises()

        expect(
            select(wrapper, 'template-target')
                .props('items')
                .map((type) => type.id)
        ).toEqual([8, 9])
    })

    it('lists the attrs names of the chosen report item type', async () => {
        const wrapper = await openNewTemplate()
        select(wrapper, 'template-kind').vm.$emit('update:modelValue', 'item')
        await flushPromises()
        select(wrapper, 'template-target').vm.$emit('update:modelValue', 9)
        // The help panel renders its content once expanded.
        await wrapper.find('.v-expansion-panel-title').trigger('click')
        await flushPromises()

        expect(wrapper.findAll('[data-test="template-attr-key"]').map((key) => key.text())).toEqual([
            'item.attrs.source_(link)',
            'item.attrs.quote'
        ])
        // An item template can start from a built-in item template.
        expect(wrapper.findAll('[data-test="template-start"]').map((start) => start.text())).toEqual(['item_generic.html'])
    })

    it('edits the source in a highlighting editor, filled by a starting point', async () => {
        const wrapper = await openNewTemplate()
        select(wrapper, 'template-kind').vm.$emit('update:modelValue', 'item')
        await flushPromises()

        await wrapper.find('[data-test="template-start"]').trigger('click')
        await flushPromises()

        const editor = wrapper.find('[data-test="template-source"] textarea')
        expect(editor.element.value).toBe('<div>generic</div>')
        expect(editor.attributes('aria-label')).toBe('Template (Jinja)')
        expect(wrapper.findAll('[data-test="template-source"] .token.tag').length).toBeGreaterThan(0)
    })

    it('creates a template and shows why core refused one', async () => {
        vi.mocked(createPublicWebTemplate).mockRejectedValueOnce({
            response: { data: { error: 'Template error on line 2: unexpected end of template' } }
        })
        const wrapper = await openNewTemplate()
        await wrapper.findAllComponents({ name: 'VTextField' })[0].vm.$emit('update:modelValue', 'Disinformation page')
        select(wrapper, 'template-target').vm.$emit('update:modelValue', 2)
        await flushPromises()

        wrapper.findComponent(DialogToolbar).vm.$emit('save')
        await flushPromises()

        expect(createPublicWebTemplate).toHaveBeenCalledWith(
            expect.objectContaining({
                id: -1,
                name: 'Disinformation page',
                product_preset_id: 2,
                report_item_type_id: null,
                require_tlp_clear: true,
                public_web_ids: []
            })
        )
        expect(wrapper.find('[data-test="template-error"]').text()).toContain('line 2')
    })
})
