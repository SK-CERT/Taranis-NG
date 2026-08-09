/* eslint-disable vue/one-component-per-file -- compact test-only Vuetify stubs */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, nextTick } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import UserSettings from '@/components/UserSettings.vue'

const { settingsStore } = vi.hoisted(() => ({
    settingsStore: {
        getProfileWordLists: [] as Array<{ id: number; name: string }>,
        getAvailableWordListsComputed: [] as Array<{ id: number; name: string }>,
        getProfileHotkeys: [],
        loadUserWordLists: vi.fn(),
        loadAvailableWordLists: vi.fn(),
        loadUserHotkeys: vi.fn(),
        saveUserWordLists: vi.fn(),
        saveUserHotkeys: vi.fn(),
        resetHotkeys: vi.fn()
    }
}))

vi.mock('@/stores/settings', () => ({
    useSettingsStore: () => settingsStore
}))

vi.mock('vue-i18n', () => ({
    useI18n: () => ({ t: (key: string) => key })
}))

const passthroughStub = defineComponent({ template: '<div><slot /></div>' })
const DataTableStub = defineComponent({
    name: 'VDataTable',
    props: {
        modelValue: { type: Array, default: () => [] },
        items: { type: Array, default: () => [] }
    },
    emits: ['update:modelValue'],
    template: '<div class="word-list-table" />'
})

const ButtonStub = defineComponent({
    name: 'VBtn',
    emits: ['click'],
    template: '<button @click="$emit(\'click\')"><slot /></button>'
})

const mountDialog = () =>
    mount(UserSettings, {
        props: { modelValue: false },
        global: {
            stubs: {
                VDialog: passthroughStub,
                VCard: passthroughStub,
                VToolbar: passthroughStub,
                VToolbarTitle: passthroughStub,
                VSpacer: passthroughStub,
                VBtn: ButtonStub,
                VIcon: passthroughStub,
                VTabs: passthroughStub,
                VTab: passthroughStub,
                VCardText: passthroughStub,
                VWindow: passthroughStub,
                VWindowItem: passthroughStub,
                VDataTable: DataTableStub,
                VRow: passthroughStub,
                VCol: passthroughStub,
                VProgressLinear: passthroughStub,
                SettingsTable: true,
                SecuritySettings: true
            }
        }
    })

describe('UserSettings word-list selection', () => {
    beforeEach(() => {
        vi.clearAllMocks()
        settingsStore.getProfileWordLists = [{ id: 2, name: 'Selected' }]
        settingsStore.getAvailableWordListsComputed = [
            { id: 1, name: 'Available' },
            { id: 2, name: 'Selected' }
        ]
        settingsStore.getProfileHotkeys = []
        settingsStore.loadUserWordLists.mockResolvedValue({})
        settingsStore.loadAvailableWordLists.mockResolvedValue({})
        settingsStore.loadUserHotkeys.mockResolvedValue({})
        settingsStore.saveUserWordLists.mockResolvedValue({})
        settingsStore.saveUserHotkeys.mockResolvedValue({})
    })

    it('shows all ACL-visible lists and preselects only the user lists', async () => {
        const wrapper = mountDialog()
        await wrapper.setProps({ modelValue: true })
        await flushPromises()

        expect(settingsStore.loadAvailableWordLists).toHaveBeenCalledWith({ search: '' })
        const table = wrapper.findComponent(DataTableStub)
        expect(table.props('items')).toEqual(settingsStore.getAvailableWordListsComputed)
        expect(table.props('modelValue')).toEqual([2])
    })

    it('does not instantiate security settings until the Security tab is selected', async () => {
        const wrapper = mountDialog()

        expect(wrapper.findComponent({ name: 'SecuritySettings' }).exists()).toBe(false)

        ;(wrapper.vm as unknown as { activeTab: string }).activeTab = 'security'
        await nextTick()

        expect(wrapper.findComponent({ name: 'SecuritySettings' }).exists()).toBe(true)
    })

    it('saves selected IDs using the backend object schema and supports an empty selection', async () => {
        const wrapper = mountDialog()
        await wrapper.setProps({ modelValue: true })
        await flushPromises()

        const table = wrapper.findComponent(DataTableStub)
        table.vm.$emit('update:modelValue', [1, 2])
        await wrapper.findAll('button')[1]!.trigger('click')
        await flushPromises()
        expect(settingsStore.saveUserWordLists).toHaveBeenLastCalledWith([{ id: 1 }, { id: 2 }])

        await wrapper.setProps({ modelValue: true })
        await flushPromises()
        wrapper.findComponent(DataTableStub).vm.$emit('update:modelValue', [])
        await wrapper.findAll('button')[1]!.trigger('click')
        await flushPromises()
        expect(settingsStore.saveUserWordLists).toHaveBeenLastCalledWith([])
    })
})
