import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { mountWithPlugins } from '../helpers/mount-helpers'
import PublicWebNodesTab from '@/components/config/public-web/PublicWebNodesTab.vue'
import { getAllPublicWebNodes, getPublicWebs } from '@/api/config'

// The health dot is derived server-side from last_seen, which core refreshes by pinging
// each node once a minute. The tab used to load once on mount, so the dot froze at
// page-load state: a node that came up a moment later stayed red until the page was
// reloaded. These tests pin the refresh, and — just as importantly — pin what the
// refresh must NOT disturb.

const { NODES } = vi.hoisted(() => ({
    NODES: [{ id: 1, name: 'Default Public Web', description: '', status: 'red', last_seen: null }]
}))

// Replaces the module wholesale, so every export the component chain reaches must be
// here; a missing one throws on property access and the component swallows it.
vi.mock('@/api/config', () => ({
    getAllPublicWebNodes: vi.fn().mockResolvedValue({ data: { total_count: NODES.length, items: NODES } }),
    getPublicWebs: vi.fn().mockResolvedValue({ data: { items: [] } }),
    deletePublicWebNode: vi.fn().mockResolvedValue({ data: {} }),
    deletePublicWeb: vi.fn().mockResolvedValue({ data: {} }),
    updatePublicWeb: vi.fn().mockResolvedValue({ data: {} })
}))

vi.mock('@/composables/useAuth', () => ({
    useAuth: () => ({ checkPermission: () => true })
}))

// Every mounted tab is torn down after its test. A tab left mounted keeps its
// visibilitychange listener on `document`, so a later test's dispatch would reach every
// previous test's component too - the counts then measure leakage, not behaviour.
const mounted = []

async function mountTab() {
    const wrapper = mountWithPlugins(PublicWebNodesTab)
    mounted.push(wrapper)
    await flushPromises()
    await wrapper.vm.$nextTick()
    return wrapper
}

describe('PublicWebNodesTab health status', () => {
    // One spy over a mutable flag: re-spying on the same accessor stacks getters, and
    // the later mockReturnValue then never wins.
    let hidden = false

    beforeEach(() => {
        vi.clearAllMocks()
        vi.useFakeTimers()
        hidden = false
        // jsdom reports the document as visible; the component skips the poll when hidden.
        vi.spyOn(document, 'hidden', 'get').mockImplementation(() => hidden)
    })

    afterEach(() => {
        while (mounted.length) mounted.pop().unmount()
        vi.useRealTimers()
        vi.restoreAllMocks()
    })

    it('loads the nodes on mount', async () => {
        await mountTab()
        expect(getAllPublicWebNodes).toHaveBeenCalledTimes(1)
    })

    it('re-fetches the nodes while the tab stays open', async () => {
        await mountTab()
        expect(getAllPublicWebNodes).toHaveBeenCalledTimes(1)

        await vi.advanceTimersByTimeAsync(30_000)
        expect(getAllPublicWebNodes).toHaveBeenCalledTimes(2)

        await vi.advanceTimersByTimeAsync(30_000)
        expect(getAllPublicWebNodes).toHaveBeenCalledTimes(3)
    })

    it('refreshes only the node list, not every node’s webs', async () => {
        await mountTab()
        const websOnMount = getPublicWebs.mock.calls.length

        await vi.advanceTimersByTimeAsync(30_000)

        // loadNodes() would re-fetch the webs of every node (an N+1 the dot does not
        // need) and re-expand the panels the user may have just collapsed.
        expect(getPublicWebs).toHaveBeenCalledTimes(websOnMount)
    })

    it('stops polling once the tab is torn down', async () => {
        const wrapper = await mountTab()
        await vi.advanceTimersByTimeAsync(30_000)
        const afterOneTick = getAllPublicWebNodes.mock.calls.length

        wrapper.unmount()
        await vi.advanceTimersByTimeAsync(120_000)

        // A surviving interval keeps polling core forever from a component nobody is
        // looking at, once per navigation to this tab.
        expect(getAllPublicWebNodes).toHaveBeenCalledTimes(afterOneTick)
    })

    it('does not poll while the tab is in the background', async () => {
        await mountTab()
        hidden = true

        await vi.advanceTimersByTimeAsync(90_000)

        expect(getAllPublicWebNodes).toHaveBeenCalledTimes(1)
    })

    it('catches up as soon as the tab is looked at again', async () => {
        await mountTab()
        hidden = true
        await vi.advanceTimersByTimeAsync(90_000)
        expect(getAllPublicWebNodes).toHaveBeenCalledTimes(1)

        hidden = false
        document.dispatchEvent(new Event('visibilitychange'))
        await flushPromises()

        // Without this the dot would stay stale for up to a further poll interval
        // after the operator switches back.
        expect(getAllPublicWebNodes).toHaveBeenCalledTimes(2)
    })
})
