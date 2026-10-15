import { flushPromises } from '@vue/test-utils'
import { defineComponent, h } from 'vue'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mountWithPlugins } from '../helpers/mount-helpers'
import NewProduct from '@/components/publish/NewProduct.vue'
import StateSelector from '@/components/common/StateSelector.vue'
import ReportItemSelector from '@/components/publish/ReportItemSelector.vue'
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

const PUBLISHED = 1
const WORK_IN_PROGRESS = 2

vi.mock('@/api/state', () => ({
    getEntityTypeStates: vi.fn().mockResolvedValue({
        data: {
            states: [
                { id: 2, display_name: 'work_in_progress', state_type: 'initial', is_default: true },
                { id: 1, display_name: 'published', state_type: 'final' }
            ]
        }
    })
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

const inProgress = { name: 'work_in_progress', display_name: 'work_in_progress' }
const completed = { name: 'completed', display_name: 'completed' }

const productDetail = (stateId, reportState) => ({
    id: 1016,
    title: 'whatever',
    description: '',
    product_type_id: 1,
    state_id: stateId,
    public_web_ids: [],
    links: [],
    report_items: [{ id: 3193, title: 'blbost', state_id: reportState === completed ? 3 : 2, state: reportState }]
})

// Every mounted dialog listens on window, so one left mounted would answer the next test's events.
let mounted = null

async function openProduct() {
    vi.mocked(getProductById).mockResolvedValueOnce({ data: productDetail(WORK_IN_PROGRESS, inProgress) })
    const wrapper = mountWithPlugins(NewProduct, {
        global: {
            stubs: {
                VDialog: { name: 'VDialog', template: '<div><slot /></div>' },
                VForm: VFormStub,
                ConfirmationDialog: true,
                StateSelector: true,
                ReportItemSelector: true,
                LinkListEditor: true,
                CiteMenu: true,
                ReferencePreview: true
            }
        }
    })
    mounted = wrapper
    await flushPromises()
    window.dispatchEvent(new CustomEvent('show-product-edit', { detail: { id: 1016, modify: true, access: true } }))
    await flushPromises()
    return wrapper
}

const shownReportStates = (wrapper) =>
    wrapper
        .findComponent(ReportItemSelector)
        .props('values')
        .map((item) => item.state.display_name)

describe('NewProduct report states', () => {
    beforeEach(() => {
        vi.clearAllMocks()
        vi.mocked(getPublishPublicWebs).mockResolvedValue({ data: { total_count: 0, items: [] } })
        vi.mocked(updateProduct).mockResolvedValue({ data: 1016 })
    })

    afterEach(() => {
        mounted?.unmount()
        mounted = null
    })

    it('shows the reports completed once the product is set to a final state', async () => {
        const wrapper = await openProduct()
        expect(shownReportStates(wrapper)).toEqual(['work_in_progress'])

        // The server completed the reports while saving the published product.
        vi.mocked(getProductById).mockResolvedValueOnce({ data: productDetail(PUBLISHED, completed) })
        wrapper.findComponent(StateSelector).vm.$emit('update:model-value', PUBLISHED)
        await flushPromises()

        expect(updateProduct).toHaveBeenCalledOnce()
        expect(updateProduct.mock.calls[0][0].state_id).toBe(PUBLISHED)
        expect(shownReportStates(wrapper)).toEqual(['completed'])
    })

    it('does not reload the reports when the product is saved in a non-final state', async () => {
        const wrapper = await openProduct()

        wrapper.findComponent(StateSelector).vm.$emit('update:model-value', WORK_IN_PROGRESS)
        await flushPromises()

        expect(updateProduct).toHaveBeenCalledOnce()
        // Only the load that opened the dialog.
        expect(getProductById).toHaveBeenCalledOnce()
        expect(shownReportStates(wrapper)).toEqual(['work_in_progress'])
    })
})
