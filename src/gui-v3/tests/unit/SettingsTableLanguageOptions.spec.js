import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import SettingsTable from '@/components/config/SettingsTable.vue'

const { settingsStore } = vi.hoisted(() => ({
    settingsStore: {
        getSettings: [],
        getDateTimeFormat: 'yyyy-MM-dd',
        loadSettings: vi.fn().mockResolvedValue(undefined),
        saveSettings: vi.fn().mockResolvedValue(undefined)
    }
}))

vi.mock('@/i18n', () => ({
    supportedLocales: ['en', 'de', 'pt-BR']
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
    useTheme: () => ({ global: { name: { value: 'light' } } })
}))

const DataTableStub = defineComponent({
    name: 'VDataTable',
    props: {
        items: { type: Array, default: () => [] }
    },
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

const passthroughStub = { template: '<div><slot /></div>' }

function mountTable() {
    return mount(SettingsTable, {
        props: { globalSetting: false },
        global: {
            stubs: {
                VContainer: passthroughStub,
                VCard: passthroughStub,
                VCardText: passthroughStub,
                VRow: passthroughStub,
                VCol: passthroughStub,
                VDataTable: DataTableStub,
                VSelect: SelectStub,
                SearchField: true,
                VDialog: true
            }
        }
    })
}

describe('SettingsTable language options', () => {
    beforeEach(() => {
        settingsStore.loadSettings.mockClear()
        settingsStore.getSettings = [
            {
                key: 'UI_LANGUAGE',
                value: 'en',
                type: 'S',
                options: null,
                is_global: false
            },
            {
                key: 'CONTENT_DEFAULT_LANGUAGE',
                value: 'en',
                type: 'S',
                options: JSON.stringify([
                    { id: 'en', txt: 'English' },
                    { id: 'ar', txt: 'Arabic' }
                ]),
                is_global: false
            }
        ]
    })

    it('discovers UI languages while retaining database options for content languages', async () => {
        const wrapper = mountTable()
        await flushPromises()

        const selects = wrapper.findAllComponents(SelectStub)
        expect(selects).toHaveLength(2)
        expect(selects[0].props('items').map(({ id }) => id)).toEqual(['en', 'de', 'pt-BR'])
        expect(selects[1].props('items').map(({ id }) => id)).toEqual(['en', 'ar'])
    })
})
