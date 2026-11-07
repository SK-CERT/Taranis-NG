import { flushPromises } from '@vue/test-utils'
import { defineComponent, h } from 'vue'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mountWithPlugins } from '../helpers/mount-helpers'
import NewProductPreset from '@/components/config/product-presets/NewProductPreset.vue'
import MdiIconPicker from '@/components/common/MdiIconPicker.vue'
import { createProductPreset, getProductPresetOptions, updateProductPreset } from '@/api/config'
import { DEFAULT_PRODUCT_ICON, deliveriesToRows, newFormatRow, OWN_LANGUAGE, rowsToDeliveries } from '@/types/product-presets'

vi.mock('@/api/config', () => ({
    createProductPreset: vi.fn(),
    updateProductPreset: vi.fn(),
    getProductPresetOptions: vi.fn()
}))

vi.mock('@/composables/useAuth', () => ({
    useAuth: () => ({ checkPermission: () => true })
}))

const VDialogStub = {
    name: 'VDialog',
    template: '<div><slot name="activator" :props="{}" /><slot /></div>'
}

const VFormStub = defineComponent({
    name: 'VForm',
    setup(_, { expose, slots }) {
        expose({ validate: () => Promise.resolve({ valid: true }) })
        return () => h('form', slots['default']?.())
    }
})

const OPTIONS = {
    formats: [
        { id: 1, title: 'e-mail CZ' },
        { id: 2, title: 'JSON' },
        { id: 3, title: 'PDF' },
        { id: 4, title: 'Mastodon post CZ' }
    ],
    channels: [
        { id: 'mail-1', name: 'VAMP' },
        { id: 'mail-2', name: 'jen JARA' },
        { id: 'sftp', name: 'va2am dev' },
        { id: 'mastodon', name: 'MastodonCzech' }
    ],
    public_webs: [
        { id: 1, name: 'Cyberfeed' },
        { id: 3, name: 'Other' }
    ]
}

// A delivery: the product in a language (null: its own) and a format, to a channel.
const pair = (product_format_id, publishing_channel_id, language = null) => ({ language, product_format_id, publishing_channel_id })
const row = (uid, product_format_id, channel_ids, language = OWN_LANGUAGE) => ({ uid, language, product_format_id, channel_ids })

const mounted = []

async function mountDialog(editItem = null) {
    const wrapper = mountWithPlugins(NewProductPreset, {
        props: { editItem },
        global: {
            stubs: {
                VDialog: VDialogStub,
                VForm: VFormStub,
                UnsavedChangesDialog: true
            }
        }
    })
    mounted.push(wrapper)
    await flushPromises()
    return wrapper
}

describe('product preset rows', () => {
    it('groups deliveries into one row per language and format, in order', () => {
        const rows = deliveriesToRows([pair(2, 'sftp'), pair(1, 'mail-1'), pair(1, 'mail-2'), pair(4, null), pair(3, 'sftp')])

        expect(rows.map((row) => [row.product_format_id, row.channel_ids])).toEqual([
            [2, ['sftp']],
            [1, ['mail-1', 'mail-2']],
            [4, []],
            [3, ['sftp']]
        ])
    })

    it('turns rows back into format-to-channel pairs, a channel-less row into a format-only delivery', () => {
        const rows = [row(1, 2, ['sftp']), row(2, 1, ['mail-1', 'mail-2']), row(3, 4, []), newFormatRow()]

        expect(rowsToDeliveries(rows)).toEqual([pair(2, 'sftp'), pair(1, 'mail-1'), pair(1, 'mail-2'), pair(4, null)])
    })

    it('keeps the languages of one format apart: Cyberfeed', () => {
        // Czech to two Mastodon accounts, English and Czech to one address, Slovak as PDF and HTML.
        const deliveries = [
            pair(4, 'mastodon', 'cs'),
            pair(4, 'mastodon-sk', 'cs'),
            pair(4, 'mail-1', 'en'),
            pair(4, 'mail-1', 'cs'),
            pair(3, 'sftp', 'sk'),
            pair(5, 'sftp', 'sk')
        ]

        const rows = deliveriesToRows(deliveries)

        expect(rows.map((entry) => [entry.language, entry.product_format_id, entry.channel_ids])).toEqual([
            ['cs', 4, ['mastodon', 'mastodon-sk', 'mail-1']],
            ['en', 4, ['mail-1']],
            ['sk', 3, ['sftp']],
            ['sk', 5, ['sftp']]
        ])
        expect(rowsToDeliveries(rows)).toEqual([
            pair(4, 'mastodon', 'cs'),
            pair(4, 'mastodon-sk', 'cs'),
            pair(4, 'mail-1', 'cs'),
            pair(4, 'mail-1', 'en'),
            pair(3, 'sftp', 'sk'),
            pair(5, 'sftp', 'sk')
        ])
    })

    it('starts a row in the language the product is written in', () => {
        expect(newFormatRow().language).toBe(OWN_LANGUAGE)
        expect(deliveriesToRows([pair(1, 'sftp')])[0].language).toBe(OWN_LANGUAGE)
    })
})

