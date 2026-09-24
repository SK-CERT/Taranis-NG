import { describe, it, expect } from 'vitest'
import { mountWithPlugins } from '../helpers/mount-helpers'
import SuggestField from '@/components/common/SuggestField.vue'

describe('SuggestField', () => {
    it('uses the suggested value as the placeholder', () => {
        const wrapper = mountWithPlugins(SuggestField, {
            props: { modelValue: '', suggested: 'https://host/metadata' }
        })

        const field = wrapper.findComponent({ name: 'VTextField' })
        expect(field.props('placeholder')).toBe('https://host/metadata')
    })

    it('renders the wand icon only when a suggestion is present', () => {
        const withSuggestion = mountWithPlugins(SuggestField, {
            props: { modelValue: '', suggested: 'https://host/metadata' }
        })
        expect(withSuggestion.find('.mdi-auto-fix').exists()).toBe(true)

        const withoutSuggestion = mountWithPlugins(SuggestField, {
            props: { modelValue: '' }
        })
        expect(withoutSuggestion.find('.mdi-auto-fix').exists()).toBe(false)
    })

    it('applies the suggestion to the model on wand click and emits "suggest"', async () => {
        const wrapper = mountWithPlugins(SuggestField, {
            props: { modelValue: '', suggested: 'https://host/metadata' }
        })

        await wrapper.find('.mdi-auto-fix').trigger('click')

        // v-model update:modelValue event
        const updateEvents = wrapper.emitted('update:modelValue')
        expect(updateEvents).toBeTruthy()
        expect(updateEvents[0][0]).toBe('https://host/metadata')
        // explicit suggest event
        const suggestEvents = wrapper.emitted('suggest')
        expect(suggestEvents).toBeTruthy()
        expect(suggestEvents[0][0]).toBe('https://host/metadata')
    })

    it('uses an explicit tooltip-label over the default common.use_suggested key', () => {
        const wrapper = mountWithPlugins(SuggestField, {
            props: { modelValue: '', suggested: 'x', tooltipLabel: 'Use this URL' }
        })

        // the tooltip text is rendered in the v-tooltip's activator content
        expect(wrapper.html()).toContain('Use this URL')
    })

    it('falls back to the common.use_suggested translation when no tooltip-label is set', () => {
        const wrapper = mountWithPlugins(SuggestField, {
            props: { modelValue: '', suggested: 'x' }
        })

        // en.json: common.use_suggested = "Use suggested value"
        expect(wrapper.html()).toContain('Use suggested value')
    })

    it('does not apply when there is no suggestion (no-op click target is absent)', () => {
        const wrapper = mountWithPlugins(SuggestField, {
            props: { modelValue: '' }
        })

        expect(wrapper.find('.mdi-auto-fix').exists()).toBe(false)
        expect(wrapper.emitted('update:modelValue')).toBeFalsy()
    })
})
