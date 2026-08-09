import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import NodesManager from '@/components/common/nodes/NodesManager.vue'

const mocks = vi.hoisted(() => ({
    loadCollectorsNodes: vi.fn(),
    deleteCollectorsNode: vi.fn()
}))

vi.mock('@/stores/config', () => ({
    useConfigStore: () => ({
        collectorsNodes: { items: [], total_count: 0 },
        loadCollectorsNodes: mocks.loadCollectorsNodes
    })
}))

vi.mock('@/api/config', () => ({
    createNewCollectorsNode: vi.fn(),
    updateCollectorsNode: vi.fn(),
    deleteCollectorsNode: mocks.deleteCollectorsNode,
    createNewPresentersNode: vi.fn(),
    updatePresentersNode: vi.fn(),
    deletePresentersNode: vi.fn(),
    createNewPublishersNode: vi.fn(),
    updatePublishersNode: vi.fn(),
    deletePublishersNode: vi.fn(),
    createNewBotsNode: vi.fn(),
    updateBotsNode: vi.fn(),
    deleteBotsNode: vi.fn()
}))

const mountedWrappers = []

const ToolbarFilterStub = {
    name: 'ToolbarFilter',
    props: ['totalCount', 'totalCountTitle'],
    template: '<div><slot name="addbutton" /></div>'
}

const mountManager = () => {
    const wrapper = mount(NodesManager, {
        props: { type: 'collectors' },
        global: {
            stubs: {
                VContainer: { template: '<div><slot /></div>' },
                ToolbarFilter: ToolbarFilterStub,
                ContentData: true,
                NodeDialog: true
            }
        }
    })
    mountedWrappers.push(wrapper)
    return wrapper
}

const notificationDetails = (dispatchEvent) =>
    dispatchEvent.mock.calls.filter(([event]) => event.type === 'notification').map(([event]) => event.detail)

describe('NodesManager feedback', () => {
    let dispatchEvent

    beforeEach(() => {
        vi.clearAllMocks()
        mocks.loadCollectorsNodes.mockResolvedValue(undefined)
        mocks.deleteCollectorsNode.mockResolvedValue(undefined)
        dispatchEvent = vi.spyOn(window, 'dispatchEvent')
        vi.spyOn(console, 'error').mockImplementation(() => undefined)
    })

    afterEach(() => {
        for (const wrapper of mountedWrappers.splice(0)) wrapper.unmount()
        vi.restoreAllMocks()
    })

    it('shows an error notification and preserves diagnostics when loading fails', async () => {
        const error = new Error('load failed')
        mocks.loadCollectorsNodes.mockRejectedValue(error)

        mountManager()
        await flushPromises()

        expect(notificationDetails(dispatchEvent)).toContainEqual({ type: 'error', loc: 'common.error' })
        expect(console.error).toHaveBeenCalledWith('Error loading collectors nodes:', error)
    })

    it('passes the node-specific complete count message and numeric choice to the toolbar', async () => {
        const wrapper = mountManager()
        await flushPromises()

        const toolbar = wrapper.findComponent(ToolbarFilterStub)
        expect(toolbar.props('totalCountTitle')).toBe('collectors.nodes.total_count')
        expect(toolbar.props('totalCount')).toBe(0)
    })

    it('shows success feedback after deleting a node', async () => {
        const wrapper = mountManager()
        await flushPromises()

        await wrapper.vm.handleDelete({ id: 'node-1' })

        expect(mocks.deleteCollectorsNode).toHaveBeenCalledWith({ id: 'node-1' })
        expect(notificationDetails(dispatchEvent)).toContainEqual({
            type: 'success',
            loc: 'common.deleted_successfully'
        })
        expect(mocks.loadCollectorsNodes).toHaveBeenCalledTimes(2)
    })

    it('shows an error notification and preserves diagnostics when deletion fails', async () => {
        const error = new Error('delete failed')
        mocks.deleteCollectorsNode.mockRejectedValue(error)
        const wrapper = mountManager()
        await flushPromises()

        await wrapper.vm.handleDelete({ id: 'node-1' })

        expect(notificationDetails(dispatchEvent)).toContainEqual({ type: 'error', loc: 'common.error_deleting' })
        expect(console.error).toHaveBeenCalledWith('Error deleting collectors node:', error)
        expect(mocks.loadCollectorsNodes).toHaveBeenCalledOnce()
    })
})
