<template>
    <v-container
        fluid
        class="pa-0"
    >
        <v-expansion-panels
            ref="panelsRoot"
            v-model="openPanels"
            multiple
            class="mt-2"
        >
            <v-expansion-panel
                v-for="node in visibleNodes"
                :key="node.id"
                :value="node.id"
            >
                <NodePanelTitle
                    :node="node"
                    :count="(sourcesByNode[node.id] || []).length"
                    :can-update="canUpdateNode"
                    :can-delete="canDeleteNode"
                    @edit="emit('edit-node', node)"
                    @delete="emit('delete-node', node)"
                >
                    <template #add>
                        <slot
                            name="add-source"
                            :node="node"
                        />
                    </template>
                </NodePanelTitle>

                <v-expansion-panel-text>
                    <v-tabs
                        :model-value="activeGroup[node.id] ?? ALL_GROUPS"
                        density="compact"
                        color="primary"
                        class="mb-2 group-tabs"
                        @update:model-value="(value) => selectGroup(node.id, String(value))"
                    >
                        <v-tab
                            v-for="tab in groupTabs(node)"
                            :key="tab.value"
                            :value="tab.value"
                        >
                            {{ tab.label }}
                            <span class="text-medium-emphasis ms-1">({{ tab.count }})</span>
                        </v-tab>
                    </v-tabs>

                    <v-table
                        density="compact"
                        class="osint-table"
                    >
                        <!-- Fixed widths, so the columns are sized by these numbers rather than by
                             whichever names and dates the selected tab happens to contain. Without
                             it every tab switch re-measures the content and the whole table shifts
                             sideways under the pointer. Name is left unsized and takes the rest. -->
                        <colgroup>
                            <col
                                v-if="selectionEnabled"
                                style="width: 48px"
                            />
                            <col style="width: 90px" />
                            <col style="width: 40px" />
                            <col />
                            <col style="width: 190px" />
                            <col style="width: 190px" />
                            <col style="width: 100px" />
                            <col style="width: 110px" />
                            <col style="width: 170px" />
                        </colgroup>
                        <thead>
                            <tr>
                                <th v-if="selectionEnabled" />
                                <th>{{ t('collectors.sources.enabled') }}</th>
                                <th class="collector-icon-column" />
                                <th>{{ t('collectors.sources.name') }}</th>
                                <th>{{ t('card_item.last_attempted') }}</th>
                                <th>{{ t('card_item.last_collected') }}</th>
                                <th>{{ t('card_item.next_run') }}</th>
                                <th>{{ t('card_item.state') }}</th>
                                <th class="text-end">{{ t('common.actions') }}</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr
                                v-for="source in visibleSources(node)"
                                :key="source.id"
                                :class="{ 'source-disabled': source.enabled === false }"
                            >
                                <td v-if="selectionEnabled">
                                    <v-checkbox
                                        :model-value="selectedIds.includes(source.id)"
                                        density="compact"
                                        hide-details
                                        @update:model-value="(value) => emit('selection-change', source.id, value === true)"
                                    />
                                </td>
                                <td>
                                    <v-switch
                                        v-if="canUpdate"
                                        :model-value="source.enabled !== false"
                                        color="primary"
                                        density="compact"
                                        hide-details
                                        :disabled="togglingId === source.id"
                                        :loading="togglingId === source.id"
                                        :title="source.enabled === false ? t('collectors.sources.disabled') : t('collectors.sources.enabled')"
                                        @update:model-value="(value) => emit('toggle-enabled', source, value !== false)"
                                    />
                                </td>
                                <td class="collector-icon-column">
                                    <v-icon
                                        :icon="collectorIcon(source)"
                                        size="small"
                                        class="text-medium-emphasis"
                                        :title="collectorName(source)"
                                    />
                                </td>
                                <td class="source-name">
                                    <bdi
                                        dir="auto"
                                        :title="source.name"
                                        >{{ source.name }}</bdi
                                    >
                                </td>
                                <td class="text-medium-emphasis text-no-wrap">
                                    <bdi dir="ltr">{{ source.last_attempted || '—' }}</bdi>
                                </td>
                                <td class="text-medium-emphasis text-no-wrap">
                                    <bdi dir="ltr">{{ source.last_collected || '—' }}</bdi>
                                </td>
                                <td>
                                    <span :title="nextRunExact(source)">{{ nextRunLabel(source) }}</span>
                                </td>
                                <td>
                                    <v-chip
                                        :color="stateOf(source).color"
                                        size="small"
                                        variant="flat"
                                        :class="{ 'cursor-pointer': stateOf(source).key === 'error' }"
                                        @click="stateOf(source).key === 'error' ? showError(source) : undefined"
                                    >
                                        {{ t(stateOf(source).label) }}
                                    </v-chip>
                                </td>
                                <td class="text-end text-no-wrap">
                                    <ActionButton
                                        v-if="canUpdate"
                                        action="collect"
                                        :disabled="source.collecting === true || source.enabled === false"
                                        :loading="collectingId === source.id"
                                        :title="collectTitle(source)"
                                        @click="emit('collect', source)"
                                    />
                                    <ActionButton
                                        v-if="canUpdate"
                                        action="edit"
                                        @click="emit('edit', source)"
                                    />
                                    <ActionButton
                                        v-if="canDelete"
                                        action="delete"
                                        @click="askDelete(source)"
                                    />
                                </td>
                            </tr>
                            <tr v-if="!visibleSources(node).length">
                                <td
                                    :colspan="selectionEnabled ? 9 : 8"
                                    class="text-medium-emphasis"
                                >
                                    {{ t('collectors.sources.none') }}
                                </td>
                            </tr>
                        </tbody>
                    </v-table>
                </v-expansion-panel-text>
            </v-expansion-panel>
        </v-expansion-panels>

        <v-row
            v-if="items.length === 0 && !loading"
            justify="center"
            class="mt-8"
        >
            <v-col class="text-center">
                <v-icon
                    size="64"
                    color="grey-lighten-1"
                >
                    mdi-database-off
                </v-icon>
                <p class="text-h6 text-grey-lighten-1 mt-4">{{ t('common.no_data') }}</p>
            </v-col>
        </v-row>

        <v-row
            v-if="loading"
            justify="center"
            class="mt-4"
        >
            <v-progress-circular
                indeterminate
                color="primary"
            />
        </v-row>

        <!-- An error is often a stack trace or a long selector: far too much for a table cell. -->
        <v-dialog
            v-model="errorDialog"
            max-width="820"
            scrollable
        >
            <v-card>
                <v-card-title>
                    <bdi dir="auto">{{ errorSource?.name }}</bdi>
                </v-card-title>
                <v-card-subtitle v-if="errorSource?.last_attempted">
                    {{ t('collectors.sources.last_attempt') }}: {{ errorSource?.last_attempted }}
                </v-card-subtitle>
                <v-card-text>
                    <pre class="error-detail text-error">{{ errorSource?.last_error_message }}</pre>
                </v-card-text>
                <v-card-actions>
                    <v-spacer />
                    <v-btn @click="errorDialog = false">{{ t('common.close') }}</v-btn>
                </v-card-actions>
            </v-card>
        </v-dialog>

        <ConfirmationDialog
            v-model="deleteDialog"
            :message="pendingDelete?.name ?? ''"
            @confirm="confirmDelete"
        />
    </v-container>
