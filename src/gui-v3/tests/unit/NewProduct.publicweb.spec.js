import { flushPromises } from '@vue/test-utils'
import { defineComponent, h } from 'vue'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mountWithPlugins } from '../helpers/mount-helpers'
import { createTestStore } from '../helpers/store-helpers'
import NewProduct from '@/components/publish/NewProduct.vue'
import { getPublishPublicWebs, updateProduct, getProductById } from '@/api/publish'
import { getAllPublicWebNodes, getPublicWebs } from '@/api/config'
import { usePublishStore } from '@/stores/publish'

const validateForm = vi.fn()

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

const VDialogStub = {
    name: 'VDialog',
    template: '<div><slot /></div>'
}

const VFormStub = defineComponent({
    name: 'VForm',
    setup(_, { expose, slots }) {
        expose({ validate: () => validateForm() })
        return () => h('form', slots['default']?.())
    }
})

function mountNewProduct() {
    return mountWithPlugins(NewProduct, {
        global: {
            stubs: {
                VDialog: VDialogStub,
                VForm: VFormStub,
                ConfirmationDialog: true,
                StateSelector: true,
                ReportItemSelector: true
            }
        }
    })
}

describe('NewProduct public-web targeting', () => {
    beforeEach(() => {
        vi.clearAllMocks()
        validateForm.mockResolvedValue({ valid: true })
    })

    it('fetches the target list exactly once on mount instead of once per node', async () => {
        vi.mocked(getPublishPublicWebs).mockResolvedValue({
            data: {
                total_count: 2,
                items: [
                    { id: 3, name: 'Alpha' },
                    { id: 4, name: 'Beta' }
                ]
            }
        })

        mountNewProduct()
        await flushPromises()

        expect(getPublishPublicWebs).toHaveBeenCalledOnce()
        expect(getAllPublicWebNodes).not.toHaveBeenCalled()
        expect(getPublicWebs).not.toHaveBeenCalled()
    })

    it('keeps the saved public-web targeting when the options request fails', async () => {
        vi.spyOn(console, 'error').mockImplementation(() => {})
        vi.mocked(getPublishPublicWebs).mockRejectedValue(new Error('insufficient permissions'))
        vi.mocked(getProductById).mockResolvedValue({
            data: { id: 5, title: 'Quarterly report', description: '', product_type_id: 1, report_items: [], public_web_ids: [3, 4] }
        })
        vi.mocked(updateProduct).mockResolvedValue({ data: 5 })
        const wrapper = mountNewProduct()
        await flushPromises()

        window.dispatchEvent(new CustomEvent('show-product-edit', { detail: { id: 5, modify: true, access: true } }))
        await flushPromises()

        await wrapper.vm.handleSave()

        expect(updateProduct).toHaveBeenCalledOnce()
        expect(updateProduct.mock.calls[0][0].public_web_ids).toEqual([3, 4])
    })

    it('does not render the target selector when the store reports no options', async () => {
        vi.mocked(getPublishPublicWebs).mockResolvedValue({ data: { total_count: 0, items: [] } })

        const wrapper = mountNewProduct()
        await flushPromises()

        expect(usePublishStore().publicWebEnabled).toBe(false)
        expect(wrapper.text()).not.toContain('Public Websites')
    })

    it('renders the target selector with every web once several exist', async () => {
        vi.mocked(getPublishPublicWebs).mockResolvedValue({
            data: {
                total_count: 2,
                items: [
                    { id: 3, name: 'Alpha' },
                    { id: 4, name: 'Beta' }
                ]
            }
        })

        const wrapper = mountNewProduct()
        await flushPromises()

        expect(usePublishStore().publicWebEnabled).toBe(true)
        expect(wrapper.text()).toContain('Public Websites')
        expect(wrapper.text()).toContain('Alpha')
        expect(wrapper.text()).toContain('Beta')
    })

    it('caches the options so a repeated load does not re-request', async () => {
        vi.mocked(getPublishPublicWebs).mockResolvedValue({ data: { total_count: 1, items: [{ id: 3, name: 'Alpha' }] } })
        const { store } = createTestStore(usePublishStore)

        await store.loadPublicWebOptions()
        await store.loadPublicWebOptions()

        expect(getPublishPublicWebs).toHaveBeenCalledOnce()
        expect(store.publicWebOptions).toEqual([{ id: 3, name: 'Alpha' }])
        expect(store.publicWebEnabled).toBe(true)
    })

    it('shares one in-flight request between concurrent loads instead of firing two', async () => {
        let resolveFetch
        vi.mocked(getPublishPublicWebs).mockReturnValue(
            new Promise((resolve) => {
                resolveFetch = resolve
            })
        )
        const { store } = createTestStore(usePublishStore)

        const first = store.loadPublicWebOptions()
        const second = store.loadPublicWebOptions()
        resolveFetch({ data: { total_count: 1, items: [{ id: 3, name: 'Alpha' }] } })
        await Promise.all([first, second])

        expect(getPublishPublicWebs).toHaveBeenCalledOnce()
        expect(store.publicWebOptions).toEqual([{ id: 3, name: 'Alpha' }])
    })

    it('refetches after invalidation so a deleted web disappears from the options', async () => {
        vi.mocked(getPublishPublicWebs)
            .mockResolvedValueOnce({
                data: {
                    total_count: 2,
                    items: [
                        { id: 3, name: 'Alpha' },
                        { id: 4, name: 'Beta' }
                    ]
                }
            })
            .mockResolvedValueOnce({ data: { total_count: 1, items: [{ id: 3, name: 'Alpha' }] } })
        const { store } = createTestStore(usePublishStore)

        await store.loadPublicWebOptions()
        expect(store.publicWebOptions).toHaveLength(2)

        store.invalidatePublicWebOptions()
        expect(store.publicWebOptions).toEqual([])

        await store.loadPublicWebOptions()
        expect(getPublishPublicWebs).toHaveBeenCalledTimes(2)
        expect(store.publicWebOptions).toEqual([{ id: 3, name: 'Alpha' }])
    })

    it('retries after a failed load and recovers on the next call', async () => {
        vi.spyOn(console, 'error').mockImplementation(() => {})
        vi.mocked(getPublishPublicWebs).mockRejectedValueOnce(new Error('boom'))
        vi.mocked(getPublishPublicWebs).mockResolvedValueOnce({ data: { total_count: 1, items: [{ id: 3, name: 'Alpha' }] } })
        const { store } = createTestStore(usePublishStore)

        await store.loadPublicWebOptions()
        expect(store.publicWebOptions).toEqual([])
        expect(store.publicWebEnabled).toBe(false)

        await store.loadPublicWebOptions()
        expect(getPublishPublicWebs).toHaveBeenCalledTimes(2)
        expect(store.publicWebOptions).toEqual([{ id: 3, name: 'Alpha' }])
        vi.restoreAllMocks()
    })

    it('drops a deleted web from the saved targeting on edit so the product cannot keep a stale id', async () => {
        // The stale-cache scenario: options were cached with web 4, an admin
        // deleted it elsewhere, the product still targets [3, 4]. Saving this
        // must not send the dead id 4 — the backend would silently drop it and
        // the product would turn global.
        vi.mocked(getPublishPublicWebs).mockResolvedValue({
            data: { total_count: 1, items: [{ id: 3, name: 'Alpha' }] }
        })
        vi.mocked(getProductById).mockResolvedValue({
            data: { id: 5, title: 'Quarterly report', description: '', product_type_id: 1, report_items: [], public_web_ids: [3, 4] }
        })
        vi.mocked(updateProduct).mockResolvedValue({ data: 5 })
        const wrapper = mountNewProduct()
        await flushPromises()

        window.dispatchEvent(new CustomEvent('show-product-edit', { detail: { id: 5, modify: true, access: true } }))
        await flushPromises()

        await wrapper.vm.handleSave()

        expect(updateProduct).toHaveBeenCalledOnce()
        expect(updateProduct.mock.calls[0][0].public_web_ids).toEqual([3])
    })

    it('refills the options on refresh so an invalidation never leaves them empty', async () => {
        vi.mocked(getPublishPublicWebs)
            .mockResolvedValueOnce({
                data: {
                    total_count: 2,
                    items: [
                        { id: 3, name: 'Alpha' },
                        { id: 4, name: 'Beta' }
                    ]
                }
            })
            .mockResolvedValueOnce({
                data: {
                    total_count: 2,
                    items: [
                        { id: 3, name: 'Alpha' },
                        { id: 5, name: 'Gamma' }
                    ]
                }
            })
        const { store } = createTestStore(usePublishStore)

        await store.loadPublicWebOptions()
        await store.refreshPublicWebOptions()

        expect(getPublishPublicWebs).toHaveBeenCalledTimes(2)
        // a bare invalidate would have left this empty
        expect(store.publicWebOptions).toEqual([
            { id: 3, name: 'Alpha' },
            { id: 5, name: 'Gamma' }
        ])
        expect(store.publicWebEnabled).toBe(true)
    })

    it('re-renders the target selector after an invalidation once the dialog is reopened', async () => {
        // The Publish view stays mounted across an SSE resync, so a dialog opened
        // afterwards must not find an empty option list - a new product saved from
        // it would carry no targeting at all, which the backend reads as "every web".
        vi.mocked(getPublishPublicWebs).mockResolvedValue({
            data: {
                total_count: 2,
                items: [
                    { id: 3, name: 'Alpha' },
                    { id: 4, name: 'Beta' }
                ]
            }
        })
        const wrapper = mountNewProduct()
        await flushPromises()

        usePublishStore().invalidatePublicWebOptions()
        await flushPromises()
        expect(wrapper.text()).not.toContain('Alpha')

        wrapper.vm.openDialog()
        await flushPromises()

        expect(getPublishPublicWebs).toHaveBeenCalledTimes(2)
        expect(wrapper.text()).toContain('Alpha')
        expect(wrapper.text()).toContain('Beta')
        // the refill is our own adjustment, not a user edit
        expect(wrapper.vm.hasUnsavedChanges()).toBe(false)
    })

    it('auto-maps every web when editing shows the selector with no explicit targeting', async () => {
        vi.mocked(getPublishPublicWebs).mockResolvedValue({
            data: {
                total_count: 2,
                items: [
                    { id: 3, name: 'Alpha' },
                    { id: 4, name: 'Beta' }
                ]
            }
        })
        vi.mocked(getProductById).mockResolvedValue({
            data: { id: 5, title: 'Quarterly report', description: '', product_type_id: 1, report_items: [], public_web_ids: [] }
        })
        vi.mocked(updateProduct).mockResolvedValue({ data: 5 })
        const wrapper = mountNewProduct()
        await flushPromises()

        window.dispatchEvent(new CustomEvent('show-product-edit', { detail: { id: 5, modify: true, access: true } }))
        await flushPromises()

        await wrapper.vm.handleSave()

        expect(updateProduct).toHaveBeenCalledOnce()
        // Legacy "no explicit mapping = all websites" is made explicit when the
        // selector is rendered, so the selection can be seen and edited.
        expect(updateProduct.mock.calls[0][0].public_web_ids).toEqual([3, 4])
    })
})
