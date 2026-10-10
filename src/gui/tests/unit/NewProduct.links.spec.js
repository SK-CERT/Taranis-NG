import { flushPromises } from '@vue/test-utils'
import { defineComponent, h } from 'vue'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mountWithPlugins } from '../helpers/mount-helpers'
import NewProduct from '@/components/publish/NewProduct.vue'
import { getProductById, getPublishPublicWebs, updateProduct } from '@/api/publish'

vi.mock('@/api/publish', () => ({
    getAllProducts: vi.fn(),
    createProduct: vi.fn(),
    updateProduct: vi.fn(),
    publishProduct: vi.fn(),
    previewProduct: vi.fn(),
    getProductById: vi.fn(),
    getPublishPublicWebs: vi.fn()
}))

vi.mock('@/api/config', () => ({
    getAllPublicWebNodes: vi.fn(),
    getPublicWebs: vi.fn()
}))

vi.mock('@/api/user', () => ({
    getAllUserProductTypes: vi.fn().mockResolvedValue({ data: { items: [] } }),
    getAllUserPublishersPresets: vi.fn().mockResolvedValue({ data: { items: [] } })
}))

vi.mock('@/api/state', () => ({
    getEntityTypeStates: vi.fn().mockResolvedValue({ data: { states: [] } })
}))

vi.mock('@/composables/useAuth', () => ({
    useAuth: () => ({ checkPermission: vi.fn().mockReturnValue(true) })
}))

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

const BLOG = 'https://blog.example/post'
const VENDOR = 'https://vendor.example/advisory'
const NVD = 'https://nvd.nist.gov/vuln/detail/CVE-2026-0001'

const productDetail = (overrides = {}) => ({
    id: 5,
    title: 'Bulletin',
    description: 'Intro',
    product_type_id: 1,
    public_web_ids: [],
    links: [{ key: 'prod01', url: BLOG }],
    report_items: [
        {
            id: 9,
            title: 'Vendor advisory',
            links: [
                { key: 'rep1aa', url: VENDOR },
                { key: 'rep1bb', url: NVD }
            ]
        }
    ],
    ...overrides
})

// Every mounted dialog listens on window, so one left mounted would answer the next test's events.
let mounted = null

async function openProduct(detail) {
    vi.mocked(getProductById).mockResolvedValue({ data: detail })
    const wrapper = mountWithPlugins(NewProduct, {
        global: {
            stubs: {
                VDialog: { name: 'VDialog', template: '<div><slot /></div>' },
                VForm: VFormStub,
                VMenu: VMenuStub,
                ConfirmationDialog: true,
                StateSelector: true,
                ReportItemSelector: true
            }
        }
    })
    mounted = wrapper
    await flushPromises()
    window.dispatchEvent(new CustomEvent('show-product-edit', { detail: { id: detail.id, modify: true, access: true } }))
    await flushPromises()
    return wrapper
}

const lastSaved = () => vi.mocked(updateProduct).mock.calls.at(-1)?.[0]

describe('NewProduct links', () => {
    beforeEach(() => {
        vi.clearAllMocks()
        vi.mocked(getPublishPublicWebs).mockResolvedValue({ data: { total_count: 0, items: [] } })
        vi.mocked(updateProduct).mockResolvedValue({ data: 5 })
    })

    afterEach(() => {
        mounted?.unmount()
        mounted = null
    })

    it('shows the product links numbered first and saves them with their keys', async () => {
        const wrapper = await openProduct(productDetail())

        const rows = wrapper.findAll('[data-test="link-row"]')
        expect(rows).toHaveLength(1)
        expect(rows[0].find('.link-list__number').text()).toBe('[1]')

        await wrapper.find('[data-test="link-add"]').trigger('click')
        await wrapper.vm.handleSave()

        // The empty row just added is not saved.
        expect(lastSaved().links).toEqual([{ key: 'prod01', url: BLOG }])
    })

    it('cites a report link by copying it into the product links', async () => {
        const wrapper = await openProduct(productDetail())

        const reportLinks = wrapper.findAll('[data-test="cite-external-link"]')
        expect(reportLinks.map((item) => item.text())).toEqual(['vendor.example/advisory', 'nvd.nist.gov/vuln/detail/CVE-2026-0001'])

        await reportLinks[1].trigger('click')
        await flushPromises()

        const saved = lastSaved()
        expect(saved.links).toHaveLength(2)
        expect(saved.links[0]).toEqual({ key: 'prod01', url: BLOG })
        expect(saved.links[1].url).toBe(NVD)
        expect(saved.description).toBe(`Intro [#${saved.links[1].key}]`)
        expect(wrapper.findAll('[data-test="link-row"]')).toHaveLength(2)
    })

    it('reuses the product link when the cited report link is already one', async () => {
        const wrapper = await openProduct(productDetail({ links: [{ key: 'prod01', url: NVD }] }))

        await wrapper.findAll('[data-test="cite-external-link"]')[1].trigger('click')
        await flushPromises()

        expect(lastSaved().links).toEqual([{ key: 'prod01', url: NVD }])
        expect(lastSaved().description).toBe('Intro [#prod01]')
    })

    it('resolves citations of report links in the description, numbered after the product links', async () => {
        const wrapper = await openProduct(productDetail({ description: 'Our note [#prod01], NVD [#rep1bb].' }))

        const chips = wrapper.findAll('[data-test="reference-preview"] [data-test="reference-chip"]').map((chip) => chip.text())
        expect(chips).toEqual(['[1]blog.example/post', '[3]nvd.nist.gov/vuln/detail/CVE-2026-0001'])
        expect(wrapper.find('[data-test="reference-missing"]').exists()).toBe(false)
    })
})