</template>

<script setup lang="ts">
    import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
    import { useI18n } from 'vue-i18n'
    import { useAuth } from '@/composables/useAuth'
    import { COLLECTOR_TYPE_FALLBACK_ICON, COLLECTOR_TYPE_ICONS } from '@/config/ui-constants'
    import ActionButton from '@/components/common/buttons/ActionButton.vue'
    import NodePanelTitle from '@/components/common/nodes/NodePanelTitle.vue'
    import type { CollectorsNodeItem, OSINTSourceItem } from '@/types/collectors'
    import ConfirmationDialog from '@/components/common/dialogs/ConfirmationDialog.vue'

    const props = withDefaults(
        defineProps<{
            items: OSINTSourceItem[]
            nodes: CollectorsNodeItem[]
            loading: boolean
            selectionEnabled: boolean
            selectedIds: Array<string | number>
            /** The source whose collect request is still in flight, if any. */
            collectingId?: string | number | null
            /** The source whose enable/disable request is still in flight, if any. */
            togglingId?: string | number | null
        }>(),
        { collectingId: null, togglingId: null }
    )

    const emit = defineEmits<{
        (event: 'delete', item: OSINTSourceItem): void
        (event: 'edit', item: OSINTSourceItem): void
        (event: 'collect', item: OSINTSourceItem): void
        (event: 'toggle-enabled', item: OSINTSourceItem, enabled: boolean): void
        (event: 'selection-change', id: string | number, selected: boolean): void
        (event: 'edit-node', node: CollectorsNodeItem): void
        (event: 'delete-node', node: CollectorsNodeItem): void
    }>()

    const { t } = useI18n()
    const { checkPermission } = useAuth()

    const canUpdate = computed(() => checkPermission('CONFIG_OSINT_SOURCE_UPDATE'))
    const canDelete = computed(() => checkPermission('CONFIG_OSINT_SOURCE_DELETE'))
    const canUpdateNode = computed(() => checkPermission('CONFIG_COLLECTORS_NODE_UPDATE'))
    const canDeleteNode = computed(() => checkPermission('CONFIG_COLLECTORS_NODE_DELETE'))

    // A source names its collector, and a node lists the collectors it runs, so the node is one
    // hop away. Nothing on the source itself names the node.
    const nodeIdByCollector = computed(() => {
        const map: Record<string, string> = {}
        for (const node of props.nodes) {
            for (const collector of node.collectors ?? []) {
                if (collector.id) map[collector.id] = String(node.id)
            }
        }
        return map
    })

    const sourcesByNode = computed(() => {
        const grouped: Record<string, OSINTSourceItem[]> = {}
        for (const source of props.items) {
            const nodeId = source.collector_id ? nodeIdByCollector.value[source.collector_id] : undefined
            if (!nodeId) continue
            if (!grouped[nodeId]) grouped[nodeId] = []
            grouped[nodeId].push(source)
        }
        return grouped
    })

    // Every node is listed, including one that collects nothing yet: its panel is where a source
    // is added to it, so hiding an empty node would make it unusable.
    const visibleNodes = computed(() => props.nodes)

    // Panels start open, and a newly appearing node opens too, so nothing is hidden by default.
    //
    // Every path to "open" has to happen after the render that first drew the panel closed, or
    // there is no closed state for Vuetify's expand transition to animate from. That rules out an
    // immediate watcher: `immediate` runs during setup whatever `flush` says, and on every visit
    // after the first the nodes are already in the store, so the panels would be open before
    // their first frame and the list would snap into place instead of opening.
    //
    // Hence two triggers rather than one. The mounted hook covers arriving with the nodes already
    // loaded, the watcher covers them arriving afterwards - a cold first visit, or a node added
    // later - and on any given visit only one of them has anything to do.
    const openPanels = ref<Array<string | number>>([])

    const openAllPanels = (): void => {
        openPanels.value = visibleNodes.value.map((node) => node.id)
    }

    watch(visibleNodes, openAllPanels, { flush: 'post' })
    onMounted(() => nextTick(openAllPanels))

    // Three things stay in view while a node's sources scroll: its title, its group tabs, and
    // the table header. Each has to know the height of the ones above it, and those are measured
    // rather than assumed - Vuetify's 64px for an open title is only a min-height, and a long node
    // name or a narrow window makes any of them taller.
    const panelsRoot = ref<{ $el?: HTMLElement } | null>(null)
    let stickyObserver: InstanceType<typeof window.ResizeObserver> | null = null

    const measureSticky = (): void => {
        const root = panelsRoot.value?.$el
        if (!root) return
        const heightOf = (selector: string, fallback: number): number => {
            const element = root.querySelector(selector) as HTMLElement | null
            return element ? Math.round(element.getBoundingClientRect().height) : fallback
        }
        const title = heightOf('.v-expansion-panel-title', 64)
        const tabs = heightOf('.group-tabs', 48)
        root.style.setProperty('--osint-title-height', `${title}px`)
        root.style.setProperty('--osint-tabs-height', `${tabs}px`)
    }

    const ALL_GROUPS = 'all'
    const UNCATEGORIZED = 'uncategorized'

    /** Which tab each node is showing. Per node, so opening one does not re-filter the others. */
    const activeGroup = ref<Record<string, string>>({})

    const selectGroup = (nodeId: string | number, value: string): void => {
        activeGroup.value = { ...activeGroup.value, [nodeId]: value }
    }

    // The default group is the "no group chosen" bucket rather than a group an operator picked,
    // so it is reported as uncategorized instead of by name.
    const realGroups = (source: OSINTSourceItem): NonNullable<OSINTSourceItem['osint_source_groups']> =>
        (source.osint_source_groups ?? []).filter((group) => group.default !== true)

    /**
     * The tabs for one node: everything it collects, then each group it actually has sources in,
     * then whatever is in no group at all.
     *
     * Only groups present on this node get a tab. Listing every configured group would put a row
     * of mostly empty tabs above every node.
     */
    const groupTabs = (node: CollectorsNodeItem): Array<{ value: string; label: string; count: number }> => {
        const sources = sourcesByNode.value[node.id] ?? []
        const counts = new Map<string, { label: string; count: number }>()
        let uncategorized = 0

        for (const source of sources) {
            const groups = realGroups(source)
            if (groups.length === 0) {
                uncategorized += 1
                continue
            }
            for (const group of groups) {
                const id = String(group.id ?? '')
                const entry = counts.get(id) ?? { label: group.name ?? '', count: 0 }
                entry.count += 1
                counts.set(id, entry)
            }
        }

        const tabs = [{ value: ALL_GROUPS, label: t('collectors.sources.group_all'), count: sources.length }]
        for (const [id, entry] of [...counts].sort((a, b) => a[1].label.localeCompare(b[1].label))) {
            tabs.push({ value: id, label: entry.label, count: entry.count })
        }
        if (uncategorized > 0) {
            tabs.push({ value: UNCATEGORIZED, label: t('collectors.sources.group_uncategorized'), count: uncategorized })
        }
        return tabs
    }

    const visibleSources = (node: CollectorsNodeItem): OSINTSourceItem[] => {
        const sources = sourcesByNode.value[node.id] ?? []
        const selected = activeGroup.value[node.id] ?? ALL_GROUPS
        if (selected === ALL_GROUPS) return sources
        if (selected === UNCATEGORIZED) return sources.filter((source) => realGroups(source).length === 0)
        return sources.filter((source) => realGroups(source).some((group) => String(group.id ?? '') === selected))
    }

    const collectorName = (source: OSINTSourceItem): string => source.collector?.name ?? source.collector?.type ?? ''

    const collectorIcon = (source: OSINTSourceItem): string =>
        COLLECTOR_TYPE_ICONS[source.collector?.type ?? ''] ?? COLLECTOR_TYPE_FALLBACK_ICON

    /**
     * What the source is doing, as one badge.
     *
     * Collecting wins over everything: it is happening now. An error comes next, because it is the
     * thing an operator has to act on. Stale means the source has produced nothing within its own
     * warning interval, which core works out. Otherwise it is simply waiting for its turn.
     */
    const stateOf = (source: OSINTSourceItem): { key: string; color: string; label: string } => {
        if (source.collecting === true) {
            return { key: 'collecting', color: 'success', label: 'collectors.sources.collecting' }
        }
        if (source.last_error_message) {
            return { key: 'error', color: 'error', label: 'collectors.sources.state_error' }
        }
        if (source.status === 'orange') {
            return { key: 'stale', color: 'warning', label: 'collectors.sources.state_stale' }
        }
        return { key: 'pending', color: 'info', label: 'collectors.sources.state_pending' }
    }

    const collectTitle = (source: OSINTSourceItem): string => {
        if (source.collecting === true) return t('collectors.sources.collecting')
        if (source.enabled === false) return t('collectors.sources.disabled')
        return t('common.collect_now')
    }

    // One clock for the whole table: a timer per row would be forty timers redrawing the same
    // second.
    const now = ref(Date.now())
    let tick: number | null = null

    const nextRunLabel = (source: OSINTSourceItem): string => {
        // While a run is under way the scheduled time is meaningless - the State column is where
        // "collecting" is said, and saying it twice in one row reads as two separate facts.
        if (source.collecting === true) return '—'
        if (source.enabled === false || !source.next_run) return '—'
        const remaining = new Date(source.next_run).getTime() - now.value
        if (Number.isNaN(remaining)) return '—'
        // The scheduler runs one job at a time, so a long run pushes everything behind it past its
        // due time. Saying so is more use than showing a negative number.
        if (remaining <= 0) return t('collectors.sources.due')
        const totalMinutes = Math.floor(remaining / 60000)
        const days = Math.floor(totalMinutes / 1440)
        const hours = Math.floor((totalMinutes % 1440) / 60)
        const minutes = totalMinutes % 60
        if (days > 0) return `${days}d ${hours}h`
        if (hours > 0) return `${hours}h ${minutes}m`
        return `${minutes}m`
    }

    /** The exact moment, for the native tooltip behind the countdown. */
    const nextRunExact = (source: OSINTSourceItem): string => {
        if (!source.next_run || source.enabled === false || source.collecting === true) return ''
        const when = new Date(source.next_run)
        return Number.isNaN(when.getTime()) ? '' : when.toLocaleString()
    }

    const errorDialog = ref(false)
    const errorSource = ref<OSINTSourceItem | null>(null)

    const showError = (source: OSINTSourceItem): void => {
        errorSource.value = source
        errorDialog.value = true
    }

    const deleteDialog = ref(false)
    const pendingDelete = ref<OSINTSourceItem | null>(null)

    const askDelete = (source: OSINTSourceItem): void => {
        pendingDelete.value = source
        deleteDialog.value = true
    }

    const confirmDelete = (): void => {
        if (pendingDelete.value) emit('delete', pendingDelete.value)
        deleteDialog.value = false
        pendingDelete.value = null
    }

    onMounted(() => {
        tick = window.setInterval(() => (now.value = Date.now()), 30000)
        measureSticky()
        if (typeof window.ResizeObserver !== 'undefined') {
            stickyObserver = new window.ResizeObserver(measureSticky)
            for (const selector of ['.v-expansion-panel-title', '.group-tabs']) {
                const element = panelsRoot.value?.$el?.querySelector(selector)
                if (element) stickyObserver.observe(element)
            }
        }
    })

    // A node appearing or disappearing changes which elements are first, so re-measure.
    watch(visibleNodes, () => nextTick(measureSticky))

    onUnmounted(() => {
        if (tick !== null) window.clearInterval(tick)
        stickyObserver?.disconnect()
    })
