import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { nextTick } from 'vue'
import { mountWithPlugins } from '../helpers/mount-helpers'
import PublishNav from '@/views/nav/PublishNav.vue'
import ToolbarFilterPublish from '@/components/publish/ToolbarFilterPublish.vue'
import ContentDataPublish from '@/components/publish/ContentDataPublish.vue'
import { getAllUserProductPresets } from '@/api/user'
import { getAllProducts } from '@/api/publish'

// The Publish sidebar lists All, then each product preset; the one picked filters the products.

const router = vi.hoisted(() => ({
    push: vi.fn(),
    replace: vi.fn(),
    route: { params: {} as Record<string, string> }
}))

vi.mock('vue-router', async () => {
    const { reactive } = await import('vue')
    router.route = reactive({ params: {} })
    return { useRouter: () => router, useRoute: () => router.route }
})

vi.mock('@/api/user', () => ({
    getAllUserProductPresets: vi.fn()
}))

vi.mock('@/api/publish', async (importOriginal) => ({
    ...(await importOriginal<typeof import('@/api/publish')>()),
    getAllProducts: vi.fn(() => Promise.resolve({ data: { items: [], total_count: 0 } }))
}))

const productPresets = [
    { id: 3, name: 'Advisory', icon: 'mdi-shield-alert' },
    { id: 5, name: 'Weekly bulletin', icon: null }
]

type Wrapper = ReturnType<typeof mountWithPlugins>
let wrapper: Wrapper | undefined

const mountNav = async (params: Record<string, string> = {}): Promise<Wrapper> => {
    router.route.params = params
    wrapper = mountWithPlugins(PublishNav)
    await flushPromises()
    return wrapper
}

const item = (nav: Wrapper, id: string) => nav.get(`[data-group-id="${id}"]`)

beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(getAllUserProductPresets).mockResolvedValue({ data: { total_count: 2, items: productPresets } } as never)
})

afterEach(() => {
    wrapper?.unmount()
    wrapper = undefined
})

describe('PublishNav', () => {
    it('lists All first, then each product preset with its icon', async () => {
        const nav = await mountNav()

        expect(nav.findAll('[data-group-id]').map((node) => node.attributes('data-group-id'))).toEqual(['all', '3', '5'])
        expect(item(nav, 'all').text()).toContain('All Products')
        expect(item(nav, '3').text()).toContain('Advisory')
        expect(item(nav, '3').html()).toContain('mdi-shield-alert')
        expect(item(nav, '5').html()).toContain('mdi-package-variant-closed')
        expect(item(nav, 'all').classes()).toContain('v-list-item--active')
        expect(router.replace).not.toHaveBeenCalled()
    })

    it("highlights the route's product preset and opens the one clicked", async () => {
        const nav = await mountNav({ productPresetId: '3' })

        expect(item(nav, '3').classes()).toContain('v-list-item--active')
        expect(item(nav, 'all').classes()).not.toContain('v-list-item--active')

        await item(nav, '5').trigger('click')
        expect(router.push).toHaveBeenCalledWith('/publish/5')
        await item(nav, 'all').trigger('click')
        expect(router.push).toHaveBeenLastCalledWith('/publish')
    })

    it('lists all products when the route names a product preset the user cannot see', async () => {
        await mountNav({ productPresetId: '9' })

        expect(router.replace).toHaveBeenCalledWith('/publish')
    })
})

describe('ToolbarFilterPublish product preset', () => {
    const filters: Array<Record<string, unknown>> = []
    const collect = (event: Event): void => {
        filters.push((event as CustomEvent).detail)
    }

    beforeEach(() => {
        filters.length = 0
        window.addEventListener('update-products-filter', collect)
    })

    afterEach(() => {
        window.removeEventListener('update-products-filter', collect)
    })

    it("filters by the route's product preset and follows the sidebar, with no select of its own", async () => {
        router.route.params = { productPresetId: '3' }
        wrapper = mountWithPlugins(ToolbarFilterPublish, { global: { stubs: { ToolbarGroup: true, TagFilterMenu: true } } })
        await flushPromises()

        expect(filters.at(-1)?.['product_preset_id']).toBe(3)
        expect(wrapper.find('.v-select').exists()).toBe(false)
        expect(getAllUserProductPresets).not.toHaveBeenCalled()

        router.route.params = { productPresetId: '5' }
        await nextTick()
        expect(filters.at(-1)?.['product_preset_id']).toBe(5)

        router.route.params = {}
        await nextTick()
        expect(filters.at(-1)?.['product_preset_id']).toBeNull()
    })

    it("loads only the route's product preset's products on opening, before any filter arrives", async () => {
        router.route.params = { productPresetId: '3' }
        wrapper = mountWithPlugins(ContentDataPublish)
        await flushPromises()

        expect(vi.mocked(getAllProducts).mock.calls[0]?.[0]).toMatchObject({ filter: { product_preset_id: 3 } })
    })
})
