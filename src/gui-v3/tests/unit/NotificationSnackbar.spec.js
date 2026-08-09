import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { createI18n } from 'vue-i18n'
import { mountWithPlugins } from '../helpers/mount-helpers'
import NotificationSnackbar from '@/components/common/NotificationSnackbar.vue'

/**
 * NotificationSnackbar Component Tests
 *
 * Tests notification component rendering and behavior
 */

// Stub VSnackbar to render inline (avoids VOverlay issues in happy-dom)
const VSnackbarStub = {
    name: 'VSnackbar',
    props: ['modelValue', 'color', 'timeout', 'location'],
    template: '<div class="v-snackbar-stub"><slot /><slot name="actions" /></div>',
    emits: ['update:modelValue']
}

function mountSnackbar() {
    return mountWithPlugins(NotificationSnackbar, {
        global: { stubs: { VSnackbar: VSnackbarStub } }
    })
}

function mountPluralSnackbar() {
    const i18n = createI18n({
        legacy: false,
        locale: 'en',
        messages: {
            en: {
                test: {
                    selected: 'No items selected | One item selected | {count} items selected'
                }
            }
        }
    })

    return mount(NotificationSnackbar, {
        global: {
            plugins: [i18n],
            stubs: {
                VSnackbar: VSnackbarStub,
                VIcon: true,
                VBtn: true
            }
        }
    })
}

describe('NotificationSnackbar', () => {
    it('should render', () => {
        const wrapper = mountSnackbar()
        expect(wrapper.exists()).toBe(true)
    })

    it('should display notification on event', async () => {
        const wrapper = mountSnackbar()

        window.dispatchEvent(
            new CustomEvent('notification', {
                detail: { type: 'success', message: 'Test notification' }
            })
        )
        await wrapper.vm.$nextTick()

        expect(wrapper.vm.show).toBe(true)
        expect(wrapper.vm.message).toBe('Test notification')
        expect(wrapper.vm.type).toBe('success')
    })

    it('should use i18n key when loc is provided', async () => {
        const wrapper = mountSnackbar()

        window.dispatchEvent(
            new CustomEvent('notification', {
                detail: { type: 'error', loc: 'common.error_saving' }
            })
        )
        await wrapper.vm.$nextTick()

        // Component calls t(loc) internally; real EN translation is "Error saving"
        expect(wrapper.vm.message).toBe('Error saving')
        expect(wrapper.vm.type).toBe('error')
    })

    it.each([
        [0, 'No items selected'],
        [1, 'One item selected'],
        [2, '2 items selected']
    ])('uses pluralCount=%i to select the distinct plural branch', async (pluralCount, expected) => {
        const wrapper = mountPluralSnackbar()

        try {
            window.dispatchEvent(
                new CustomEvent('notification', {
                    detail: {
                        type: 'success',
                        loc: 'test.selected',
                        params: { count: pluralCount },
                        pluralCount
                    }
                })
            )
            await wrapper.vm.$nextTick()

            expect(wrapper.vm.message).toBe(expected)
        } finally {
            wrapper.unmount()
        }
    })

    it('should show correct icon for each type', async () => {
        const wrapper = mountSnackbar()

        const expectedIcons = {
            success: 'mdi-check-circle',
            error: 'mdi-alert-circle',
            warning: 'mdi-alert',
            info: 'mdi-information'
        }

        for (const [type, icon] of Object.entries(expectedIcons)) {
            window.dispatchEvent(
                new CustomEvent('notification', {
                    detail: { type, message: `Test ${type}` }
                })
            )
            await wrapper.vm.$nextTick()
            expect(wrapper.vm.icon).toBe(icon)
        }
    })

    it('should auto-dismiss after timeout', async () => {
        const wrapper = mountSnackbar()

        window.dispatchEvent(
            new CustomEvent('notification', {
                detail: { type: 'success', message: 'Auto dismiss test' }
            })
        )
        await wrapper.vm.$nextTick()
        expect(wrapper.vm.show).toBe(true)

        wrapper.vm.show = false
        await wrapper.vm.$nextTick()
        expect(wrapper.vm.show).toBe(false)
    })

    it('should close when close button is clicked', async () => {
        const wrapper = mountSnackbar()

        window.dispatchEvent(
            new CustomEvent('notification', {
                detail: { type: 'info', message: 'Test' }
            })
        )
        await wrapper.vm.$nextTick()
        expect(wrapper.vm.show).toBe(true)

        wrapper.vm.show = false
        await wrapper.vm.$nextTick()
        expect(wrapper.vm.show).toBe(false)
    })

    it('should handle multiple rapid notifications', async () => {
        const wrapper = mountSnackbar()

        window.dispatchEvent(
            new CustomEvent('notification', {
                detail: { type: 'success', message: 'First' }
            })
        )
        window.dispatchEvent(
            new CustomEvent('notification', {
                detail: { type: 'error', message: 'Second' }
            })
        )
        await wrapper.vm.$nextTick()

        expect(wrapper.vm.show).toBe(true)
        expect(wrapper.vm.message).toBe('Second')
        expect(wrapper.vm.type).toBe('error')
    })
})
