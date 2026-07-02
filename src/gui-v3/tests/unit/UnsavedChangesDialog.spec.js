import { describe, it, expect } from 'vitest'
import { mountWithPlugins } from '../helpers/mount-helpers'
import UnsavedChangesDialog from '@/components/common/dialogs/UnsavedChangesDialog.vue'

// Stub VDialog to render inline (avoids teleport/overlay issues in happy-dom)
const VDialogStub = {
    name: 'VDialog',
    props: ['modelValue', 'maxWidth'],
    template: '<div class="v-dialog-stub"><slot /></div>',
    emits: ['update:modelValue']
}

function mountDialog(props = {}) {
    return mountWithPlugins(UnsavedChangesDialog, {
        props: { modelValue: true, ...props },
        global: { stubs: { VDialog: VDialogStub } }
    })
}

const buttons = (wrapper) => wrapper.findAllComponents({ name: 'VBtn' })
const buttonByColor = (wrapper, color) => buttons(wrapper).find((b) => b.props('color') === color)

describe('UnsavedChangesDialog', () => {
    // ── Rendering ─────────────────────────────────
    describe('rendering', () => {
        it('renders the title and the default message', () => {
            const wrapper = mountDialog()
            expect(wrapper.text()).toContain('Unsaved Changes')
            expect(wrapper.text()).toContain('You have unsaved changes')
        })

        it('renders the three action buttons', () => {
            const wrapper = mountDialog()
            expect(wrapper.text()).toContain('Continue editing')
            expect(wrapper.text()).toContain('Save and Close')
            expect(wrapper.text()).toContain('Close without saving')
        })

        it('renders a custom message when provided', () => {
            const wrapper = mountDialog({ message: 'Custom warning text' })
            expect(wrapper.text()).toContain('Custom warning text')
            expect(wrapper.text()).not.toContain('You have unsaved changes')
        })
    })

    // ── Events ────────────────────────────────────
    describe('events', () => {
        it('emits continue when "Continue editing" is clicked', async () => {
            const wrapper = mountDialog()
            await buttonByColor(wrapper, 'primary').trigger('click')
            expect(wrapper.emitted('continue')).toHaveLength(1)
        })

        it('emits save when "Save and Close" is clicked', async () => {
            const wrapper = mountDialog()
            await buttonByColor(wrapper, 'success').trigger('click')
            expect(wrapper.emitted('save')).toHaveLength(1)
        })

        it('emits discard when "Close without saving" is clicked', async () => {
            const wrapper = mountDialog()
            await buttonByColor(wrapper, 'error').trigger('click')
            expect(wrapper.emitted('discard')).toHaveLength(1)
        })
    })

    // ── Props ─────────────────────────────────────
    describe('props', () => {
        it('passes maxWidth through to VDialog', () => {
            const wrapper = mountDialog()
            expect(wrapper.findComponent(VDialogStub).props('maxWidth')).toBe('500px')
        })
    })
})
