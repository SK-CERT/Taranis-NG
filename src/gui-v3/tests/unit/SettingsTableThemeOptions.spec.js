/* eslint-disable vue/one-component-per-file -- test harness uses minimal inline components */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import SettingsTable from '@/components/config/SettingsTable.vue'
import { themeFamilies } from '@/themes'

const { settingsStore, themeChange } = vi.hoisted(() => ({
    settingsStore: {
        getSettings: [],
        getDateTimeFormat: 'yyyy-MM-dd',
        loadSettings: vi.fn().mockResolvedValue(undefined),
        saveSettings: vi.fn().mockResolvedValue(undefined)
    },
    themeChange: vi.fn()
}))

vi.mock('@/i18n', () => ({
    supportedLocales: ['en']
}))

vi.mock('@/stores/settings', () => ({
    useSettingsStore: () => settingsStore
}))

vi.mock('vue-i18n', () => ({
    useI18n: () => ({
        t: (key) => key,
        te: () => false,
        locale: { value: 'en' }
    })
}))

vi.mock('vuetify', () => ({
    useTheme: () => ({ change: themeChange, global: { name: { value: 'taranis-light' } } })
}))

const DataTableStub = defineComponent({
    name: 'VDataTable',
    props: { items: { type: Array, default: () => [] } },
    template: `
        <div>
            <div v-for="item in items" :key="item.key">
                <slot name="item.value" :item="item" />
            </div>
        </div>
    `
})

const SelectStub = defineComponent({
    name: 'VSelect',
    props: {
        modelValue: { type: String, default: '' },
        items: { type: Array, default: () => [] }
    },
    template: '<div class="select-stub" />'
})

const passthroughStub = (name) => defineComponent({ name, template: '<div><slot /></div>' })

function mountTable() {
    const pinia = createPinia()
    setActivePinia(pinia)
    return mount(SettingsTable, {
        props: { globalSetting: false },
        global: {
            plugins: [pinia],
            stubs: {
                VContainer: passthroughStub('VContainer'),
                VCard: passthroughStub('VCard'),
                VCardText: passthroughStub('VCardText'),
                VRow: passthroughStub('VRow'),
                VCol: passthroughStub('VCol'),
                VDataTable: DataTableStub,
                VSelect: SelectStub,
                VSwitch: true,
                VIcon: true,
                VChip: true,
                SearchField: true,
                VDialog: true
            }
        }
    })
}

describe('SettingsTable theme options', () => {
    beforeEach(() => {
        themeChange.mockClear()
        settingsStore.saveSettings.mockClear()
        settingsStore.getSettings = [
            { key: 'SPELLCHECK', value: 'true', type: 'B', is_global: false },
            { key: 'UI_THEME', value: 'taranis', type: 'S', options: '', is_global: false },
            { key: 'DARK_THEME', value: 'false', type: 'B', is_global: false }
        ]
    })

    // The setting ships with empty `options`, so the dropdown has to come from
    // the frontend registry - that is what lets a new theme skip the migration.
    it('offers every registered theme family despite empty database options', async () => {
        const wrapper = mountTable()
        await flushPromises()

        const selects = wrapper.findAllComponents(SelectStub)
        expect(selects).toHaveLength(1)
        expect(selects[0].props('items').map(({ id }) => id)).toEqual(themeFamilies.map((family) => family.id))
    })

    it('keeps the theme picker next to the dark/light switch', async () => {
        const wrapper = mountTable()
        await flushPromises()

        const keys = wrapper.vm.records.map((record) => record.key)
        expect(Math.abs(keys.indexOf('UI_THEME') - keys.indexOf('DARK_THEME'))).toBe(1)
    })

    it('applies the chosen family to the current variant', async () => {
        const wrapper = mountTable()
        await flushPromises()

        await wrapper.vm.updateSetting({ key: 'UI_THEME', value: 'taranis', type: 'S' }, 'forest')

        expect(settingsStore.saveSettings).toHaveBeenCalledWith({
            data: expect.objectContaining({ key: 'UI_THEME', value: 'forest' }),
            is_global: false
        })
        expect(themeChange).toHaveBeenLastCalledWith('forest-light')
    })

    it('keeps the chosen family when the variant is toggled', async () => {
        const wrapper = mountTable()
        await flushPromises()

        await wrapper.vm.updateSetting({ key: 'UI_THEME', value: 'taranis', type: 'S' }, 'amber')
        await wrapper.vm.updateSetting({ key: 'DARK_THEME', value: 'false', type: 'B' }, 'true')

        expect(themeChange).toHaveBeenLastCalledWith('amber-dark')
    })

    it('falls back to the default family when the stored value names a removed theme', async () => {
        const wrapper = mountTable()
        await flushPromises()

        // The composable holds the active variant as app-global state, so pin it
        // here rather than relying on whatever an earlier case left behind.
        await wrapper.vm.updateSetting({ key: 'DARK_THEME', value: 'true', type: 'B' }, 'false')
        await wrapper.vm.updateSetting({ key: 'UI_THEME', value: 'taranis', type: 'S' }, 'retired-theme')

        expect(themeChange).toHaveBeenLastCalledWith('taranis-light')
    })
})
