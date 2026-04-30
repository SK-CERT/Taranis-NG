import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mountWithPlugins } from '../helpers/mount-helpers'
import DeleteConfirmationDialog from '@/components/common/dialogs/ConfirmationDialog.vue'

// Stub VDialog to render inline (avoids teleport/overlay issues in happy-dom)
const VDialogStub = {
  name: 'VDialog',
  props: ['modelValue', 'maxWidth'],
  template: '<div class="v-dialog-stub"><slot /></div>',
  emits: ['update:modelValue']
}

function mountDialog(props = {}, options = {}) {
  return mountWithPlugins(DeleteConfirmationDialog, {
    props: { modelValue: true, message: 'Delete this?', ...props },
    global: {
      stubs: { VDialog: VDialogStub },
      ...(options.global || {})
    },
    ...options
  })
}

describe('DeleteConfirmationDialog', () => {
  // ── Rendering ─────────────────────────────────
  describe('rendering', () => {
    it('should render dialog content when modelValue is true', async () => {
      const wrapper = mountDialog({ message: 'Are you sure?' })

      expect(wrapper.text()).toContain('Are you sure?')
    })

    it('should show error icon in dialog', async () => {
      const wrapper = mountDialog()

      expect(wrapper.html()).toContain('mdi-alert-circle')
    })
  })

  // ── Confirm Action ────────────────────────────
  describe('confirm', () => {
    it('should emit confirm when confirm button is clicked', async () => {
      const wrapper = mountDialog()
      await wrapper.vm.$nextTick()

      // Find the confirm button (typically the second btn in the card actions)
      const btns = wrapper.findAllComponents({ name: 'VBtn' })
      const confirmBtn = btns.find(b => b.props('color') === 'error')
        || btns[btns.length - 1]
      await confirmBtn.trigger('click')
      await wrapper.vm.$nextTick()

      expect(wrapper.emitted('confirm')).toBeDefined()
    })
  })

  // ── Cancel / Close ────────────────────────────
  describe('cancel', () => {
    it('should emit update:modelValue false when cancel button is clicked', async () => {
      // Start with modelValue false, then set to true so watcher syncs isOpen
      const wrapper = mountDialog({ modelValue: false })
      await wrapper.setProps({ modelValue: true })
      await wrapper.vm.$nextTick()

      // Find cancel button (first VBtn, typically "No" / cancel)
      const btns = wrapper.findAllComponents({ name: 'VBtn' })
      const cancelBtn = btns.find(b => b.props('variant') === 'text')
        || btns[0]
      await cancelBtn.trigger('click')
      await wrapper.vm.$nextTick()

      const updates = wrapper.emitted('update:modelValue')
      expect(updates).toBeDefined()
      expect(updates[updates.length - 1]).toEqual([false])
    })
  })

  // ── Props ─────────────────────────────────────
  describe('props', () => {
    it('should pass maxWidth to VDialog', () => {
      const wrapper = mountDialog({ maxWidth: '600px' })
      const dialog = wrapper.findComponent(VDialogStub)
      expect(dialog.props('maxWidth')).toBe('600px')
    })
  })

  // ── Slot Content ──────────────────────────────
  describe('slot', () => {
    it('should render slot content', async () => {
      const wrapper = mountDialog(
        {},
        { slots: { default: '<strong>Custom delete warning</strong>' } }
      )
      await wrapper.vm.$nextTick()

      expect(wrapper.html()).toContain('Custom delete warning')
    })
  })
})
