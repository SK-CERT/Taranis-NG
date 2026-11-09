import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { mountWithPlugins } from '../helpers/mount-helpers'
import PublicWebTemplatesTab from '@/components/config/public-web/PublicWebTemplatesTab.vue'
import BuiltinTemplateDialog from '@/components/config/public-web/BuiltinTemplateDialog.vue'
import { getAllPublicWebTemplates, getBuiltinPublicWebTemplates, setBuiltinPublicWebTemplateEnabled } from '@/api/config'

const BUILTINS = [
    { name: 'builtin/_macros.html', source: '{% macro x() %}{% endmacro %}', can_disable: false, enabled: true },
    { name: 'builtin/item_generic.html', source: '<div>generic</div>', can_disable: true, enabled: true },
    { name: 'builtin/item_vulnerability.html', source: '<div>vulnerability</div>', can_disable: true, enabled: false },
    { name: 'builtin/product_base.html', source: '{% block detail %}{% endblock %}', can_disable: false, enabled: true },
    {
        name: 'builtin/product_vulnerability.html',
        source: '{% extends "builtin/product_base.html" %}',
        can_disable: true,
        enabled: true,
        updated_at: '07.11.2026 - 12:30',
        updated_by: 'admin'
    }
]

const builtinsResponse = (items = BUILTINS) => ({ data: { items: items.map((item) => ({ ...item })) } })

vi.mock('@/api/config', async (importOriginal) => ({
    ...(await importOriginal()),
    getAllPublicWebTemplates: vi.fn().mockResolvedValue({ data: { total_count: 0, items: [] } }),
    deletePublicWebTemplate: vi.fn(),
    getBuiltinPublicWebTemplates: vi.fn(),
    setBuiltinPublicWebTemplateEnabled: vi.fn()
}))

const permissions = vi.hoisted(() => ({ update: true }))
vi.mock('@/composables/useAuth', () => ({
    useAuth: () => ({ checkPermission: (permission) => permission !== 'CONFIG_PUBLIC_WEB_NODE_UPDATE' || permissions.update })
}))

const mounted = []

async function mountTab() {
    const wrapper = mountWithPlugins(PublicWebTemplatesTab, {
        global: { stubs: { NewPublicWebTemplate: true, VDialog: { template: '<div><slot /></div>' } } }
    })
    mounted.push(wrapper)
    await flushPromises()
    return wrapper
}

const rows = (wrapper) => wrapper.findAll('[data-test="builtin-row"]')
const row = (wrapper, name) => rows(wrapper).find((candidate) => candidate.find('code').text() === name)
const switchOf = (rowWrapper) => rowWrapper.findComponent({ name: 'VSwitch' })

