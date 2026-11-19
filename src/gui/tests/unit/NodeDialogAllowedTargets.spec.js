/**
 * The collectors node dialog carries "Allowed internal targets": the internal hosts and
 * networks the node's sources may be fetched from. Collectors fetch from public addresses
 * only, and this list - edited with the node permissions, not the source ones - is the
 * exception. The other node types have no such field.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { mountWithPlugins } from '../helpers/mount-helpers'
import NodeDialog from '@/components/common/nodes/NodeDialog.vue'
import { createNewCollectorsNode, updateCollectorsNode, updatePresentersNode } from '@/api/config'

vi.mock('@/api/config', () => ({
    createNewCollectorsNode: vi.fn(),
    updateCollectorsNode: vi.fn(),
    deleteCollectorsNode: vi.fn(),
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

vi.mock('@/composables/useAuth', () => ({
    useAuth: () => ({ checkPermission: () => true })
}))

const NODE = { id: 'node-1', name: 'Collectors', description: '', api_url: 'http://collectors.example.org', api_key: '', api_key_set: true }
const FIELD = '[data-test="node-allowed-private-targets"]'

async function openDialog(type, editItem) {
    const wrapper = mountWithPlugins(NodeDialog, { props: { type, editItem }, attachTo: document.body })
    await flushPromises()
    wrapper.vm.formRef = { validate: () => Promise.resolve({ valid: true }), reset: () => undefined }
    return wrapper
}

describe('NodeDialog allowed internal targets', () => {
    beforeEach(() => {
        vi.clearAllMocks()
        document.body.innerHTML = ''
        vi.spyOn(console, 'error').mockImplementation(() => undefined)
        createNewCollectorsNode.mockResolvedValue({})
        updateCollectorsNode.mockResolvedValue({})
        updatePresentersNode.mockResolvedValue({})
    })

    it('shows the stored list of a collectors node', async () => {
        const wrapper = await openDialog('collectors', { ...NODE, allowed_private_targets: 'intranet.example.org\n10.20.0.0/16' })

        const field = document.querySelector(`${FIELD} textarea`)
        expect(field).not.toBeNull()
        expect(field.value).toBe('intranet.example.org\n10.20.0.0/16')
        wrapper.unmount()
    })

    it('sends the edited list when the node is saved', async () => {
        const wrapper = await openDialog('collectors', { ...NODE, allowed_private_targets: '' })

        wrapper.vm.localItem.allowed_private_targets = 'intranet.example.org'
        await wrapper.vm.persist()

        expect(updateCollectorsNode).toHaveBeenCalledTimes(1)
        expect(updateCollectorsNode.mock.calls[0][0]).toMatchObject({ id: 'node-1', allowed_private_targets: 'intranet.example.org' })
        wrapper.unmount()
    })

    it('starts a new collectors node with an empty list', async () => {
        const wrapper = await openDialog('collectors', null)

        expect(wrapper.vm.localItem.allowed_private_targets).toBe('')
        wrapper.unmount()
    })

    it('shows why core refused the list', async () => {
        const reason = "Allowed internal targets: '0.0.0.0/0' covers every address; name the internal networks that sources are on"
        updateCollectorsNode.mockRejectedValue({ response: { data: { error: reason } } })
        const wrapper = await openDialog('collectors', { ...NODE, allowed_private_targets: '0.0.0.0/0' })

        expect(await wrapper.vm.persist()).toBe(false)
        await flushPromises()

        expect(document.body.textContent).toContain(reason)
        wrapper.unmount()
    })

    it('has no such field on the other node types', async () => {
        const wrapper = await openDialog('presenters', { ...NODE, name: 'Presenters' })

        expect(document.querySelector(FIELD)).toBeNull()
        wrapper.unmount()
    })
})
