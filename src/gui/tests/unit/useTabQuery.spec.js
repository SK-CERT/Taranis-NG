import { describe, it, expect } from 'vitest'
import { defineComponent, nextTick } from 'vue'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { useTabQuery } from '@/composables/useTabQuery'

// Minimal host component that exercises the composable.
const Harness = defineComponent({
    props: {
        tabs: { type: Array, required: true },
        def: { type: String, required: true }
    },
    setup(props) {
        const activeTab = useTabQuery(props.tabs, props.def)
        return { activeTab }
    },
    template: '<div>{{ activeTab }}</div>'
})

async function mountWithRouter(initialQuery = {}, tabs = ['a', 'b', 'c'], def = 'a') {
    const router = createRouter({
        history: createMemoryHistory(),
        routes: [{ path: '/', component: Harness }]
    })
    router.push({ path: '/', query: initialQuery })
    await router.isReady()

    const wrapper = mount(Harness, {
        props: { tabs, def },
        global: { plugins: [router] }
    })
    return { wrapper, router }
}

describe('useTabQuery', () => {
    // ── Initialisation ────────────────────────────
    it('initialises from a valid ?tab= query', async () => {
        const { wrapper } = await mountWithRouter({ tab: 'b' })
        expect(wrapper.vm.activeTab).toBe('b')
    })

    it('falls back to the default tab when the query is missing', async () => {
        const { wrapper } = await mountWithRouter({})
        expect(wrapper.vm.activeTab).toBe('a')
    })

    it('falls back to the default tab when the query is invalid', async () => {
        const { wrapper } = await mountWithRouter({ tab: 'does-not-exist' })
        expect(wrapper.vm.activeTab).toBe('a')
    })

    // ── Syncing tab -> URL ────────────────────────
    it('writes the active tab to the URL query', async () => {
        const { wrapper, router } = await mountWithRouter({})
        wrapper.vm.activeTab = 'c'
        await flushPromises()
        expect(router.currentRoute.value.query.tab).toBe('c')
    })

    // ── Syncing URL -> tab ────────────────────────
    it('reacts to external query changes (deep links / back-forward)', async () => {
        const { wrapper, router } = await mountWithRouter({ tab: 'a' })
        await router.push({ path: '/', query: { tab: 'b' } })
        await nextTick()
        expect(wrapper.vm.activeTab).toBe('b')
    })

    it('resets to the default when the query changes to an invalid value', async () => {
        const { wrapper, router } = await mountWithRouter({ tab: 'b' })
        await router.push({ path: '/', query: { tab: 'nope' } })
        await nextTick()
        expect(wrapper.vm.activeTab).toBe('a')
    })
})
