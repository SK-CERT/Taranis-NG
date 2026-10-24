import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { mountWithPlugins } from '../helpers/mount-helpers'
import PublicWebNodesTab from '@/components/config/public-web/PublicWebNodesTab.vue'
import NewPublicWebNode from '@/components/config/public-web/NewPublicWebNode.vue'
import { getAllPublicWebNodes, getPublicWebs, updatePublicWebNode } from '@/api/config'

// A whole public-web node can be switched off: core then publishes none of its webs and
// serves it nothing. The webs keep their own switches for when it is back.

const { NODES } = vi.hoisted(() => ({
    NODES: [
        { id: 1, name: 'Default Public Web', description: '', status: 'green', last_seen: '07.11.2026 - 20:00:00', enabled: true },
        { id: 2, name: 'Remote', description: 'cesnet', status: 'red', last_seen: '07.11.2026 - 10:00:00', enabled: false }
    ]
}))

const nodesResponse = (changes = {}) => ({
    data: { total_count: NODES.length, items: NODES.map((node) => ({ ...node, ...(changes[node.id] || {}) })) }
})

vi.mock('@/api/config', () => ({
    getAllPublicWebNodes: vi.fn(),
    getPublicWebs: vi.fn().mockResolvedValue({ data: { items: [{ id: 1, name: 'Cyberfeed', hostname: 'feed.example', enabled: true }] } }),
    deletePublicWebNode: vi.fn().mockResolvedValue({ data: {} }),
    deletePublicWeb: vi.fn().mockResolvedValue({ data: {} }),
    updatePublicWeb: vi.fn().mockResolvedValue({ data: {} }),
    updatePublicWebNode: vi.fn().mockResolvedValue({ data: {} }),
    createNewPublicWebNode: vi.fn().mockResolvedValue({ data: {} })
}))

const permissions = vi.hoisted(() => ({ update: true }))
vi.mock('@/composables/useAuth', () => ({
    useAuth: () => ({ checkPermission: (permission) => permission !== 'CONFIG_PUBLIC_WEB_NODE_UPDATE' || permissions.update })
}))

const mounted = []

async function mountTab() {
    const wrapper = mountWithPlugins(PublicWebNodesTab, { global: { stubs: { NewPublicWebNode: true, NewPublicWeb: true } } })
    mounted.push(wrapper)
    await flushPromises()
    return wrapper
}

const panel = (wrapper, name) => wrapper.findAll('.v-expansion-panel').find((candidate) => candidate.text().includes(name))
const nodeSwitch = (panelWrapper) =>
    panelWrapper.findAllComponents({ name: 'VSwitch' }).find((component) => component.attributes('data-test') === 'node-enabled')

describe('PublicWebNodesTab node switch', () => {
    beforeEach(() => {
        vi.clearAllMocks()
        permissions.update = true
        vi.mocked(getAllPublicWebNodes).mockResolvedValue(nodesResponse())
    })
    afterEach(() => {
        while (mounted.length) mounted.pop().unmount()
    })

    it('shows a switched-off node as such, without a health colour', async () => {
        const wrapper = await mountTab()

        const off = panel(wrapper, 'Remote')
        expect(nodeSwitch(off).props('modelValue')).toBe(false)
        expect(off.find('[data-test="node-disabled"]').text()).toBe('Disabled')
        expect(off.find('[data-test="node-status"]').attributes('title')).toBe('Disabled')
        expect(off.find('[data-test="node-disabled-notice"]').text()).toContain('none of its webs are published')

        const on = panel(wrapper, 'Default Public Web')
        expect(nodeSwitch(on).props('modelValue')).toBe(true)
        expect(on.find('[data-test="node-disabled"]').exists()).toBe(false)
        expect(on.find('[data-test="node-disabled-notice"]').exists()).toBe(false)
    })

    it('switches a node off at once, saving the whole node, and re-reads only the nodes', async () => {
        const wrapper = await mountTab()
        const websLoaded = getPublicWebs.mock.calls.length
        vi.mocked(getAllPublicWebNodes).mockResolvedValue(nodesResponse({ 1: { enabled: false } }))

        nodeSwitch(panel(wrapper, 'Default Public Web')).vm.$emit('update:modelValue', false)
        await wrapper.vm.$nextTick()
        // Flipped before core answers.
        expect(panel(wrapper, 'Default Public Web').find('[data-test="node-disabled"]').exists()).toBe(true)
        await flushPromises()

        expect(updatePublicWebNode).toHaveBeenCalledWith(expect.objectContaining({ id: 1, name: 'Default Public Web', enabled: false }))
        expect(getAllPublicWebNodes).toHaveBeenCalledTimes(2)
        expect(getPublicWebs).toHaveBeenCalledTimes(websLoaded)
        expect(nodeSwitch(panel(wrapper, 'Default Public Web')).props('modelValue')).toBe(false)
    })

    it('puts the switch back and says so when core refuses', async () => {
        vi.spyOn(console, 'error').mockImplementation(() => undefined)
        const notifications = []
        const listener = (event) => notifications.push(event.detail)
        window.addEventListener('notification', listener)
        vi.mocked(updatePublicWebNode).mockRejectedValueOnce({ response: { status: 400 } })
        const wrapper = await mountTab()

        nodeSwitch(panel(wrapper, 'Remote')).vm.$emit('update:modelValue', true)
        await flushPromises()
        window.removeEventListener('notification', listener)

        expect(nodeSwitch(panel(wrapper, 'Remote')).props('modelValue')).toBe(false)
        expect(notifications).toEqual([{ type: 'error', loc: 'common.error_updating' }])
    })

    it('keeps the switch read-only without the update permission', async () => {
        permissions.update = false
        const wrapper = await mountTab()

        expect(nodeSwitch(panel(wrapper, 'Default Public Web')).props('disabled')).toBe(true)
    })
})

describe('NewPublicWebNode switch', () => {
    afterEach(() => {
        while (mounted.length) mounted.pop().unmount()
    })

    it('edits a node with its switch, and creates one switched on', async () => {
        const stubs = {
            VDialog: {
                props: ['modelValue'],
                template: '<div><slot name="activator" :props="{}" /><div v-if="modelValue"><slot /></div></div>'
            }
        }
        const wrapper = mountWithPlugins(NewPublicWebNode, { props: { editItem: { ...NODES[1] } }, global: { stubs } })
        mounted.push(wrapper)
        await flushPromises()

        const field = () =>
            wrapper.findAllComponents({ name: 'VSwitch' }).find((component) => component.attributes('data-test') === 'node-enabled-field')
        expect(field().props('modelValue')).toBe(false)

        await wrapper.setProps({ editItem: { id: 3, name: 'Older', description: '' } })
        expect(field().props('modelValue')).toBe(true)
    })
})