</script>

<style scoped>
    /* Each node's title stays at the top of the scroll area while its own sources scroll past,
       and is pushed out of the way by the next node's title. The panels have no overflow of their
       own, so the scroll area the view provides is what these stick against. */
    :deep(.v-expansion-panel-title) {
        position: sticky;
        top: 0;
        z-index: 3;
        background: rgb(var(--v-theme-surface));
    }

    /* The group tabs hold their place under the node title they belong to, so switching group
       stays reachable however far down the list you are. The panel text has 8px of top padding;
       the negative margin plus matching padding lets the strip's background cover it, otherwise
       rows would show through the gap above the tabs. */
    .group-tabs {
        position: sticky;
        top: var(--osint-title-height, 64px);
        z-index: 2;
        background: rgb(var(--v-theme-surface));
        /* Extends the surface a few pixels above the strip, so sub-pixel scroll positions cannot
           flash a seam of moving rows between it and the node title. It must be a shadow rather
           than padding: the strip is a fixed-height border box with overflow hidden, so padding
           pushes the tab down and clips its underline slider off the bottom edge. */
        box-shadow: 0 -8px 0 rgb(var(--v-theme-surface));
    }

    /* A switched-off source is dimmed the way a read news item is, and comes back on hover. */
    .osint-table :deep(table) {
        table-layout: fixed;
        /* Below this the name column has no room left, so the table scrolls sideways inside
           .osint-scroll instead of crushing every column. */
        min-width: 1100px;
    }

    /* A name too long for its column ends in an ellipsis; the full one is in its title. */
    .source-name {
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }

    .source-disabled {
        opacity: 0.55;
    }

    .source-disabled:hover {
        opacity: 1;
    }

    /* Vuetify gives this wrapper `overflow: auto`, which makes it the scrollport the sticky
       header below obeys - and it never scrolls, so the header could not stick to the page and
       its `top` offset pushed it down among the rows instead. Making it visible hands the header
       to .osint-scroll, the element that actually scrolls. Nothing is lost: a table too wide to
       fit now scrolls sideways in .osint-scroll, which is `auto` on both axes. */
    :deep(.v-table__wrapper) {
        overflow: visible;
    }

    /* The header sits under the tabs, which sit under the node title. Its z-index is the lowest
       of the three: it comes last in the DOM, so without that it would paint over the tabs. */
    :deep(.v-table thead th) {
        position: sticky;
        top: calc(var(--osint-title-height, 64px) + var(--osint-tabs-height, 48px));
        z-index: 1;
        background: rgb(var(--v-theme-surface));
    }

    .cursor-pointer {
        cursor: pointer;
    }

    /* Narrow and padded down, so the icon sits against the name it belongs to and every name in
       the table still starts at the same x. */
    .collector-icon-column {
        width: 1px;
        padding-inline-end: 0 !important;
    }

    .error-detail {
        white-space: pre-wrap;
        word-break: break-word;
        font-size: 0.8125rem;
        margin: 0;
    }
</style>
