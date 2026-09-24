/* eslint-disable vue/one-component-per-file -- test harness uses minimal inline components */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import ThemeEditor from '@/components/config/ThemeEditor.vue'
import { EDITABLE_TOKENS } from '@/themes/custom'

const { settingsStore, themeThemes } = vi.hoisted(() => ({
    settingsStore: {
        getSettings: [],
        getSetting: vi.fn(),
        saveSettings: vi.fn().mockResolvedValue(undefined)
    },
    themeThemes: { value: {} }
}))

vi.mock('@/stores/settings', () => ({ useSettingsStore: () => settingsStore }))

vi.mock('vue-i18n', () => ({
    useI18n: () => ({ t: (key) => key, te: () => false })
}))

vi.mock('vuetify', () => ({
    useTheme: () => ({ change: vi.fn(), themes: themeThemes, global: { name: { value: 'custom-light' } } })
}))

/** The editor coalesces previews into one animation frame, so wait for one. */
const nextFrame = () => new Promise((resolve) => requestAnimationFrame(resolve))

const passthrough = (name) => defineComponent({ name, template: '<div><slot /><slot name="activator" :props="{}" /></div>' })

const ColorPickerStub = defineComponent({
    name: 'VColorPicker',
    props: { modelValue: { type: String, default: '' }, mode: { type: String, default: '' } },
    emits: ['update:modelValue'],
    template: '<div class="picker-stub" />'
})

function mountEditor() {
    const pinia = createPinia()
    setActivePinia(pinia)
    return mount(ThemeEditor, {
        global: {
            plugins: [pinia],
            stubs: {
                VMenu: passthrough('VMenu'),
                VColorPicker: ColorPickerStub,
                VBtnToggle: passthrough('VBtnToggle'),
                VBtn: passthrough('VBtn'),
                VAlert: true,
                VIcon: true
            }
        }
    })
}

describe('ThemeEditor', () => {
    beforeEach(() => {
        settingsStore.saveSettings.mockClear()
        settingsStore.getSetting.mockReturnValue('')
        settingsStore.getSettings = [{ id: 7, key: 'CUSTOM_THEME', value: '', type: 'S', is_global: false }]
        themeThemes.value = {}
    })

    it('renders one colour slot per editable token', async () => {
        const wrapper = mountEditor()
        await flushPromises()

        expect(wrapper.findAll('.token__swatch')).toHaveLength(EDITABLE_TOKENS.length)
        expect(wrapper.findAllComponents(ColorPickerStub)).toHaveLength(EDITABLE_TOKENS.length)
    })

    // The editor writes straight into Vuetify's live theme map, which is what
    // makes the preview immediate.
    it('installs the palette into the live themes on load and on every edit', async () => {
        const wrapper = mountEditor()
        await flushPromises()

        expect(Object.keys(themeThemes.value).sort()).toEqual(['custom-dark', 'custom-light'])

        wrapper.vm.setToken('primary', '#abcdef')
        await nextFrame()

        expect(wrapper.vm.values['primary']).toBe('#ABCDEF')
        expect(themeThemes.value['custom-light'].colors.primary).toBe('#ABCDEF')
    })

    it('ignores a picker value that is not a usable colour', async () => {
        const wrapper = mountEditor()
        await flushPromises()
        const before = wrapper.vm.values['primary']

        wrapper.vm.setToken('primary', '')
        wrapper.vm.setToken('primary', undefined)
        await flushPromises()

        expect(wrapper.vm.values['primary']).toBe(before)
    })

    it('saves valid JSON onto the CUSTOM_THEME record', async () => {
        const wrapper = mountEditor()
        await flushPromises()

        wrapper.vm.setToken('primary', '#123456')
        await wrapper.vm.save()

        expect(settingsStore.saveSettings).toHaveBeenCalledTimes(1)
        const payload = settingsStore.saveSettings.mock.calls[0][0]
        expect(payload.is_global).toBe(false)
        expect(payload.data.id).toBe(7)

        const stored = JSON.parse(payload.data.value)
        expect(stored.light.primary).toBe('#123456')
        expect(stored.basedOn).toBeTruthy()
        expect(Object.keys(stored)).toEqual(['basedOn', 'light', 'dark'])
    })

    it('reads a stored palette back on load', async () => {
        settingsStore.getSetting.mockReturnValue(JSON.stringify({ basedOn: 'forest', light: { primary: '#0F0F0F' }, dark: {} }))

        const wrapper = mountEditor()
        await flushPromises()

        expect(wrapper.vm.values['primary']).toBe('#0F0F0F')
    })

    it('reverts an unsaved edit when the tab goes away', async () => {
        const wrapper = mountEditor()
        await flushPromises()
        const original = wrapper.vm.values['primary']

        wrapper.vm.setToken('primary', '#FF00FF')
        await nextFrame()
        expect(themeThemes.value['custom-light'].colors.primary).toBe('#FF00FF')

        wrapper.unmount()
        expect(themeThemes.value['custom-light'].colors.primary).toBe(original)
    })

    it('resets a single colour without touching the others', async () => {
        const wrapper = mountEditor()
        await flushPromises()
        const originalPrimary = wrapper.vm.values['primary']

        wrapper.vm.setToken('primary', '#FF00FF')
        wrapper.vm.setToken('accent', '#00FFFF')
        await nextFrame()
        expect(wrapper.vm.isModified('primary')).toBe(true)

        wrapper.vm.resetToken('primary')
        await nextFrame()

        expect(wrapper.vm.values['primary']).toBe(originalPrimary)
        expect(wrapper.vm.isModified('primary')).toBe(false)
        // the other edit survives
        expect(wrapper.vm.values['accent']).toBe('#00FFFF')
        expect(wrapper.vm.isModified('accent')).toBe(true)
    })

    it('tracks whether anything differs from the seed', async () => {
        const wrapper = mountEditor()
        await flushPromises()

        expect(wrapper.vm.isDirty).toBe(false)
        wrapper.vm.setToken('primary', '#FF00FF')
        await nextFrame()
        expect(wrapper.vm.isDirty).toBe(true)
        wrapper.vm.resetToken('primary')
        await nextFrame()
        expect(wrapper.vm.isDirty).toBe(false)
    })

    it('resets back to the seed', async () => {
        const wrapper = mountEditor()
        await flushPromises()
        const original = wrapper.vm.values['primary']

        wrapper.vm.setToken('primary', '#FF00FF')
        wrapper.vm.reset()
        await flushPromises()

        expect(wrapper.vm.values['primary']).toBe(original)
    })
})
