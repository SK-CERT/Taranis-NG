import { describe, it, expect, beforeEach, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createTestI18n } from '../helpers/mount-helpers'
import { useAssessStore } from '@/stores/assess'
import AssessView from '@/views/users/AssessView.vue'

/**
 * Every group tab is the same route record, so switching between them reuses the view. A
 * selection left over from the previous group would still be sent to a group action - which
 * always targets the group in the URL - and would merge news items across groups.
 */

vi.mock('@/api/assess', () => ({
    getManualOSINTSources: vi.fn().mockResolvedValue({ data: [] }),
    getNewsItemsByGroup: vi.fn().mockResolvedValue({ data: { total_count: 0, items: [] } }),
    voteNewsItemAggregate: vi.fn(),
    readNewsItemAggregate: vi.fn(),
    importantNewsItemAggregate: vi.fn(),
    deleteNewsItemAggregate: vi.fn(),
    saveNewsItemAggregate: vi.fn(),
    deleteNewsItem: vi.fn(),
    groupAction: vi.fn(),
    importantNewsItem: vi.fn(),
    readNewsItem: vi.fn(),
    voteNewsItem: vi.fn(),
    selectAllNewsItems: vi.fn()
}))

vi.mock('@/composables/useKeyboard', () => ({
    default: () => ({
        onInit: vi.fn(),
        keyAction: vi.fn(),
        reindexCardItems: vi.fn(),
        setDetailDialogCloseCallback: vi.fn(),
        setReloadCallback: vi.fn()
    })
}))

const vuetify = createVuetify({ components, directives })

const mountAssessView = async () => {
    const pinia = createPinia()
    setActivePinia(pinia)

    const router = createRouter({
        history: createMemoryHistory(),
        routes: [
            { path: '/', component: { template: '<div />' } },
            { path: '/assess/group/:groupId', name: 'assess', component: AssessView }
        ]
    })

    router.push('/assess/group/group-a')
    await router.isReady()

    const wrapper = mount(
        { template: '<router-view />' },
        {
            global: {
                plugins: [vuetify, createTestI18n(), pinia, router],
                stubs: {
                    ViewLayout: true,
                    ToolbarFilterAssess: true,
                    ContentDataAssess: true,
                    AddNewsItemDialog: true,
                    AddNewButton: true,
                    NewReportItem: true
                }
            }
        }
    )

    await flushPromises()

    return { wrapper, router, store: useAssessStore() }
}

describe('AssessView group switch', () => {
    beforeEach(() => {
        vi.clearAllMocks()
    })

    it('clears the selection when the group tab changes', async () => {
        const { router, store } = await mountAssessView()

        store.multiSelect(true)
        store.select({ id: 'a1', type: 'news_item_aggregate' })
        store.select({ id: 'a2', type: 'news_item_aggregate' })
        expect(store.getSelection).toHaveLength(2)

        await router.push('/assess/group/group-b')
        await flushPromises()

        expect(store.getSelection).toEqual([])
    })

    it('keeps multi-select mode on across the switch', async () => {
        const { router, store } = await mountAssessView()

        store.multiSelect(true)
        store.select({ id: 'a1', type: 'news_item_aggregate' })

        await router.push('/assess/group/group-b')
        await flushPromises()

        expect(store.getMultiSelect).toBe(true)
    })

    it('keeps the selection when the route is re-entered with the same group', async () => {
        const { router, store } = await mountAssessView()

        store.multiSelect(true)
        store.select({ id: 'a1', type: 'news_item_aggregate' })

        await router.push({ name: 'assess', params: { groupId: 'group-a' }, query: { q: 'x' } })
        await flushPromises()

        expect(store.getSelection).toHaveLength(1)
    })

    it('drops multi-select entirely when leaving the assess view', async () => {
        const { router, store } = await mountAssessView()

        store.multiSelect(true)
        store.select({ id: 'a1', type: 'news_item_aggregate' })

        await router.push('/')
        await flushPromises()

        expect(store.getMultiSelect).toBe(false)
        expect(store.getSelection).toEqual([])
    })
})
