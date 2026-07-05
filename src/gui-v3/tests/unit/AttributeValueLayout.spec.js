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

    it('hides the delete button for a single value (the last cannot be deleted)', () => {
        const wrapper = mountLayout({ values: makeValues(1) })
        expect(deleteBtn(wrapper).exists()).toBe(false)
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
