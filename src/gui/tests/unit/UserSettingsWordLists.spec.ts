/* eslint-disable vue/one-component-per-file -- compact test-only Vuetify stubs */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, nextTick } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import UserSettings from '@/components/UserSettings.vue'

const { settingsStore, tMock } = vi.hoisted(() => ({
    settingsStore: {
        getProfileWordLists: [] as Array<{ id: number; name: string }>,
        getAvailableWordListsComputed: [] as Array<{ id: number; name: string }>,
        getProfileHotkeys: [] as Array<{ alias: string; icon: string; key: string }>,
        loadUserWordLists: vi.fn(),
        loadAvailableWordLists: vi.fn(),
        loadUserHotkeys: vi.fn(),
        saveUserWordLists: vi.fn(),
        saveUserHotkeys: vi.fn(),
        resetHotkeys: vi.fn()
    },
    tMock: vi.fn((key: string, params?: { action?: string }) => (params?.action ? `${key}: ${params.action}` : key))
}))

vi.mock('@/stores/settings', () => ({
    useSettingsStore: () => settingsStore
}))

vi.mock('vue-i18n', () => ({
    useI18n: () => ({ t: tMock })
}))

const passthroughStub = defineComponent({ template: '<div><slot /></div>' })
const DialogStub = defineComponent({
    name: 'VDialog',
    props: {
        modelValue: { type: Boolean, default: false },
        maxWidth: { type: [String, Number], default: undefined }
    },
    emits: ['keydown'],
    computed: {
        isKeyDialog(): boolean {
            return String(this.maxWidth) === '300'
        },
        isVisible(): boolean {
            return !this.isKeyDialog || this.modelValue
        }
    },
    template: `
        <div
            v-if="isVisible"
            :data-test="isKeyDialog ? 'key-dialog' : 'settings-dialog'"
            @keydown="$emit('keydown', $event)"
        >
            <slot />
        </div>
    `
})
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

const I18nTStub = defineComponent({
    name: 'I18nT',
    props: { keypath: { type: String, required: true } },
    template: '<span data-test="key-prompt">{{ keypath }}: <slot name="action" /></span>'
})

const mountDialog = () =>
    mount(UserSettings, {
        props: { modelValue: false },
        global: {
            stubs: {
                VDialog: DialogStub,
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
                I18nT: I18nTStub,
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

    it('edits only the selected hotkey through the key prompt and saves the result', async () => {
        settingsStore.getProfileHotkeys = [
            { alias: 'publish', icon: 'mdi-publish', key: 'p' },
            { alias: 'assess', icon: 'mdi-file-search', key: 'a' }
        ]
        const wrapper = mountDialog()
        await wrapper.setProps({ modelValue: true })
        await flushPromises()

        expect(wrapper.find('[data-test="key-dialog"]').exists()).toBe(false)
        expect(wrapper.find('[data-test="key-prompt"]').exists()).toBe(false)

        const publishButton = wrapper.findAll('.hotkey-card').find((button) => button.text().includes('settings.publish'))
        expect(publishButton).toBeDefined()
        await publishButton!.trigger('click')
        await nextTick()

        expect(wrapper.get('[data-test="key-prompt"]').text()).toContain('settings.press_key_for: settings.publish')
        expect(wrapper.get('[data-test="key-prompt"] strong').text()).toBe('settings.publish')

        const keyEvent = new KeyboardEvent('keydown', { key: 'z', bubbles: true, cancelable: true })
        wrapper.get('[data-test="key-dialog"]').element.dispatchEvent(keyEvent)
        await nextTick()

        expect(keyEvent.defaultPrevented).toBe(true)
        expect(wrapper.find('[data-test="key-dialog"]').exists()).toBe(false)
        expect(wrapper.findAll('.hotkey-card').map((button) => button.find('kbd').text())).toEqual(['z', 'a'])

        await wrapper.findAll('button')[1]!.trigger('click')
        await flushPromises()

        expect(settingsStore.saveUserHotkeys).toHaveBeenCalledWith([
            { alias: 'publish', icon: 'mdi-publish', key: 'z' },
            { alias: 'assess', icon: 'mdi-file-search', key: 'a' }
        ])
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
