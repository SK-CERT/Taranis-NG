import { describe, it, expect, vi } from 'vitest'
import { mountWithPlugins } from '../helpers/mount-helpers'
import ActionButton from '@/components/common/buttons/ActionButton.vue'

describe('ActionButton', () => {
  // ── Predefined Actions ────────────────────────
  describe('predefined actions', () => {
    it.each([
      ['delete', 'mdi-delete-outline', 'error'],
      ['edit', 'mdi-pencil', 'primary'],
      ['publish', 'mdi-file-outline', 'info'],
      ['remove', 'mdi-minus-thick', 'accent'],
      ['open', 'mdi-open-in-new', 'primary'],
      ['open_source', 'mdi-open-in-app', 'primary'],
      ['lock', 'mdi-lock-outline', 'warning']
    ])('action="%s" should render icon %s with color %s', (action, expectedIcon, expectedColor) => {
      const wrapper = mountWithPlugins(ActionButton, {
        props: { action }
      })

      // Vuetify 4 renders icon name in the HTML (class or text depending on version)
      expect(wrapper.html()).toContain(expectedIcon)

      const btn = wrapper.findComponent({ name: 'VBtn' })
      expect(btn.props('color')).toBe(expectedColor)
    })
  })

  // ── Custom Props ──────────────────────────────
  describe('custom props', () => {
    it('should use custom icon and color when no action', () => {
      const wrapper = mountWithPlugins(ActionButton, {
        props: { icon: 'mdi-star', color: 'success' }
      })

      expect(wrapper.html()).toContain('mdi-star')
      const btn = wrapper.findComponent({ name: 'VBtn' })
      expect(btn.props('color')).toBe('success')
    })

    it('should use default icon/color when no action or custom props', () => {
      const wrapper = mountWithPlugins(ActionButton, { props: {} })

      expect(wrapper.html()).toContain('mdi-help')
      const btn = wrapper.findComponent({ name: 'VBtn' })
      expect(btn.props('color')).toBe('primary')
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
