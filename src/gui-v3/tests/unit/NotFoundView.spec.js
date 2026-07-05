import { describe, it, expect } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { mountWithPlugins } from '../helpers/mount-helpers'
import NotFoundView from '@/views/NotFoundView.vue'

async function mountAt(path = '/does-not-exist') {
    const router = createRouter({
        history: createMemoryHistory(),
        routes: [
            { path: '/', name: 'home', component: { template: '<div>home</div>' } },
            { path: '/:pathMatch(.*)*', name: 'not_found', component: NotFoundView }
        ]
    })
    router.push(path)
    await router.isReady()

    const wrapper = mountWithPlugins(NotFoundView, {
        global: { plugins: [router] }
    })
    return { wrapper, router }
}

describe('NotFoundView', () => {
    // ── Rendering ─────────────────────────────────
    it('renders the 404 heading, title and message', async () => {
        const { wrapper } = await mountAt('/config/does-not-exist')
        expect(wrapper.text()).toContain('404')
        expect(wrapper.text()).toContain('Page not found')
        expect(wrapper.text()).toContain('doesn’t exist')
    })

    it('shows the attempted path', async () => {
        const { wrapper } = await mountAt('/config/does-not-exist')
        expect(wrapper.text()).toContain('/config/does-not-exist')
    })

    it('reflects a different unknown top-level path', async () => {
        const { wrapper } = await mountAt('/totally-unknown')
        expect(wrapper.text()).toContain('/totally-unknown')
    })

    // ── Navigation ────────────────────────────────
    it('navigates home when "Go to home" is clicked', async () => {
        const { wrapper, router } = await mountAt('/config/does-not-exist')

        const homeBtn = wrapper.findAllComponents({ name: 'VBtn' }).find((b) => b.text().includes('Go to home'))
        expect(homeBtn).toBeTruthy()

        await homeBtn.trigger('click')
        await flushPromises()

        expect(router.currentRoute.value.path).toBe('/')
    })
})