describe('PublicWebTemplatesTab built-in templates', () => {
    beforeEach(() => {
        vi.clearAllMocks()
        permissions.update = true
        vi.mocked(getBuiltinPublicWebTemplates).mockResolvedValue(builtinsResponse())
        vi.mocked(setBuiltinPublicWebTemplateEnabled).mockResolvedValue({ data: {} })
    })
    afterEach(() => {
        while (mounted.length) mounted.pop().unmount()
    })

    it('lists every built-in, with a switch where it can be switched off and no delete anywhere', async () => {
        const wrapper = await mountTab()

        expect(rows(wrapper).map((candidate) => candidate.find('code').text())).toEqual(BUILTINS.map((builtin) => builtin.name))
        for (const name of ['builtin/_macros.html', 'builtin/product_base.html']) {
            expect(row(wrapper, name).find('[data-test="builtin-switch"]').exists()).toBe(false)
            expect(row(wrapper, name).find('[data-test="builtin-always-on"]').exists()).toBe(true)
        }
        expect(switchOf(row(wrapper, 'builtin/item_generic.html')).props('modelValue')).toBe(true)
        expect(switchOf(row(wrapper, 'builtin/item_vulnerability.html')).props('modelValue')).toBe(false)
        expect(wrapper.find('[data-test="builtin-templates"]').findAll('.mdi-delete')).toHaveLength(0)
        expect(row(wrapper, 'builtin/product_vulnerability.html').text()).toContain('admin')
    })

    it('says what a built-in is used for, and what is different while it is off', async () => {
        const wrapper = await mountTab()

        expect(row(wrapper, 'builtin/item_generic.html').text()).toContain('Any other report item of a type without a template of its own.')
        expect(row(wrapper, 'builtin/item_generic.html').find('[data-test="builtin-off-effect"]').exists()).toBe(false)
        expect(row(wrapper, 'builtin/item_vulnerability.html').find('[data-test="builtin-off-effect"]').text()).toBe(
            'Off: these items use the generic template, or are left out if it is off too.'
        )
    })

    it('switches a built-in off at once and re-reads the list quietly', async () => {
        const wrapper = await mountTab()
        vi.mocked(getBuiltinPublicWebTemplates).mockResolvedValue(
            builtinsResponse(
                BUILTINS.map((builtin) => (builtin.name === 'builtin/product_vulnerability.html' ? { ...builtin, enabled: false } : builtin))
            )
        )

        switchOf(row(wrapper, 'builtin/product_vulnerability.html')).vm.$emit('update:modelValue', false)
        await wrapper.vm.$nextTick()

        // Flipped before core answers.
        expect(row(wrapper, 'builtin/product_vulnerability.html').find('[data-test="builtin-off-effect"]').text()).toContain(
            'only products with a template of their own'
        )
        await flushPromises()

        expect(setBuiltinPublicWebTemplateEnabled).toHaveBeenCalledWith('builtin/product_vulnerability.html', false)
        expect(getBuiltinPublicWebTemplates).toHaveBeenCalledTimes(2)
        expect(switchOf(row(wrapper, 'builtin/product_vulnerability.html')).props('modelValue')).toBe(false)
    })

    it('puts the switch back and says so when core refuses', async () => {
        vi.spyOn(console, 'error').mockImplementation(() => undefined)
        const notifications = []
        const listener = (event) => notifications.push(event.detail)
        window.addEventListener('notification', listener)
        vi.mocked(setBuiltinPublicWebTemplateEnabled).mockRejectedValueOnce({ response: { status: 400 } })
        const wrapper = await mountTab()

        switchOf(row(wrapper, 'builtin/item_generic.html')).vm.$emit('update:modelValue', false)
        await flushPromises()
        window.removeEventListener('notification', listener)

        expect(switchOf(row(wrapper, 'builtin/item_generic.html')).props('modelValue')).toBe(true)
        expect(notifications).toEqual([{ type: 'error', loc: 'common.error_updating' }])
    })

    it('keeps the switches read-only without the update permission', async () => {
        permissions.update = false
        const wrapper = await mountTab()

        expect(switchOf(row(wrapper, 'builtin/item_generic.html')).props('disabled')).toBe(true)
    })

    it('shows the source of a built-in', async () => {
        const wrapper = await mountTab()

        await row(wrapper, 'builtin/item_generic.html').find('[data-test="builtin-view"]').trigger('click')
        await flushPromises()

        const dialog = wrapper.findComponent(BuiltinTemplateDialog)
        expect(dialog.props('modelValue')).toBe(true)
        expect(dialog.find('[data-test="builtin-dialog-name"]').text()).toBe('builtin/item_generic.html')
        const source = dialog.find('[data-test="builtin-dialog-source"] textarea')
        expect(source.element.value).toBe('<div>generic</div>')
        // Shown to read and copy, not to change.
        expect(source.attributes('aria-readonly')).toBe('true')
    })

    it('says which webs each custom template is for, and hands the dialog the webs', async () => {
        const webs = [
            { id: 5, name: 'Cyberfeed' },
            { id: 6, name: 'Partners' }
        ]
        vi.mocked(getAllPublicWebTemplates).mockResolvedValueOnce({
            data: {
                total_count: 2,
                items: [
                    { id: 3, name: 'Bulletin page', product_preset_id: 1, public_web_ids: [], web_names: [] },
                    { id: 4, name: 'Cyberfeed bulletin', product_preset_id: 1, public_web_ids: [5, 6], web_names: ['Cyberfeed', 'Partners'] }
                ],
                public_webs: webs
            }
        })
        const wrapper = await mountTab()

        expect(wrapper.findAll('[data-test="template-webs-cell"]').map((cell) => cell.text())).toEqual(['Every web', 'Cyberfeed, Partners'])
        expect(wrapper.findComponent({ name: 'NewPublicWebTemplate' }).props('publicWebs')).toEqual(webs)
    })

    it('narrows the built-ins with the search', async () => {
        const wrapper = await mountTab()

        wrapper.findComponent({ name: 'ToolbarFilter' }).vm.$emit('update-filter', { search: 'GENERIC' })
        await flushPromises()

        expect(rows(wrapper).map((candidate) => candidate.find('code').text())).toEqual(['builtin/item_generic.html'])
    })
})

describe('BuiltinTemplateDialog', () => {
    afterEach(() => {
        while (mounted.length) mounted.pop().unmount()
    })

    it('copies the source, and says when the clipboard refuses', async () => {
        const writeText = vi.fn().mockResolvedValueOnce(undefined).mockRejectedValueOnce(new Error('denied'))
        vi.stubGlobal('navigator', { ...navigator, clipboard: { writeText } })
        const wrapper = mountWithPlugins(BuiltinTemplateDialog, {
            props: { modelValue: true, template: BUILTINS[1], usedFor: 'Any other report item' },
            global: { stubs: { VDialog: { template: '<div><slot /></div>' } } }
        })
        mounted.push(wrapper)

        await wrapper.find('[data-test="builtin-dialog-copy"]').trigger('click')
        await flushPromises()
        expect(writeText).toHaveBeenCalledWith('<div>generic</div>')
        expect(wrapper.find('[data-test="builtin-dialog-copy"]').text()).toBe('Copied')

        await wrapper.find('[data-test="builtin-dialog-copy"]').trigger('click')
        await flushPromises()
        expect(wrapper.text()).toContain('Copying failed.')
        vi.unstubAllGlobals()
    })
})
