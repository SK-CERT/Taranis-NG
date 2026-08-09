import { defineComponent, h } from 'vue'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mountWithPlugins } from '../helpers/mount-helpers'
import AiProvidersTab from '@/components/config/data-providers/AiProvidersTab.vue'
import DataProvidersTab from '@/components/config/data-providers/DataProvidersTab.vue'

const { configStore } = vi.hoisted(() => ({
    configStore: {
        aiProviders: { items: [] },
        dataProviders: { items: [] },
        loadAiProviders: vi.fn().mockResolvedValue(undefined),
        loadDataProviders: vi.fn().mockResolvedValue(undefined)
    }
}))

vi.mock('@/stores/config', () => ({ useConfigStore: () => configStore }))
vi.mock('@/composables/useAuth', () => ({ useAuth: () => ({ checkPermission: () => true }) }))

const VDataTableStub = defineComponent({
    name: 'VDataTable',
    props: {
        items: {
            type: Array,
            default: () => []
        }
    },
    setup(props, { slots }) {
        return () =>
            h(
                'div',
                props.items.map((item) => slots['item.updated_at']?.({ item }))
            )
    }
})

const stubs = {
    VDataTable: VDataTableStub,
    NewAiProvider: true,
    NewDataProvider: true,
    SearchField: true,
    ActionButton: true,
    ConfirmationDialog: true
}

describe.each([
    ['AI provider', AiProvidersTab, 'aiProviders'],
    ['data provider', DataProvidersTab, 'dataProviders']
])('%s table timestamp', (_label, component, stateKey) => {
    beforeEach(() => {
        vi.clearAllMocks()
        configStore.aiProviders.items = []
        configStore.dataProviders.items = []
    })

    it('locale-formats valid values, preserves invalid raw fallbacks, and uses automatic direction', async () => {
        const rawTimestamp = '2026-08-09T17:30:00.000Z'
        const items = [
            { id: 1, name: 'Valid', updated_at: rawTimestamp },
            { id: 2, name: 'Legacy', updated_at: 'وقت قديم' },
            { id: 3, name: 'Missing' }
        ]
        configStore[stateKey].items = items
        const wrapper = mountWithPlugins(component, { global: { stubs } })

        wrapper.vm.$i18n.locale = 'ar'
        await wrapper.vm.$nextTick()

        const expectedTimestamp = new Intl.DateTimeFormat('ar', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(rawTimestamp))
        const timestamps = wrapper.findAll('bdi[dir="auto"]').map((value) => value.text())

        expect(timestamps).toEqual([expectedTimestamp, 'وقت قديم', ''])
        expect(items.map((item) => item.updated_at)).toEqual([rawTimestamp, 'وقت قديم', undefined])
    })
})
