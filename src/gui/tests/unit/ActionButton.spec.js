import { describe, it, expect, vi } from 'vitest'
import { mountWithPlugins } from '../helpers/mount-helpers'
import ActionButton from '@/components/common/buttons/ActionButton.vue'

describe('ActionButton', () => {
    // ── Predefined Actions ────────────────────────
    describe('predefined actions', () => {
        it.each([
            ['delete', 'mdi-delete-outline'],
            ['edit', 'mdi-pencil'],
            ['publish', 'mdi-file-outline'],
            ['remove', 'mdi-minus-thick'],
            ['open', 'mdi-open-in-new'],
            ['open_source', 'mdi-open-in-new'],
            ['lock', 'mdi-lock-outline']
        ])('action="%s" should render icon %s', (action, expectedIcon) => {
            const wrapper = mountWithPlugins(ActionButton, {
                props: { action }
            })

            // Vuetify 4 renders icon name in the HTML (class or text depending on version)
            expect(wrapper.html()).toContain(expectedIcon)
        })
    })

    // ── Custom Props ──────────────────────────────
    describe('custom props', () => {
        it('should use custom icon and color when no action', () => {
            const wrapper = mountWithPlugins(ActionButton, {
                props: { icon: 'mdi-star', color: 'success' }
            })

            expect(wrapper.html()).toContain('mdi-star')
            const icon = wrapper.findComponent({ name: 'VIcon' })
            expect(icon.props('color')).toBe('success')
        })

        it('should use default icon/color when no action or custom props', () => {
            const wrapper = mountWithPlugins(ActionButton, { props: {} })

            expect(wrapper.html()).toContain('mdi-help')
            const icon = wrapper.findComponent({ name: 'VIcon' })
            expect(icon.props('color')).toBe('primary')
        })

        it('should pass size to v-btn', () => {
            const wrapper = mountWithPlugins(ActionButton, {
                props: { action: 'edit', size: 'x-large' }
            })

            const btn = wrapper.findComponent({ name: 'VBtn' })
            expect(btn.props('size')).toBe('x-large')
        })

        it('should pass title to v-btn', () => {
            const wrapper = mountWithPlugins(ActionButton, {
                props: { action: 'delete', title: 'Remove item' }
            })

            const btn = wrapper.findComponent({ name: 'VBtn' })
            expect(btn.attributes('title')).toBe('Remove item')
        })
    })

    // ── Disabled State ────────────────────────────
    describe('disabled state', () => {
        it('should be disabled when disabled prop is true', () => {
            const wrapper = mountWithPlugins(ActionButton, {
                props: { action: 'edit', disabled: true }
            })

            const btn = wrapper.findComponent({ name: 'VBtn' })
            expect(btn.props('disabled')).toBe(true)
        })

        it('lock action should always be disabled', () => {
            const wrapper = mountWithPlugins(ActionButton, {
                props: { action: 'lock' }
            })

            const btn = wrapper.findComponent({ name: 'VBtn' })
            expect(btn.props('disabled')).toBe(true)
        })

        it('should not emit click when disabled', async () => {
            const wrapper = mountWithPlugins(ActionButton, {
                props: { action: 'delete', disabled: true }
            })

            await wrapper.findComponent({ name: 'VBtn' }).trigger('click')
            expect(wrapper.emitted('click')).toBeUndefined()
        })
    })

    // ── Click Events ──────────────────────────────
    describe('click events', () => {
        it('should emit click when clicked and not disabled', async () => {
            const wrapper = mountWithPlugins(ActionButton, {
                props: { action: 'edit' }
            })

            await wrapper.findComponent({ name: 'VBtn' }).trigger('click')
            expect(wrapper.emitted('click')).toHaveLength(1)
        })
    })
})
