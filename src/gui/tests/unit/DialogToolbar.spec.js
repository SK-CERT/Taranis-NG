import { describe, it, expect } from 'vitest'
import { mountWithPlugins } from '../helpers/mount-helpers'
import DialogToolbar from '@/components/common/dialogs/DialogToolbar.vue'

const buttons = (wrapper) => wrapper.findAllComponents({ name: 'VBtn' })

describe('DialogToolbar', () => {
    // ── Rendering ─────────────────────────────────
    it('renders the title', () => {
        const wrapper = mountWithPlugins(DialogToolbar, { props: { title: 'My Dialog' } })
        expect(wrapper.text()).toContain('My Dialog')
    })

    it('shows Cancel and Save by default', () => {
        const wrapper = mountWithPlugins(DialogToolbar, { props: { title: 'X' } })
        expect(buttons(wrapper)).toHaveLength(2)
        expect(wrapper.text()).toContain('Cancel')
        expect(wrapper.text()).toContain('Save')
    })

    it('hides the Save button when showSave is false', () => {
        const wrapper = mountWithPlugins(DialogToolbar, { props: { title: 'X', showSave: false } })
        expect(buttons(wrapper)).toHaveLength(1)
        expect(wrapper.text()).toContain('Cancel')
        expect(wrapper.text()).not.toContain('Save')
    })

    // ── Events ────────────────────────────────────
    it('emits cancel when Cancel is clicked', async () => {
        const wrapper = mountWithPlugins(DialogToolbar, { props: { title: 'X' } })
        await buttons(wrapper)[0].trigger('click')
        expect(wrapper.emitted('cancel')).toHaveLength(1)
    })

    it('emits save when Save is clicked', async () => {
        const wrapper = mountWithPlugins(DialogToolbar, { props: { title: 'X' } })
        await buttons(wrapper)[1].trigger('click')
        expect(wrapper.emitted('save')).toHaveLength(1)
    })

    // ── Saving / disabled states ──────────────────
    it('disables both buttons and shows loading on Save while saving', () => {
        const wrapper = mountWithPlugins(DialogToolbar, { props: { title: 'X', saving: true } })
        const [cancel, save] = buttons(wrapper)
        expect(cancel.props('disabled')).toBe(true)
        expect(save.props('disabled')).toBe(true)
        expect(save.props('loading')).toBe(true)
    })

    it('disables only Save when saveDisabled is true', () => {
        const wrapper = mountWithPlugins(DialogToolbar, { props: { title: 'X', saveDisabled: true } })
        const [cancel, save] = buttons(wrapper)
        expect(cancel.props('disabled')).toBe(false)
        expect(save.props('disabled')).toBe(true)
    })

    it('enables both buttons when idle', () => {
        const wrapper = mountWithPlugins(DialogToolbar, { props: { title: 'X' } })
        const [cancel, save] = buttons(wrapper)
        expect(cancel.props('disabled')).toBe(false)
        expect(save.props('disabled')).toBe(false)
    })
})
