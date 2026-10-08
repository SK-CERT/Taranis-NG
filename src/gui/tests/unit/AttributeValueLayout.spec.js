import { describe, it, expect } from 'vitest'
import { createI18n } from 'vue-i18n'
import { mountWithPlugins } from '../helpers/mount-helpers'
import AttributeValueLayout from '@/components/common/attribute/AttributeValueLayout.vue'

// The delete button is the only VBtn this layout renders (default col_right slot), so its
// presence maps directly to `delButtonVisible`.
const deleteBtn = (wrapper) => wrapper.findComponent({ name: 'VBtn' })

const makeValues = (n) => Array.from({ length: n }, (_, i) => ({ id: i, index: i, value: `v${i}` }))

const VMenuStub = {
    template: '<div class="menu-stub"><slot name="activator" :props="{}" /><slot /></div>'
}

// Render the tooltip content inline so provenance details are queryable without
// opening a VOverlay. The activator slot is still rendered for the icon assertions.
const VTooltipStub = {
    template: '<div class="tooltip-stub"><slot name="activator" :props="{}" /><slot /></div>'
}

const provenanceMessages = {
    attribute: {
        last_updated_at: 'Last updated at {date}',
        updated_by_user: 'Updated by {user}'
    }
}

const createProvenanceI18n = (locale = 'en') =>
    createI18n({
        legacy: false,
        locale,
        fallbackLocale: 'en',
        messages: { en: provenanceMessages, [locale]: provenanceMessages }
    })

function mountLayout(props = {}, locale = 'en') {
    return mountWithPlugins(AttributeValueLayout, {
        props: { valIndex: 0, values: makeValues(2), ...props },
        global: {
            plugins: [createProvenanceI18n(locale)],
            stubs: { VMenu: VMenuStub, VTooltip: VTooltipStub }
        }
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
    it('exposes modification provenance through the tooltip activator icon', () => {
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

        // The activator is a VIcon (rendered as <i>) bound to the tooltip's activator props;
        // it is not a button and carries no aria-label in this implementation.
        expect(activator.exists()).toBe(true)
        expect(activator.element.tagName).toBe('I')
        expect(activator.classes()).toContain('attribute-provenance__activator')

        const details = wrapper.find('.attribute-provenance__details')
        expect(details.exists()).toBe(true)
        expect(details.findAll('bdi[dir="auto"]').map((value) => value.text())).toEqual(['05.08.2026 - 03:45', 'Arthur Dent'])
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

        const details = wrapper.find('.attribute-provenance__details')
        expect(details.text()).toContain('new')
        expect(details.text()).toContain('Second analyst')
        expect(details.text()).not.toContain('First analyst')
    })

    it('uses the app locale for timestamp and accessible-list formatting without changing the raw value', () => {
        const rawTimestamp = '2026-08-09T17:30:00.000Z'
        const values = [{ id: 1, last_updated: rawTimestamp, user: { name: 'المحلل' } }]
        const wrapper = mountLayout({ values }, 'ar')
        const formattedTimestamp = new Intl.DateTimeFormat('ar', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(rawTimestamp))

        const details = wrapper.find('.attribute-provenance__details')
        expect(details.exists()).toBe(true)
        expect(wrapper.findAll('bdi[dir="auto"]').map((value) => value.text())).toEqual([formattedTimestamp, 'المحلل'])
        expect(values[0].last_updated).toBe(rawTimestamp)
    })

    // ── Embed-delete: expose visibility/handler via the col_middle slot ───────
    it('exposes delVisible via the col_middle scoped slot and omits the col_right button', () => {
        const wrapper = mountWithPlugins(AttributeValueLayout, {
            props: { valIndex: 0, values: makeValues(2), embedDelete: true },
            global: {
                plugins: [createProvenanceI18n()],
                stubs: { VMenu: VMenuStub }
            },
            slots: {
                col_middle: `<template #col_middle="{ delVisible }"><span class="dv">{{ delVisible }}</span></template>`
            }
        })
        expect(wrapper.find('.dv').text()).toBe('true')
        // With embedDelete, the layout does not render its own col_right delete button.
        expect(deleteBtn(wrapper).exists()).toBe(false)
    })
})
