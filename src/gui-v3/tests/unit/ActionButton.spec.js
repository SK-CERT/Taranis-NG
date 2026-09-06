import { describe, it, expect, vi } from 'vitest'
import { nextTick } from 'vue'
import { mount } from '@vue/test-utils'
import { createI18n } from 'vue-i18n'
import { mountWithPlugins } from '../helpers/mount-helpers'
import ActionButton from '@/components/common/buttons/ActionButton.vue'
import en from '@/i18n/en.json'
import cs from '@/i18n/cs.json'

describe('ActionButton', () => {
    // ── Loading ───────────────────────────────────
    describe('loading', () => {
        it('does not emit while the action is in flight', async () => {
            const wrapper = mountWithPlugins(ActionButton, { props: { action: 'collect', loading: true } })

            await wrapper.findComponent({ name: 'VBtn' }).trigger('click')

            expect(wrapper.emitted('click')).toBeUndefined()
        })

        it('emits normally when it is not loading', async () => {
            const wrapper = mountWithPlugins(ActionButton, { props: { action: 'collect' } })

            await wrapper.findComponent({ name: 'VBtn' }).trigger('click')

            expect(wrapper.emitted('click')).toHaveLength(1)
        })
    })

    // ── Predefined Actions ────────────────────────
    describe('predefined actions', () => {
        it.each([
            ['delete', 'mdi-delete-outline'],
            ['edit', 'mdi-pencil'],
            ['publish', 'mdi-file-outline'],
            ['remove', 'mdi-minus-thick'],
            ['open', 'mdi-open-in-new'],
            ['open_source', 'mdi-open-in-new'],
            ['lock', 'mdi-lock-outline'],
            ['collect', 'mdi-play-circle-outline']
        ])('action="%s" should render icon %s', (action, expectedIcon) => {
            const wrapper = mountWithPlugins(ActionButton, {
                props: { action }
            })

            // Vuetify 4 renders icon name in the HTML (class or text depending on version)
            expect(wrapper.html()).toContain(expectedIcon)
        })

        it.each([
            ['delete', 'Delete'],
            ['edit', 'Edit'],
            ['publish', 'Publish'],
            ['remove', 'Remove'],
            ['open', 'Open'],
            ['open_source', 'Open source'],
            ['lock', 'Lock'],
            ['collect', 'Collect now']
        ])('action="%s" translates its default title', (action, expectedTitle) => {
            const wrapper = mountWithPlugins(ActionButton, { props: { action } })

            expect(wrapper.findComponent({ name: 'VBtn' }).attributes('title')).toBe(expectedTitle)
        })

        it('reacts to locale changes while an explicit title continues to win', async () => {
            const i18n = createI18n({
                legacy: false,
                locale: 'en',
                fallbackLocale: 'en',
                messages: { en, cs }
            })
            const wrapper = mount(ActionButton, {
                props: { action: 'delete' },
                global: {
                    plugins: [i18n],
                    stubs: {
                        VBtn: {
                            props: ['title'],
                            template: '<button :title="title"><slot /></button>'
                        },
                        VIcon: true
                    }
                }
            })

            expect(wrapper.get('button').attributes('title')).toBe('Delete')

            i18n.global.locale.value = 'cs'
            await nextTick()
            expect(wrapper.get('button').attributes('title')).toBe('Smazat')

            await wrapper.setProps({ title: 'Remove this row' })
            i18n.global.locale.value = 'en'
            await nextTick()
            expect(wrapper.get('button').attributes('title')).toBe('Remove this row')
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

    describe('reacting to prop changes after mount', () => {
        /**
         * These were read once during setup, so a button whose look or availability is driven by
         * state kept whatever it was given on the frame it mounted: a toolbar toggle stayed the
         * inactive colour after selection mode turned on, a select-all never swapped its icon,
         * and a row action that mounted unavailable never became available.
         */
        it('becomes available when disabled turns false', async () => {
            const wrapper = mountWithPlugins(ActionButton, { props: { action: 'delete', disabled: true } })
            expect(wrapper.findComponent({ name: 'VBtn' }).props('disabled')).toBe(true)

            await wrapper.setProps({ disabled: false })

            expect(wrapper.findComponent({ name: 'VBtn' }).props('disabled')).toBe(false)

            await wrapper.findComponent({ name: 'VBtn' }).trigger('click')
            expect(wrapper.emitted('click')).toHaveLength(1)
        })

        it('swaps its icon and colour when they change', async () => {
            const wrapper = mountWithPlugins(ActionButton, {
                props: { icon: 'mdi-select-all', color: 'medium-emphasis' }
            })

            await wrapper.setProps({ icon: 'mdi-checkbox-blank-outline', color: 'primary' })

            // Vuetify 4 renders icon name in the HTML (class or text depending on version)
            expect(wrapper.html()).toContain('mdi-checkbox-blank-outline')
            expect(wrapper.findComponent({ name: 'VIcon' }).props('color')).toBe('primary')
        })
    })
})
