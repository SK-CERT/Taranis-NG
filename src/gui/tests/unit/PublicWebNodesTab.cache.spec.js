import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { mountWithPlugins } from '../helpers/mount-helpers'
import PublicWebNodesTab from '@/components/config/public-web/PublicWebNodesTab.vue'
import { getAllPublicWebNodes, resetPublicWebNodeCache } from '@/api/config'

// A public-web node's cache can be cleared on demand, so a change shows now rather than when
// the node's cache would expire.

const { NODES } = vi.hoisted(() => ({
    NODES: [
        { id: 1, name: 'Default Public Web', description: '', status: 'green', api_url: 'http://public-web', enabled: true },
        { id: 2, name: 'Offline copy', description: '', status: 'red', api_url: '', enabled: true }
    ]
}))

vi.mock('@/api/config', () => ({
    getAllPublicWebNodes: vi.fn(),
    getPublicWebs: vi.fn().mockResolvedValue({ data: { items: [] } }),
    deletePublicWebNode: vi.fn(),
    deletePublicWeb: vi.fn(),
    updatePublicWeb: vi.fn(),
    updatePublicWebNode: vi.fn(),
    createNewPublicWebNode: vi.fn(),
    resetPublicWebNodeCache: vi.fn()
}))

const permissions = vi.hoisted(() => ({ update: true }))
vi.mock('@/composables/useAuth', () => ({
    useAuth: () => ({ checkPermission: (permission) => permission !== 'CONFIG_PUBLIC_WEB_NODE_UPDATE' || permissions.update })
}))

const mounted = []
const notifications = []
const onNotification = (event) => notifications.push(event.detail)

async function mountTab() {
    const wrapper = mountWithPlugins(PublicWebNodesTab, { global: { stubs: { NewPublicWebNode: true, NewPublicWeb: true } } })
    mounted.push(wrapper)
    await flushPromises()
    return wrapper
}

const panel = (wrapper, name) => wrapper.findAll('.v-expansion-panel').find((candidate) => candidate.text().includes(name))
const clearButton = (panelWrapper) => panelWrapper.find('[data-test="node-clear-cache"]')

describe('PublicWebNodesTab clear cache', () => {
    beforeEach(() => {
        vi.clearAllMocks()
        permissions.update = true
        notifications.length = 0
        window.addEventListener('notification', onNotification)
        vi.mocked(getAllPublicWebNodes).mockResolvedValue({ data: { total_count: NODES.length, items: NODES } })
    })
    afterEach(() => {
        window.removeEventListener('notification', onNotification)
        while (mounted.length) mounted.pop().unmount()
    })

    it('clears a node cache, says so and re-reads the nodes for their health', async () => {
        vi.mocked(resetPublicWebNodeCache).mockResolvedValue({ data: { reset: true } })
        const wrapper = await mountTab()
        const loads = getAllPublicWebNodes.mock.calls.length

        const button = clearButton(panel(wrapper, 'Default Public Web'))
        expect(button.attributes('title')).toBe('Clear cache')
        await button.trigger('click')
        await flushPromises()

        expect(resetPublicWebNodeCache).toHaveBeenCalledWith(1)
        expect(notifications).toEqual([{ type: 'success', loc: 'public_web.nodes.cache_cleared', params: { name: 'Default Public Web' } }])
        expect(getAllPublicWebNodes).toHaveBeenCalledTimes(loads + 1)
    })

    it('says when the node could not clear it', async () => {
        vi.spyOn(console, 'error').mockImplementation(() => {})
        vi.mocked(resetPublicWebNodeCache).mockRejectedValue(new Error('503'))
        const wrapper = await mountTab()

        await clearButton(panel(wrapper, 'Default Public Web')).trigger('click')
        await flushPromises()

        expect(notifications).toEqual([{ type: 'error', loc: 'public_web.nodes.cache_clear_failed', params: { name: 'Default Public Web' } }])
    })

    it('offers it only for a node core can reach, to whoever may change nodes', async () => {
        const wrapper = await mountTab()
        expect(clearButton(panel(wrapper, 'Offline copy')).exists()).toBe(false)

        permissions.update = false
        const readOnly = await mountTab()
        expect(clearButton(panel(readOnly, 'Default Public Web')).exists()).toBe(false)
    })
})
