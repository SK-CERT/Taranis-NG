/* eslint-disable vue/one-component-per-file */
import { computed, defineComponent, h } from 'vue'
import { createPinia, setActivePinia } from 'pinia'
import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useSettingsStore } from '@/stores/settings'
import { useSpellcheck } from '@/composables/useSpellcheck'
import AssetDialog from '@/components/assets/AssetDialog.vue'
import CpeEditor from '@/components/assets/CpeEditor.vue'
import { mountWithPlugins } from '../helpers/mount-helpers'

vi.mock('@/composables/useAuth', () => ({
    useAuth: () => ({ checkPermission: () => true })
}))

const VTextField = defineComponent({
    name: 'VTextField',
    inheritAttrs: false,
    props: {
        modelValue: { type: String, default: '' },
        label: { type: String, default: '' },
        spellcheck: Boolean
    },
    setup(props) {
        return () => h('input', { 'data-label': props.label, 'spellcheck': String(props.spellcheck) })
    }
})

const VTextarea = defineComponent({
    name: 'VTextarea',
    inheritAttrs: false,
    props: {
        modelValue: { type: String, default: '' },
        label: { type: String, default: '' },
        spellcheck: Boolean
    },
    setup(props) {
        return () => h('textarea', { 'data-label': props.label, 'spellcheck': String(props.spellcheck) })
    }
})

const passThrough = { template: '<div><slot /></div>' }

function mountAssetDialog() {
    return mountWithPlugins(AssetDialog, {
        props: { modelValue: true, groupId: 'group-1' },
        global: {
            stubs: {
                VDialog: passThrough,
                VCard: passThrough,
                VCardText: passThrough,
                VWindow: passThrough,
                VWindowItem: passThrough,
                VForm: passThrough,
                VTextField,
                VTextarea,
                VTabs: true,
                DialogToolbar: true,
                CpeEditor: true
            }
        }
    })
}

describe('spellcheck preference', () => {
    beforeEach(() => setActivePinia(createPinia()))

    it('is reactive and enabled by default', async () => {
        const Consumer = defineComponent({
            setup() {
                const spellcheck = useSpellcheck()
                return { enabled: computed(() => String(spellcheck.value)) }
            },
            template: '<span>{{ enabled }}</span>'
        })
        const wrapper = mount(Consumer)
        const settingsStore = useSettingsStore()

        expect(wrapper.text()).toBe('true')
        settingsStore.spellcheck = false
        await wrapper.vm.$nextTick()
        expect(wrapper.text()).toBe('false')
    })

    it('applies the preference to prose while excluding asset identifiers', async () => {
        const wrapper = mountAssetDialog()
        const settingsStore = useSettingsStore()
        settingsStore.spellcheck = false
        await wrapper.vm.$nextTick()

        const inputs = wrapper.findAll('input')
        const [name, serial] = inputs
        const description = wrapper.find('textarea')

        expect(name?.attributes('spellcheck')).toBe('false')
        expect(description.attributes('spellcheck')).toBe('false')
        expect(serial?.attributes('spellcheck')).toBe('false')

        settingsStore.spellcheck = true
        await wrapper.vm.$nextTick()
        expect(name?.attributes('spellcheck')).toBe('true')
        expect(description.attributes('spellcheck')).toBe('true')
        expect(serial?.attributes('spellcheck')).toBe('false')
    })

    it('keeps CPE codes excluded while applying the preference to their descriptions', () => {
        const wrapper = mountWithPlugins(CpeEditor, {
            global: {
                stubs: {
                    VCard: passThrough,
                    VCardTitle: passThrough,
                    VSpacer: true,
                    VBtn: true,
                    VDataTable: true,
                    VDialog: passThrough,
                    VCardText: passThrough,
                    VToolbar: passThrough,
                    VToolbarTitle: passThrough,
                    VCombobox: VTextField,
                    VTextField,
                    DialogToolbar: true
                }
            }
        })
        const settingsStore = useSettingsStore()
        settingsStore.spellcheck = true

        const fields = wrapper.findAll('input[data-label]')
        expect(fields).toHaveLength(2)
        expect(fields[0]?.attributes('spellcheck')).toBe('false')
        expect(fields[1]?.attributes('spellcheck')).toBe('true')
    })
})
