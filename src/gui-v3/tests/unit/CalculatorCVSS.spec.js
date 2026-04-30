import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mountWithPlugins } from '../helpers/mount-helpers'
import CalculatorCVSS from '@/components/common/CalculatorCVSS.vue'

// Stub VDialog to render inline (avoids teleport/overlay issues)
const VDialogStub = {
  name: 'VDialog',
  props: ['modelValue', 'fullscreen', 'transition'],
  template: '<div class="v-dialog-stub"><slot /></div>',
  emits: ['update:modelValue']
}

function mountCalculator(props = {}, options = {}) {
  return mountWithPlugins(CalculatorCVSS, {
    props: { modelValue: '', ...props },
    global: {
      stubs: { VDialog: VDialogStub },
      ...(options.global || {})
    },
    ...options
  })
}

describe('CalculatorCVSS', () => {
  // ── Button Rendering ──────────────────────────
  describe('button rendering', () => {
    it('should render a calculator button', () => {
      const wrapper = mountCalculator()
      const btn = wrapper.findComponent({ name: 'VBtn' })
      expect(btn.exists()).toBe(true)
      expect(wrapper.html()).toContain('mdi-calculator')
    })

    it('should disable button when disabled prop is true', () => {
      const wrapper = mountCalculator({ disabled: true })
      const btn = wrapper.findComponent({ name: 'VBtn' })
      expect(btn.props('disabled')).toBe(true)
    })
  })

  // ── Dialog Open ───────────────────────────────
  describe('dialog open', () => {
    it('should open dialog on button click', async () => {
      const wrapper = mountCalculator()
      // Initially visible is false
      expect(wrapper.vm.visible).toBe(false)

      await wrapper.findComponent({ name: 'VBtn' }).trigger('click')
      expect(wrapper.vm.visible).toBe(true)
    })

    it('should detect version from existing vector on open', async () => {
      const wrapper = mountCalculator({
        modelValue: 'CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H'
      })

      await wrapper.findComponent({ name: 'VBtn' }).trigger('click')
      expect(wrapper.vm.selectedVersion).toBe('3.1')
    })

    it('should default to version 3.1 when no vector', async () => {
      const wrapper = mountCalculator()
      await wrapper.findComponent({ name: 'VBtn' }).trigger('click')
      expect(wrapper.vm.selectedVersion).toBe('3.1')
    })

    it('should detect CVSS 2.0 vector', async () => {
      const wrapper = mountCalculator({
        modelValue: 'AV:N/AC:L/Au:N/C:C/I:C/A:C'
      })

      await wrapper.findComponent({ name: 'VBtn' }).trigger('click')
      expect(wrapper.vm.selectedVersion).toBe('2.0')
    })

    it('should detect CVSS 4.0 vector', async () => {
      const wrapper = mountCalculator({
        modelValue: 'CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:H/SC:N/SI:N/SA:N'
      })

      await wrapper.findComponent({ name: 'VBtn' }).trigger('click')
      expect(wrapper.vm.selectedVersion).toBe('4.0')
    })
  })

  // ── Version Switching ─────────────────────────
  describe('version switching', () => {
    it('should create a new instance when version changes', async () => {
      const wrapper = mountCalculator()
      await wrapper.findComponent({ name: 'VBtn' }).trigger('click')

      // Default is 3.1 — switch to 4.0
      wrapper.vm.selectedVersion = '4.0'
      await wrapper.vm.$nextTick()
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.cvssInstance).toBeDefined()
      expect(wrapper.vm.vectorInput).toContain('CVSS:4.0')
    })

    it('should preserve version options', async () => {
      const wrapper = mountCalculator()
      await wrapper.findComponent({ name: 'VBtn' }).trigger('click')

      expect(wrapper.vm.versionOptions).toEqual(['2.0', '3.0', '3.1', '4.0'])
    })
  })

  // ── Vector Input ──────────────────────────────
  describe('vector input', () => {
    it('should parse a pasted CVSS 3.1 vector', async () => {
      const wrapper = mountCalculator()
      await wrapper.findComponent({ name: 'VBtn' }).trigger('click')

      const vector = 'CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H'
      wrapper.vm.onVectorInput(vector)
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.selectedVersion).toBe('3.1')
      expect(wrapper.vm.vectorInput).toContain('CVSS:3.1')
    })

    it('should auto-switch version when a different vector is pasted', async () => {
      const wrapper = mountCalculator()
      await wrapper.findComponent({ name: 'VBtn' }).trigger('click')

      // Start with 3.1 (default), paste a 4.0 vector
      const v4vector = 'CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:H/SC:N/SI:N/SA:N'
      wrapper.vm.onVectorInput(v4vector)
      await wrapper.vm.$nextTick()
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.selectedVersion).toBe('4.0')
    })
  })

  // ── Metric Selection ──────────────────────────
  describe('metric selection', () => {
    it('should have metric groups after opening', async () => {
      const wrapper = mountCalculator()
      await wrapper.findComponent({ name: 'VBtn' }).trigger('click')

      expect(wrapper.vm.metricGroups).toBeDefined()
      expect(wrapper.vm.metricGroups.length).toBeGreaterThan(0)
    })

    it('should update vector when a metric is toggled', async () => {
      const wrapper = mountCalculator()
      await wrapper.findComponent({ name: 'VBtn' }).trigger('click')

      const groups = wrapper.vm.metricGroups
      const firstGroup = groups[0]
      const firstMetric = firstGroup.metrics[0]

      // Select the second value (index 1) if available, otherwise index 0
      const idx = firstMetric.values.length > 1 ? 1 : 0
      wrapper.vm.onMetricToggle(firstMetric, idx)
      await wrapper.vm.$nextTick()

      // Vector should now contain the selected metric
      expect(wrapper.vm.vectorInput.length).toBeGreaterThan(0)
    })
  })

  // ── Score Display ─────────────────────────────
  describe('score display', () => {
    it('should compute scores from a complete vector', async () => {
      const wrapper = mountCalculator({
        modelValue: 'CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H'
      })

      await wrapper.findComponent({ name: 'VBtn' }).trigger('click')
      await wrapper.vm.$nextTick()

      const scores = wrapper.vm.scores
      expect(scores).toBeDefined()
    })

    it('should build scoreDisplay items with severity labels', async () => {
      const wrapper = mountCalculator({
        modelValue: 'CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H'
      })

      await wrapper.findComponent({ name: 'VBtn' }).trigger('click')
      await wrapper.vm.$nextTick()

      const display = wrapper.vm.scoreDisplay
      expect(display).toBeDefined()
      expect(display.length).toBeGreaterThan(0)
      expect(display[0]).toHaveProperty('score')
      expect(display[0]).toHaveProperty('severityLabel')
    })
  })

  // ── Cancel / Emit ─────────────────────────────
  describe('cancel and emit', () => {
    it('should emit update:modelValue with vector string on cancel', async () => {
      const wrapper = mountCalculator({
        modelValue: 'CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H'
      })

      await wrapper.findComponent({ name: 'VBtn' }).trigger('click')
      await wrapper.vm.$nextTick()

      wrapper.vm.cancel()
      await wrapper.vm.$nextTick()

      const emitted = wrapper.emitted('update:modelValue')
      expect(emitted).toBeDefined()
      expect(emitted[emitted.length - 1][0]).toContain('CVSS:3.1')
    })

    it('should close dialog on cancel', async () => {
      const wrapper = mountCalculator()
      await wrapper.findComponent({ name: 'VBtn' }).trigger('click')
      expect(wrapper.vm.visible).toBe(true)

      wrapper.vm.cancel()
      await wrapper.vm.$nextTick()
      expect(wrapper.vm.visible).toBe(false)
    })
  })

  // ── Tooltips ──────────────────────────────────
  describe('tooltips', () => {
    it('should have showTooltips toggle', async () => {
      const wrapper = mountCalculator()
      await wrapper.findComponent({ name: 'VBtn' }).trigger('click')

      expect(wrapper.vm.showTooltips).toBeDefined()
      expect(typeof wrapper.vm.showTooltips).toBe('boolean')
    })
  })

  // ── Score Values ──────────────────────────────
  describe('score values', () => {
    describe('base score', () => {
      it.each([
        ['CVSS:4.0/AV:L/AC:L/AT:P/PR:L/UI:N/VC:H/VI:H/VA:H/SC:N/SI:N/SA:N', '7.3'],
        ['CVSS:3.1/AV:L/AC:H/PR:L/UI:N/S:U/C:H/I:H/A:H', '7.0'],
        ['CVSS:4.0/AV:N/AC:L/AT:P/PR:N/UI:P/VC:H/VI:H/VA:H/SC:N/SI:N/SA:N', '7.7'],
        ['CVSS:3.1/AV:N/AC:H/PR:N/UI:N/S:U/C:H/I:H/A:H', '8.1'],
        ['CVSS:4.0/AV:N/AC:L/AT:P/PR:N/UI:N/VC:H/VI:L/VA:L/SC:N/SI:N/SA:N', '8.3'],
        ['CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N', '7.5']
      ])('vector %s → base %s', async (vector, expectedBase) => {
        const wrapper = mountCalculator({ modelValue: vector })
        await wrapper.findComponent({ name: 'VBtn' }).trigger('click')
        await wrapper.vm.$nextTick()

        const display = wrapper.vm.scoreDisplay
        expect(display).toBeDefined()
        expect(display[0].score).toBe(expectedBase)
      })
    })

    describe('threat score (CVSS 4.0 with E metric)', () => {
      it.each([
        ['CVSS:4.0/AV:N/AC:L/AT:P/PR:N/UI:P/VC:H/VI:H/VA:H/SC:N/SI:N/SA:N/E:U', '5.2'],
        ['CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:N/VA:N/SC:N/SI:N/SA:N/E:A', '8.7']
      ])('vector %s → threat %s', async (vector, expectedThreat) => {
        const wrapper = mountCalculator({ modelValue: vector })
        await wrapper.findComponent({ name: 'VBtn' }).trigger('click')
        await wrapper.vm.$nextTick()

        const display = wrapper.vm.scoreDisplay
        expect(display).toBeDefined()
        expect(display[1].name).toBe('threat')
        expect(display[1].score).toBe(expectedThreat)
      })
    })

    describe('temporal score (CVSS 3.1 with temporal metrics)', () => {
      it('CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N/E:F/RL:O/RC:C → temporal 7.0', async () => {
        const vector = 'CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N/E:F/RL:O/RC:C'
        const wrapper = mountCalculator({ modelValue: vector })
        await wrapper.findComponent({ name: 'VBtn' }).trigger('click')
        await wrapper.vm.$nextTick()

        const display = wrapper.vm.scoreDisplay
        expect(display).toBeDefined()
        expect(display[1].name).toBe('temporal')
        expect(display[1].score).toBe('7.0')
      })
    })

    describe('environmental score (CVSS 4.0 with environmental metrics)', () => {
      it('CVSS:4.0 with CR/IR/AR/MAV/MAC/MVC/MVI/MVA → environmental 8.1', async () => {
        const vector =
          'CVSS:4.0/AV:N/AC:L/AT:P/PR:N/UI:N/VC:H/VI:L/VA:L/SC:N/SI:N/SA:N/CR:H/IR:L/AR:L/MAV:N/MAC:H/MVC:H/MVI:L/MVA:L'
        const wrapper = mountCalculator({ modelValue: vector })
        await wrapper.findComponent({ name: 'VBtn' }).trigger('click')
        await wrapper.vm.$nextTick()

        const display = wrapper.vm.scoreDisplay
        expect(display).toBeDefined()
        expect(display[2].name).toBe('environmental')
        expect(display[2].score).toBe('8.1')
      })
    })
  })
})
