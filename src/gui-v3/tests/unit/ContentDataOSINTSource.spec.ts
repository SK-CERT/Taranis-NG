import { describe, it, expect, vi } from 'vitest'
import { nextTick } from 'vue'
import { flushPromises } from '@vue/test-utils'
import { mountWithPlugins } from '../helpers/mount-helpers'
import ContentDataOSINTSource from '@/components/config/collectors/ContentDataOSINTSource.vue'

/**
 * The OSINT sources table: sources grouped under the node that collects them.
 *
 * The state badge and the countdown are the two things worth pinning. A badge has to say the one
 * thing an operator should act on, and the countdown has three states that are easy to get wrong:
 * a source with no schedule must not read "0m", one whose run is overdue must say so rather than
 * show a negative number, and a collecting source shows what it is doing instead of a time.
 */

vi.mock('@/composables/useAuth', () => ({
    useAuth: () => ({ checkPermission: () => true })
}))

const NODE = {
    id: 'node-1',
    name: 'Collectors node',
    description: 'the only node',
    status: 'green',
    collectors: [{ id: 'collector-1' }]
}

const source = (overrides = {}) => ({
    id: 'source-1',
    name: 'A source',
    collector_id: 'collector-1',
    collector: { id: 'collector-1', name: 'Web Collector' },
    enabled: true,
    collecting: false,
    status: 'green',
    ...overrides
})

const mountTable = async (items: object[], nodes: object[] = [NODE], selectionEnabled = false) => {
    const wrapper = mountWithPlugins(ContentDataOSINTSource, {
        props: { items, nodes, loading: false, selectionEnabled, selectedIds: [] }
    })
    // The node panels open a tick after mount, so that the closed frame exists for the expand
    // animation to run from. Their contents are not in the DOM until that has happened.
    await nextTick()
    return wrapper
}

type Table = Awaited<ReturnType<typeof mountTable>>

const badgeText = (wrapper: Table) => wrapper.findComponent({ name: 'VChip' }).text()
// Columns: enabled, collector icon, name, last attempted, last collected, next run, state.
// Asserted rather than optional-chained at every call site: a table that rendered fewer columns
// than expected should fail here, naming the problem, not further down as an undefined value.
const nextRunCell = (wrapper: Table) => wrapper.findAll('tbody td')[5]!

