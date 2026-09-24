import { defineComponent, h } from 'vue'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mountWithPlugins } from '../helpers/mount-helpers'
import NewProduct from '@/components/publish/NewProduct.vue'
import { previewProduct } from '@/api/publish'
import { navigateReservedTabOrCurrentWindow, openBlankTabWithoutOpener } from '@/utils/window'

const validateForm = vi.fn()

vi.mock('@/api/publish', () => ({
    createProduct: vi.fn(),
    updateProduct: vi.fn(),
    publishProduct: vi.fn(),
    previewProduct: vi.fn()
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

vi.mock('@/utils/window', () => ({
    openBlankTabWithoutOpener: vi.fn(),
    navigateReservedTabOrCurrentWindow: vi.fn()
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

function mountPreviewEditor() {
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

describe('NewProduct preview', () => {
    beforeEach(() => {
        vi.clearAllMocks()
    })

    it('reserves the preview tab before asynchronous validation completes and preserves Ctrl-click', async () => {
        let finishValidation: ((result: { valid: boolean }) => void) | undefined
        validateForm.mockReturnValue(
            new Promise((resolve) => {
                finishValidation = resolve
            })
        )
        const previewWindow = { close: vi.fn() } as unknown as Window
        vi.mocked(openBlankTabWithoutOpener).mockReturnValue(previewWindow)
        vi.mocked(previewProduct).mockResolvedValue({ data: { token: 'ticket-123' } } as never)
        const wrapper = mountPreviewEditor()

        const preview = wrapper.vm.handlePreview({ ctrlKey: true } as MouseEvent)

        expect(openBlankTabWithoutOpener).toHaveBeenCalledOnce()
        expect(previewProduct).not.toHaveBeenCalled()

        finishValidation?.({ valid: true })
        await preview

        expect(previewProduct).toHaveBeenCalledWith(expect.any(Object), true, '')
        expect(navigateReservedTabOrCurrentWindow).toHaveBeenCalledWith(previewWindow, '/api/v1/publish/products/preview/ticket-123')
    })

    it('closes the reserved tab when validation fails', async () => {
        validateForm.mockResolvedValue({ valid: false })
        const previewWindow = { close: vi.fn() } as unknown as Window
        vi.mocked(openBlankTabWithoutOpener).mockReturnValue(previewWindow)
        const wrapper = mountPreviewEditor()

        await wrapper.vm.handlePreview()

        expect(previewWindow.close).toHaveBeenCalledOnce()
        expect(previewProduct).not.toHaveBeenCalled()
        expect(navigateReservedTabOrCurrentWindow).not.toHaveBeenCalled()
    })

    it('closes the reserved tab when preview generation fails', async () => {
        validateForm.mockResolvedValue({ valid: true })
        const previewWindow = { close: vi.fn() } as unknown as Window
        vi.mocked(openBlankTabWithoutOpener).mockReturnValue(previewWindow)
        vi.mocked(previewProduct).mockRejectedValue(new Error('preview failed'))
        vi.spyOn(console, 'error').mockImplementation(() => undefined)
        const wrapper = mountPreviewEditor()

        await wrapper.vm.handlePreview()

        expect(previewWindow.close).toHaveBeenCalledOnce()
        expect(navigateReservedTabOrCurrentWindow).not.toHaveBeenCalled()
    })
})
