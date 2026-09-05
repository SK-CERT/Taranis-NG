import { describe, it, expect } from 'vitest'
import { defineComponent, h } from 'vue'
import { VExpansionPanel, VExpansionPanels } from 'vuetify/components'
import { mountWithPlugins } from '../helpers/mount-helpers'
import NodePanelTitle from '@/components/common/nodes/NodePanelTitle.vue'

/**
 * The bar every node announces itself with, shared by public webs and OSINT sources.
 *
 * The health dot is the part worth pinning: it is the only signal that a node has stopped
 * answering, and "never connected" has to be distinguishable from "was fine, now late".
 */

const node = (overrides = {}) => ({
    id: 'node-1',
    name: 'A node',
    description: 'does things',
    status: 'green',
    last_seen: '04.09.2026 - 14:00:00',
    ...overrides
})

// VExpansionPanelTitle injects its open state from the panel around it, so it can only be
// mounted where the tabs actually put it.
type TitleProps = InstanceType<typeof NodePanelTitle>['$props']

const inPanel = (props: TitleProps, slots: Record<string, () => unknown> = {}) =>
    defineComponent({
        render: () => h(VExpansionPanels, () => h(VExpansionPanel, () => h(NodePanelTitle, props, slots)))
    })

const mountTitle = (props = {}) => mountWithPlugins(inPanel({ node: node(), count: 3, canUpdate: true, canDelete: true, ...props }))

const dot = (wrapper: ReturnType<typeof mountTitle>) => wrapper.findComponent({ name: 'VIcon' })
const title = (wrapper: ReturnType<typeof mountTitle>) => wrapper.findComponent(NodePanelTitle)

describe('NodePanelTitle', () => {
    it('names the node and counts what it holds', () => {
        const wrapper = mountTitle()

        expect(wrapper.text()).toContain('A node')
        expect(wrapper.text()).toContain('(3)')
        expect(wrapper.text()).toContain('does things')
    })

    it.each([
        ['green', 'success', 'mdi-circle'],
        ['orange', 'warning', 'mdi-circle-outline'],
        ['red', 'error', 'mdi-circle-outline']
    ])('shows %s health as a %s dot', (status, colour, icon) => {
        const wrapper = mountTitle({ node: node({ status }) })

        expect(dot(wrapper).props('color')).toBe(colour)
        expect(wrapper.html()).toContain(icon)
    })

    it('says a node has never connected rather than reporting a last seen time it does not have', () => {
        const wrapper = mountTitle({ node: node({ status: 'red', last_seen: undefined }) })

        expect(dot(wrapper).attributes('title')).toBe('Never connected')
    })

    it('reports when a reachable node was last seen', () => {
        const wrapper = mountTitle()

        const title = dot(wrapper).attributes('title')
        expect(title).toContain('Reachable')
        expect(title).toContain('04.09.2026 - 14:00:00')
    })

    it('emits edit and delete for the node it is showing', async () => {
        const wrapper = mountTitle()
        const buttons = wrapper.findAllComponents({ name: 'ActionButton' })

        // Asserted: two action buttons are exactly what this case is about, so a missing one
        // should fail here rather than silently skip the click.
        await buttons[0]!.trigger('click')
        await buttons[1]!.trigger('click')

        expect(title(wrapper).emitted('edit')?.[0]?.[0]).toMatchObject({ id: 'node-1' })
        expect(title(wrapper).emitted('delete')?.[0]?.[0]).toMatchObject({ id: 'node-1' })
    })

    it('hides the actions a viewer has no permission for', () => {
        const wrapper = mountTitle({ canUpdate: false, canDelete: false })

        expect(wrapper.findAllComponents({ name: 'ActionButton' })).toHaveLength(0)
    })

    it('renders whatever the tab adds to the node', () => {
        const wrapper = mountWithPlugins(inPanel({ node: node(), count: 0 }, { add: () => h('button', { class: 'add-thing' }, 'Add') }))

        expect(wrapper.find('button.add-thing').exists()).toBe(true)
    })

    it('keeps a click on what the tab added from collapsing the panel', async () => {
        // The title bar is itself a button; without the guard, adding a child would fold away the
        // node it belongs to.
        const wrapper = mountWithPlugins(inPanel({ node: node(), count: 0 }, { add: () => h('button', { class: 'add-thing' }, 'Add') }))
        const panel = wrapper.findComponent(VExpansionPanel)

        await wrapper.find('button.add-thing').trigger('click')

        expect(panel.find('.v-expansion-panel-title--active').exists()).toBe(false)
    })
})
