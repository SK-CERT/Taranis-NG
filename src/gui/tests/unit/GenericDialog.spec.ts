/* eslint-disable vue/one-component-per-file -- compact test-only Vuetify stubs */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent } from 'vue'
import { mount } from '@vue/test-utils'
import GenericDialog from '@/components/common/GenericDialog.vue'

const { tMock } = vi.hoisted(() => ({
    tMock: vi.fn((key: string, params?: { title?: string }) => (params?.title ? `${key}: ${params.title}` : key))
}))

vi.mock('vue-i18n', () => ({
    useI18n: () => ({ t: tMock })
}))

const passthroughStub = defineComponent({ template: '<div><slot /></div>' })
const DialogToolbarStub = defineComponent({
    name: 'DialogToolbar',
    props: {
        title: { type: String, required: true },
        saving: { type: Boolean, default: false }
    },
    template: '<div data-test="dialog-title">{{ title }}</div>'
})

const mountDialog = (props: Record<string, unknown>) =>
    mount(GenericDialog, {
        props: {
            modelValue: true,
            item: {},
            ...props
        },
        global: {
            stubs: {
                VDialog: passthroughStub,
                VCard: passthroughStub,
                VCardText: passthroughStub,
                VForm: passthroughStub,
                VAlert: passthroughStub,
                AddNewButton: true,
                DialogToolbar: DialogToolbarStub
            }
        }
    })

describe('GenericDialog title composition', () => {
    beforeEach(() => {
        vi.clearAllMocks()
    })

    it('uses the explicit edit title unchanged', () => {
        const wrapper = mountDialog({ isEdit: true, title: 'Provider', editTitle: 'Update provider' })

        expect(wrapper.find('[data-test="dialog-title"]').text()).toBe('Update provider')
        expect(tMock).not.toHaveBeenCalledWith('common.edit_named', expect.anything())
    })

    it('uses one reorderable message and bidi-isolates the dynamic title', () => {
        const wrapper = mountDialog({ isEdit: true, title: 'مزود الهوية' })

        expect(tMock).toHaveBeenCalledWith('common.edit_named', {
            title: '\u2068مزود الهوية\u2069'
        })
        expect(wrapper.find('[data-test="dialog-title"]').text()).toBe('common.edit_named: \u2068مزود الهوية\u2069')
    })
})