describe('ContentDataOSINTSource', () => {
    describe('opening animation', () => {
        /**
         * The panels have to be drawn closed once before they open, or Vuetify's expand transition
         * has no closed state to animate from and the list simply appears.
         *
         * The case that matters is the second visit onwards: the nodes are already in the store by
         * the time the tab mounts. An immediate watcher would open them during setup and the
         * animation would play on the first visit only - which is exactly how this was reported.
         */
        const mountWithNodesReady = () =>
            mountWithPlugins(ContentDataOSINTSource, {
                props: { items: [source()], nodes: [NODE], loading: false, selectionEnabled: false, selectedIds: [] }
            })

        // A closed panel renders no contents at all, so the table is the plainest evidence of
        // which state the panel was in on a given frame.
        it('draws the panels closed on the first frame even when the nodes are already loaded', () => {
            const wrapper = mountWithNodesReady()

            expect(wrapper.find('tbody').exists()).toBe(false)
        })

        it('opens them once mounting is done', async () => {
            const wrapper = mountWithNodesReady()

            await flushPromises()

            expect(wrapper.find('tbody').exists()).toBe(true)
            expect(wrapper.text()).toContain('A source')
        })
    })

    describe('column widths', () => {
        /**
         * Switching tabs re-renders the table with a different set of rows. With an automatic
         * layout the browser sizes each column to whatever those rows contain, so every switch
         * nudged the whole table sideways. A colgroup plus a fixed layout makes the widths a
         * property of the table rather than of its current contents.
         */
        it('sizes every column but the name, which absorbs the remaining width', async () => {
            const wrapper = await mountTable([source()])

            const cols = wrapper.findAll('colgroup col')
            const widths = cols.map((col) => col.attributes('style') ?? '')

            // One per column: enabled, icon, name, attempted, collected, next run, state, actions.
            expect(cols).toHaveLength(8)
            expect(widths.filter((width) => width === '')).toHaveLength(1)
            expect(widths[2]).toBe('')
        })

        it('adds a column for the checkbox when selection is on, so the widths still line up', async () => {
            const wrapper = await mountTable([source()], [NODE], true)

            expect(wrapper.findAll('colgroup col')).toHaveLength(9)
            expect(wrapper.findAll('thead th')).toHaveLength(9)
        })

        it('spans the empty-state row across every column', async () => {
            // A short colspan leaves the message boxed into one column and the rest of the row
            // empty, which reads as a broken table rather than an empty one.
            const wrapper = await mountTable([], [NODE])

            const cell = wrapper.find('tbody td[colspan]')
            expect(cell.attributes('colspan')).toBe(String(wrapper.findAll('thead th').length))
        })

        it('keeps a name too long for its column reachable through its title', async () => {
            const long = 'Broadcom Security Advisories - Brocade Storage Networking'
            const wrapper = await mountTable([source({ name: long })])

            expect(wrapper.find('td.source-name bdi').attributes('title')).toBe(long)
        })
    })

    describe('disabled sources', () => {
        it('dims the row of a source that is switched off', async () => {
            const wrapper = await mountTable([source({ enabled: false })])

            expect(wrapper.find('tbody tr').classes()).toContain('source-disabled')
        })

        it('leaves an enabled source at full contrast', async () => {
            const wrapper = await mountTable([source({ enabled: true })])

            expect(wrapper.find('tbody tr').classes()).not.toContain('source-disabled')
        })
    })

    describe('grouping', () => {
        it('lists a source under the node that collects it', async () => {
            const wrapper = await mountTable([source()])

            expect(wrapper.text()).toContain('Collectors node')
            expect(wrapper.text()).toContain('A source')
        })

        it('shows a node that collects nothing, because that is where a source is added to it', async () => {
            const empty = { id: 'node-2', name: 'Idle node', collectors: [{ id: 'collector-2' }] }

            const wrapper = await mountTable([source()], [NODE, empty])

            expect(wrapper.text()).toContain('Idle node')
            expect(wrapper.text()).toContain('No OSINT sources on this node')
        })

        it('leaves out a source whose collector belongs to no known node', async () => {
            const wrapper = await mountTable([source({ collector_id: 'collector-elsewhere' })])

            expect(wrapper.text()).not.toContain('A source')
        })
    })

    describe('group tabs', () => {
        const inGroup = (name: string, id: string) => ({ id, name })

        it('offers All plus each group the node actually has sources in', async () => {
            const wrapper = await mountTable([
                source({ id: 's1', osint_source_groups: [inGroup('Hardware', 'g1')] }),
                source({ id: 's2', osint_source_groups: [inGroup('News', 'g2')] })
            ])

            const labels = wrapper.findAllComponents({ name: 'VTab' }).map((tab) => tab.text())
            expect(labels[0]).toContain('All')
            expect(labels.join(' ')).toContain('Hardware')
            expect(labels.join(' ')).toContain('News')
        })

        it('does not offer a tab for a group with no sources on this node', async () => {
            const wrapper = await mountTable([source({ osint_source_groups: [inGroup('Hardware', 'g1')] })])

            expect(
                wrapper
                    .findAllComponents({ name: 'VTab' })
                    .map((t) => t.text())
                    .join(' ')
            ).not.toContain('News')
        })

        it('counts the sources behind each tab', async () => {
            const wrapper = await mountTable([
                source({ id: 's1', osint_source_groups: [inGroup('Hardware', 'g1')] }),
                source({ id: 's2', osint_source_groups: [inGroup('Hardware', 'g1')] })
            ])

            expect(wrapper.findAllComponents({ name: 'VTab' })[0]!.text()).toContain('(2)')
        })

        it('treats the default group as uncategorized rather than naming it', async () => {
            // The default group is where a source lands when nobody chose one for it.
            const wrapper = await mountTable([source({ osint_source_groups: [{ id: 'g0', name: 'Default', default: true }] })])

            const labels = wrapper
                .findAllComponents({ name: 'VTab' })
                .map((tab) => tab.text())
                .join(' ')
            expect(labels).toContain('Uncategorized')
            expect(labels).not.toContain('Default')
        })

        it('treats a source with no groups at all as uncategorized', async () => {
            const wrapper = await mountTable([source({ osint_source_groups: [] })])

            expect(
                wrapper
                    .findAllComponents({ name: 'VTab' })
                    .map((t) => t.text())
                    .join(' ')
            ).toContain('Uncategorized')
        })

        it('shows only the selected group once a tab is chosen', async () => {
            const wrapper = await mountTable([
                source({ id: 's1', name: 'Hardware source', osint_source_groups: [inGroup('Hardware', 'g1')] }),
                source({ id: 's2', name: 'News source', osint_source_groups: [inGroup('News', 'g2')] })
            ])

            await wrapper.findComponent({ name: 'VTabs' }).vm.$emit('update:modelValue', 'g1')

            expect(wrapper.text()).toContain('Hardware source')
            expect(wrapper.text()).not.toContain('News source')
        })

        it('filters each node independently', async () => {
            const second = { id: 'node-2', name: 'Second node', collectors: [{ id: 'collector-2' }] }
            const wrapper = await mountTable(
                [
                    source({ id: 's1', name: 'First source', osint_source_groups: [inGroup('Hardware', 'g1')] }),
                    source({
                        id: 's2',
                        name: 'Second source',
                        collector_id: 'collector-2',
                        osint_source_groups: [inGroup('News', 'g2')]
                    })
                ],
                [NODE, second]
            )

            // Narrowing the first node must leave the second showing everything it has.
            await wrapper.findAllComponents({ name: 'VTabs' })[0]!.vm.$emit('update:modelValue', 'g1')

            expect(wrapper.text()).toContain('First source')
            expect(wrapper.text()).toContain('Second source')
        })
    })

    describe('collector type', () => {
        it('shows an icon rather than repeating the collector name in every row', async () => {
            const wrapper = await mountTable([source({ collector: { id: 'collector-1', type: 'RSS_COLLECTOR', name: 'RSS Collector' } })])

            const icon = wrapper.find('tbody td.collector-icon-column .v-icon')
            expect(icon.exists()).toBe(true)
            // The name is still reachable, as the icon's tooltip.
            expect(icon.attributes('title')).toBe('RSS Collector')
        })

        it('falls back to a placeholder icon for an unknown collector type', async () => {
            const wrapper = await mountTable([source({ collector: { id: 'collector-1', type: 'FUTURE_COLLECTOR' } })])

            expect(wrapper.find('tbody td.collector-icon-column .v-icon').exists()).toBe(true)
        })
    })

    describe('collection history', () => {
        it('shows when the source was last attempted and last collected', async () => {
            const wrapper = await mountTable([source({ last_attempted: '04.09.2026 - 12:00:00', last_collected: '04.09.2026 - 11:00:00' })])

            const cells = wrapper.findAll('tbody td')
            expect(cells[3]!.text()).toBe('04.09.2026 - 12:00:00')
            expect(cells[4]!.text()).toBe('04.09.2026 - 11:00:00')
        })

        it('shows a dash for a source that has never run', async () => {
            const cells = (await mountTable([source()])).findAll('tbody td')

            expect(cells[3]!.text()).toBe('—')
            expect(cells[4]!.text()).toBe('—')
        })
    })

    describe('node actions', () => {
        it('offers editing and deleting the node itself', async () => {
            const wrapper = await mountTable([source()])

            const editNode = wrapper.findAll('button').find((b) => b.attributes('title') === 'Edit')
            await editNode?.trigger('click')

            expect(wrapper.emitted('edit-node')?.[0]?.[0]).toMatchObject({ id: 'node-1' })
        })
    })

    describe('state badge', () => {
        it('says pending when there is nothing to report', async () => {
            expect(badgeText(await mountTable([source()]))).toBe('Pending')
        })

        it('says collecting while a run is in progress', async () => {
            expect(badgeText(await mountTable([source({ collecting: true })]))).toBe('Collecting…')
        })

        it('says error when the last run failed', async () => {
            expect(badgeText(await mountTable([source({ last_error_message: 'it broke' })]))).toBe('Error')
        })

        it('says stale when the source has produced nothing recently', async () => {
            expect(badgeText(await mountTable([source({ status: 'orange' })]))).toBe('Stale')
        })

        it('prefers collecting over a previous error', async () => {
            // What it is doing now matters more than what went wrong last time.
            expect(badgeText(await mountTable([source({ collecting: true, last_error_message: 'it broke' })]))).toBe('Collecting…')
        })

        it('opens the full error, which is too long for a cell', async () => {
            const wrapper = await mountTable([
                source({ last_error_message: 'a very long stack trace', last_attempted: '04.09.2026 - 12:00:00' })
            ])

            await wrapper.findComponent({ name: 'VChip' }).trigger('click')

            const dialog = wrapper.findComponent({ name: 'VDialog' })
            expect(dialog.props('modelValue')).toBe(true)
            // Vuetify teleports the dialog to the body, so it is not inside the wrapper.
            expect(document.body.textContent).toContain('a very long stack trace')
            expect(document.body.textContent).toContain('A source')
        })

        it('does not open a dialog for a badge that carries no error', async () => {
            const wrapper = await mountTable([source()])

            await wrapper.findComponent({ name: 'VChip' }).trigger('click')

            expect(wrapper.findComponent({ name: 'VDialog' }).props('modelValue')).toBe(false)
        })
    })

    describe('next run', () => {
        it('counts down, and carries the exact time as a tooltip', async () => {
            // A few seconds of slack: the remaining time is floored, so exactly 90 minutes
            // would render as 1h 29m by the time the component computes it.
            const soon = new Date(Date.now() + 90 * 60 * 1000 + 30 * 1000).toISOString()

            const cell = nextRunCell(await mountTable([source({ next_run: soon })]))

            expect(cell.text()).toBe('1h 30m')
            expect(cell.find('span').attributes('title')).not.toBe('')
        })

        it('says due rather than showing a negative time', async () => {
            // The scheduler runs one job at a time, so a long run really does delay the queue.
            const past = new Date(Date.now() - 60 * 1000).toISOString()

            expect(nextRunCell(await mountTable([source({ next_run: past })])).text()).toBe('Due')
        })

        it('shows a dash when the source is not scheduled', async () => {
            expect(nextRunCell(await mountTable([source({ next_run: null })])).text()).toBe('—')
        })

        it('shows a dash for a switched-off source', async () => {
            const soon = new Date(Date.now() + 60 * 60 * 1000).toISOString()

            expect(nextRunCell(await mountTable([source({ enabled: false, next_run: soon })])).text()).toBe('—')
        })

        it('shows a dash while collecting, since the State column already says so', async () => {
            // Repeating "Collecting…" in two columns reads as two separate facts.
            const soon = new Date(Date.now() + 60 * 60 * 1000).toISOString()

            expect(nextRunCell(await mountTable([source({ collecting: true, next_run: soon })])).text()).toBe('—')
        })
    })

    describe('actions', () => {
        it('dims a switched-off source', async () => {
            const wrapper = await mountTable([source({ enabled: false })])

            expect(wrapper.find('tbody tr').classes()).toContain('source-disabled')
        })

        it('emits toggle-enabled from the switch', async () => {
            const wrapper = await mountTable([source()])

            await wrapper.findComponent({ name: 'VSwitch' }).vm.$emit('update:modelValue', false)

            expect(wrapper.emitted('toggle-enabled')?.[0]?.[1]).toBe(false)
        })

        it('cannot collect a source that is already collecting', async () => {
            const wrapper = await mountTable([source({ collecting: true })])

            const collect = wrapper.findAll('button').find((b) => b.attributes('title') === 'Collecting…')
            expect(collect?.attributes('disabled')).toBeDefined()
        })

        it('cannot collect a switched-off source', async () => {
            const wrapper = await mountTable([source({ enabled: false })])

            const collect = wrapper.findAll('button').find((b) => b.attributes('title') === 'Disabled')
            expect(collect?.attributes('disabled')).toBeDefined()
        })

        it('emits collect when the play button is pressed', async () => {
            const wrapper = await mountTable([source()])

            await wrapper
                .findAll('button')
                .find((b) => b.attributes('title') === 'Collect now')
                ?.trigger('click')

            expect(wrapper.emitted('collect')).toHaveLength(1)
        })
    })
})
