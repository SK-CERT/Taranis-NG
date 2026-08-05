import { describe, it, expect } from 'vitest'
import { mountWithPlugins } from '../helpers/mount-helpers'
import AttributeValueLayout from '@/components/common/attribute/AttributeValueLayout.vue'

// The delete button is the only VBtn this layout renders (default col_right slot), so its
// presence maps directly to `delButtonVisible`.
const deleteBtn = (wrapper) => wrapper.findComponent({ name: 'VBtn' })

const makeValues = (n) => Array.from({ length: n }, (_, i) => ({ id: i, index: i, value: `v${i}` }))

function mountLayout(props = {}) {
    return mountWithPlugins(AttributeValueLayout, {
        props: { valIndex: 0, values: makeValues(2), ...props }
    })
}

describe('AttributeValueLayout', () => {
    // ── Delete button visibility (persistent, not hover-gated) ────────────────
    it('shows the delete button without hover when there is more than the minimum', () => {
        const wrapper = mountLayout({ values: makeValues(2) })
        expect(deleteBtn(wrapper).exists()).toBe(true)
    })

    it('hides the delete button for the last value when one is required', () => {
        expect(deleteBtn(mountLayout({ values: makeValues(1), occurrence: 1 })).exists()).toBe(false)
    })

    it('allows deleting the last value when min_occurrence is 0', () => {
        // min_occurrence 0 -> the attribute may end up with no values at all.
        expect(deleteBtn(mountLayout({ values: makeValues(1), occurrence: 0 })).exists()).toBe(true)
    })

    it('respects a higher min_occurrence', () => {
        // occurrence = 2 -> at least two values must remain.
        expect(deleteBtn(mountLayout({ values: makeValues(2), occurrence: 2 })).exists()).toBe(false)
        expect(deleteBtn(mountLayout({ values: makeValues(3), occurrence: 2 })).exists()).toBe(true)
    })

    // ── Delete action ─────────────────────────────────────────────────────────
    it('emits del-value when the delete button is clicked', async () => {
        const wrapper = mountLayout({ values: makeValues(2) })
        await deleteBtn(wrapper).trigger('click')
        expect(wrapper.emitted('del-value')).toBeTruthy()
    })

    // ── Modification provenance ──────────────────────────────────────────────
    it('exposes modification provenance through a keyboard-focusable control', () => {
        const wrapper = mountLayout({
            values: [
                {
                    id: 1,
                    value: 'v1',
                    last_updated: '05.08.2026 - 03:45',
                    user: { name: 'Arthur Dent' }
                }
            ]
        })
        const activator = wrapper.find('.attribute-provenance__activator')

        expect(activator.exists()).toBe(true)
        expect(activator.element.tagName).toBe('BUTTON')
        expect(activator.attributes('aria-label')).toBe('Last updated: 05.08.2026 - 03:45; Updated by: Arthur Dent')
        expect(activator.attributes('tabindex')).not.toBe('-1')
    })

    it('renders no provenance control when both timestamp and modifier are absent', () => {
        const wrapper = mountLayout({
            values: [{ id: 1, value: 'v1', last_updated: null, user: null }]
        })

        expect(wrapper.find('.attribute-provenance__activator').exists()).toBe(false)
        expect(wrapper.find('.attribute-provenance__details').exists()).toBe(false)
    })

    it('uses the selected value provenance rather than another occurrence', () => {
        const wrapper = mountLayout({
            valIndex: 1,
            values: [
                { id: 1, last_updated: 'old', user: { name: 'First analyst' } },
                { id: 2, last_updated: 'new', user: { name: 'Second analyst' } }
            ]
        })

        expect(wrapper.find('.attribute-provenance__activator').attributes('aria-label')).toBe(
            'Last updated: new; Updated by: Second analyst'
        )
    })

    // ── Embed-delete: expose visibility/handler via the col_middle slot ───────
    it('exposes delVisible via the col_middle scoped slot and omits the col_right button', () => {
        const wrapper = mountWithPlugins(AttributeValueLayout, {
            props: { valIndex: 0, values: makeValues(2), embedDelete: true },
            slots: {
                col_middle: `<template #col_middle="{ delVisible }"><span class="dv">{{ delVisible }}</span></template>`
            }
        })
        expect(wrapper.find('.dv').text()).toBe('true')
        // With embedDelete, the layout does not render its own col_right delete button.
        expect(deleteBtn(wrapper).exists()).toBe(false)
    })
})
