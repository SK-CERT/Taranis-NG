import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, nextTick, reactive } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { usePermissionTabs } from '@/composables/usePermissionTabs'

const allowedPermissions = reactive(new Set())
const checkPermission = vi.fn((permission) => allowedPermissions.has(permission))

vi.mock('@/composables/useAuth', () => ({
    useAuth: () => ({ checkPermission })
}))

const sourcesMounted = vi.fn()
const nodesMounted = vi.fn()
const mountedWrappers = []

const SourcesTab = defineComponent({
    name: 'SourcesTab',
    setup() {
        sourcesMounted()
    },
    template: '<div>sources content</div>'
})

const NodesTab = defineComponent({
    name: 'NodesTab',
    setup() {
        nodesMounted()
    },
    template: '<div>nodes content</div>'
})

const tabs = [
    { value: 'sources', permission: 'CONFIG_OSINT_SOURCE_ACCESS', component: SourcesTab },
    { value: 'nodes', permission: 'CONFIG_COLLECTORS_NODE_ACCESS', component: NodesTab }
]

const Harness = defineComponent({
    setup() {
        return usePermissionTabs(tabs)
    },
    template: `
        <nav>
            <span v-for="tab in availableTabs" :key="tab.value" :data-tab="tab.value" />
        </nav>
        <template v-for="tab in availableTabs" :key="tab.value">
            <component
                :is="tab.component"
                v-if="activeTab === tab.value"
            />
        </template>
    `
})

async function mountAt(tab) {
    const router = createRouter({
        history: createMemoryHistory(),
        routes: [{ path: '/', component: Harness }]
    })
    await router.push({ path: '/', query: tab ? { tab } : {} })
    await router.isReady()

    const wrapper = mount(Harness, { global: { plugins: [router] } })
    mountedWrappers.push(wrapper)
    await flushPromises()
    return { wrapper, router }
}

describe('configuration tab permissions', () => {
    beforeEach(() => {
        allowedPermissions.clear()
        checkPermission.mockClear()
        sourcesMounted.mockClear()
        nodesMounted.mockClear()
    })

    afterEach(() => {
        for (const wrapper of mountedWrappers.splice(0)) {
            wrapper.unmount()
        }
    })

    it('filters forbidden tabs and never mounts their content', async () => {
        allowedPermissions.add('CONFIG_COLLECTORS_NODE_ACCESS')

        const { wrapper } = await mountAt('nodes')

        expect(wrapper.find('[data-tab="sources"]').exists()).toBe(false)
        expect(wrapper.find('[data-tab="nodes"]').exists()).toBe(true)
        expect(sourcesMounted).not.toHaveBeenCalled()
        expect(nodesMounted).toHaveBeenCalledOnce()
    })

    it('normalizes a forbidden deep link to the first permitted tab', async () => {
        allowedPermissions.add('CONFIG_COLLECTORS_NODE_ACCESS')

        const { wrapper, router } = await mountAt('sources')

        expect(wrapper.vm.activeTab).toBe('nodes')
        expect(router.currentRoute.value.query.tab).toBe('nodes')
        expect(sourcesMounted).not.toHaveBeenCalled()
        expect(nodesMounted).toHaveBeenCalledOnce()
    })

    it('normalizes invalid external query changes', async () => {
        allowedPermissions.add('CONFIG_OSINT_SOURCE_ACCESS')
        allowedPermissions.add('CONFIG_COLLECTORS_NODE_ACCESS')
        const { wrapper, router } = await mountAt('nodes')

        await router.push({ path: '/', query: { tab: 'unknown' } })
        await nextTick()
        await flushPromises()

        expect(wrapper.vm.activeTab).toBe('sources')
        expect(router.currentRoute.value.query.tab).toBe('sources')
    })

    it('renders no content when no child tab is permitted', async () => {
        const { wrapper } = await mountAt('sources')

        expect(wrapper.findAll('[data-tab]').length).toBe(0)
        expect(wrapper.vm.activeTab).toBe('')
        expect(sourcesMounted).not.toHaveBeenCalled()
        expect(nodesMounted).not.toHaveBeenCalled()
    })

    it('moves away from the active tab when its permission is revoked', async () => {
        allowedPermissions.add('CONFIG_OSINT_SOURCE_ACCESS')
        allowedPermissions.add('CONFIG_COLLECTORS_NODE_ACCESS')
        const { wrapper, router } = await mountAt('nodes')

        allowedPermissions.delete('CONFIG_COLLECTORS_NODE_ACCESS')
        await nextTick()
        await flushPromises()

        expect(wrapper.vm.activeTab).toBe('sources')
        expect(router.currentRoute.value.query.tab).toBe('sources')
        expect(wrapper.find('[data-tab="nodes"]').exists()).toBe(false)
    })
})