describe('NewProductPreset', () => {
    beforeEach(() => {
        vi.clearAllMocks()
        vi.mocked(getProductPresetOptions).mockResolvedValue({ data: OPTIONS })
        vi.mocked(createProductPreset).mockResolvedValue({ data: { id: 9 } })
        vi.mocked(updateProductPreset).mockResolvedValue({ data: { id: 5 } })
    })

    afterEach(() => {
        mounted.splice(0).forEach((wrapper) => wrapper.unmount())
    })

    it('saves one format to two addresses, two formats to one SFTP and a Mastodon post as pairs', async () => {
        const wrapper = await mountDialog()
        wrapper.vm.openCreateDialog()
        wrapper.vm.localItem.name = 'Vulnerability advisory'
        wrapper.vm.rows = [row(1, 2, ['sftp']), row(2, 3, ['sftp']), row(3, 1, ['mail-1', 'mail-2']), row(4, 4, ['mastodon'])]

        expect(await wrapper.vm.persist()).toBe(true)

        const payload = vi.mocked(createProductPreset).mock.calls[0][0]
        expect(payload).toMatchObject({ id: -1, name: 'Vulnerability advisory', public_web_enabled: false, public_web_ids: [] })
        expect(payload.deliveries).toEqual([pair(2, 'sftp'), pair(3, 'sftp'), pair(1, 'mail-1'), pair(1, 'mail-2'), pair(4, 'mastodon')])
        expect(wrapper.emitted('saved')).toHaveLength(1)
    })

    it('loads a product preset into rows and saves its edits, public web targets included', async () => {
        const wrapper = await mountDialog({
            id: 5,
            name: 'Advisory',
            description: null,
            public_web_enabled: true,
            public_web_ids: [3],
            deliveries: [
                { id: 1, product_format_id: 1, publishing_channel_id: 'mail-1' },
                { id: 2, product_format_id: 1, publishing_channel_id: 'mail-2' },
                { id: 3, product_format_id: 4, publishing_channel_id: null }
            ]
        })

        expect(wrapper.vm.rows.map((row) => [row.product_format_id, row.channel_ids])).toEqual([
            [1, ['mail-1', 'mail-2']],
            [4, []]
        ])
        expect(wrapper.text()).toContain('Other')

        wrapper.vm.rows[0].channel_ids = ['mail-2']
        wrapper.vm.moveRow(1, -1)
        expect(await wrapper.vm.persist()).toBe(true)

        const payload = vi.mocked(updateProductPreset).mock.calls[0][0]
        expect(payload).toMatchObject({ id: 5, description: '', public_web_enabled: true, public_web_ids: [3] })
        expect(payload.deliveries).toEqual([pair(4, null), pair(1, 'mail-2')])
    })

    it('stores no icon until another one than the default is picked', async () => {
        const wrapper = await mountDialog()
        wrapper.vm.openCreateDialog()
        wrapper.vm.localItem.name = 'Advisory'
        wrapper.vm.rows = [row(1, 2, [])]
        const picker = wrapper.findComponent(MdiIconPicker)
        expect(picker.props('modelValue')).toBe(DEFAULT_PRODUCT_ICON)

        expect(await wrapper.vm.persist()).toBe(true)
        expect(vi.mocked(createProductPreset).mock.calls[0][0].icon).toBeNull()

        picker.vm.$emit('update:modelValue', 'mdi-rss')
        expect(await wrapper.vm.persist()).toBe(true)
        expect(vi.mocked(createProductPreset).mock.calls[1][0].icon).toBe('mdi-rss')
    })

    it("shows the product preset's own icon", async () => {
        const wrapper = await mountDialog({ id: 5, name: 'Advisory', icon: 'mdi-rss', deliveries: [pair(1, 'mail-1')] })

        expect(wrapper.findComponent(MdiIconPicker).props('modelValue')).toBe('mdi-rss')
    })

    it('offers each format on one row of a language only', async () => {
        const wrapper = await mountDialog()
        wrapper.vm.openCreateDialog()
        wrapper.vm.rows = [row(1, 1, []), row(2, null, []), row(3, null, [], 'cs')]

        expect(wrapper.vm.formatItemsFor(wrapper.vm.rows[1]).map((format) => format.id)).toEqual([2, 3, 4])
        expect(wrapper.vm.formatItemsFor(wrapper.vm.rows[0]).map((format) => format.id)).toEqual([1, 2, 3, 4])
        expect(wrapper.vm.formatItemsFor(wrapper.vm.rows[2]).map((format) => format.id)).toEqual([1, 2, 3, 4])
    })

    it("offers the product's own language first, then the languages rows already have", async () => {
        const wrapper = await mountDialog()
        wrapper.vm.openCreateDialog()
        wrapper.vm.rows = [row(1, 1, [], 'sk')]

        const items = wrapper.vm.languageItems
        expect(items[0]).toEqual({ title: "The product's language", value: OWN_LANGUAGE })
        expect(items.map((item) => item.value)).toContain('sk')
    })

    it('saves the language of each row', async () => {
        const wrapper = await mountDialog()
        wrapper.vm.openCreateDialog()
        wrapper.vm.localItem.name = 'Cyberfeed'
        wrapper.vm.rows = [row(1, 4, ['mastodon'], 'cs'), row(2, 4, ['mail-1'], 'en'), row(3, 2, ['sftp'])]

        expect(await wrapper.vm.persist()).toBe(true)

        expect(vi.mocked(createProductPreset).mock.calls[0][0].deliveries).toEqual([
            pair(4, 'mastodon', 'cs'),
            pair(4, 'mail-1', 'en'),
            pair(2, 'sftp')
        ])
    })

    it('asks for a format or the public web before saving', async () => {
        const wrapper = await mountDialog()
        wrapper.vm.openCreateDialog()
        wrapper.vm.localItem.name = 'Empty'
        wrapper.vm.removeRow(0)

        expect(await wrapper.vm.persist()).toBe(false)
        await flushPromises()

        expect(createProductPreset).not.toHaveBeenCalled()
        expect(wrapper.text()).toContain('Add a format, or show the products on the public web.')

        wrapper.vm.localItem.public_web_enabled = true
        wrapper.vm.localItem.public_web_ids = [1]
        expect(await wrapper.vm.persist()).toBe(true)
        expect(vi.mocked(createProductPreset).mock.calls[0][0]).toMatchObject({ deliveries: [], public_web_ids: [1] })
    })

    it('drops the web targets of a product preset taken off the public web', async () => {
        const wrapper = await mountDialog({
            id: 5,
            name: 'Advisory',
            public_web_enabled: true,
            public_web_ids: [1],
            deliveries: [pair(2, 'sftp')]
        })
        wrapper.vm.localItem.public_web_enabled = false

        await wrapper.vm.persist()

        expect(vi.mocked(updateProductPreset).mock.calls[0][0]).toMatchObject({ public_web_enabled: false, public_web_ids: [] })
    })

    it('shows why the server refused to save', async () => {
        vi.mocked(createProductPreset).mockRejectedValue({
            response: { status: 400, data: { error: "A product preset named 'Advisory' already exists." } }
        })
        const wrapper = await mountDialog()
        wrapper.vm.openCreateDialog()
        wrapper.vm.localItem.name = 'Advisory'
        wrapper.vm.rows = [row(1, 2, [])]

        expect(await wrapper.vm.persist()).toBe(false)
        await flushPromises()

        expect(wrapper.text()).toContain('Could not save the product')
        expect(wrapper.text()).toContain("A product preset named 'Advisory' already exists.")
        expect(wrapper.emitted('saved')).toBeUndefined()
    })
})
