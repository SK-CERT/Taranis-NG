<template>
    <v-container
        fluid
        class="pa-0"
    >
        <ToolbarFilter
            :total-count="configStore.publicWebNodes.total_count"
            total-count-title="public_web.nodes.total_count"
            @update-filter="handleFilterUpdate"
        >
            <template #addbutton>
                <NewPublicWebNode
                    :edit-item="nodeEditItem"
                    @saved="handleNodeSaved"
                />
            </template>
        </ToolbarFilter>

        <v-expansion-panels
            v-model="openPanels"
            multiple
            class="mt-2"
        >
            <v-expansion-panel
                v-for="node in nodes"
                :key="node.id"
                :value="node.id"
            >
                <NodePanelTitle
                    :node="node"
                    :count="(websByNode[node.id] || []).length"
                    :can-update="canUpdate"
                    :can-delete="canDelete"
                    @edit="editNode(node)"
                    @delete="askDeleteNode(node)"
                >
                    <template #add>
                        <NewPublicWeb
                            :node-id="node.id"
                            :edit-item="webEditItems[node.id] || null"
                            @saved="handleWebSaved(node.id)"
                        />
                    </template>
                </NodePanelTitle>

                <v-expansion-panel-text>
                    <v-table density="compact">
                        <thead>
                            <tr>
                                <th>{{ t('public_web.webs.enabled') }}</th>
                                <th>{{ t('public_web.webs.name') }}</th>
                                <th>{{ t('public_web.webs.hostname') }}</th>
                                <th>{{ t('public_web.webs.languages') }}</th>
                                <th class="text-end">{{ t('public_web.webs.actions') }}</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr
                                v-for="web in websByNode[node.id] || []"
                                :key="web.id"
                                :class="{ 'text-medium-emphasis': web.enabled === false }"
                            >
                                <td>
                                    <v-switch
                                        :model-value="web.enabled !== false"
                                        color="primary"
                                        density="compact"
                                        hide-details
                                        :disabled="!canUpdate || togglingWeb === web.id"
                                        :loading="togglingWeb === web.id"
                                        @update:model-value="(val) => toggleWebEnabled(node.id, web, val)"
                                    />
                                </td>
                                <td>{{ web.name }}</td>
                                <td>{{ web.hostname }}</td>
                                <td>{{ (web.config && web.config.languages ? web.config.languages : []).join(', ') }}</td>
                                <td class="text-end">
                                    <v-btn
                                        v-if="canUpdate"
                                        icon="mdi-pencil"
                                        size="x-small"
                                        variant="text"
                                        @click="editWeb(node.id, web)"
                                    />
                                    <v-btn
                                        v-if="canDelete"
                                        icon="mdi-delete"
                                        size="x-small"
                                        variant="text"
                                        color="error"
                                        @click="askDeleteWeb(node.id, web)"
                                    />
                                </td>
                            </tr>
                            <tr v-if="!(websByNode[node.id] || []).length">
                                <td
                                    colspan="5"
                                    class="text-medium-emphasis"
                                >
                                    {{ t('public_web.webs.none') }}
                                </td>
                            </tr>
                        </tbody>
                    </v-table>
                </v-expansion-panel-text>
            </v-expansion-panel>
        </v-expansion-panels>

        <!-- Delete confirmation -->
        <v-dialog
            v-model="confirmDelete.show"
            max-width="420"
        >
            <v-card>
                <v-card-title>{{ t('public_web.confirm_delete_title') }}</v-card-title>
                <v-card-text>{{ confirmDelete.message }}</v-card-text>
                <v-card-actions>
                    <v-spacer />
                    <v-btn
                        variant="text"
                        @click="confirmDelete.show = false"
                    >
                        {{ t('common.cancel') }}
                    </v-btn>
                    <v-btn
                        color="error"
                        variant="tonal"
                        @click="performDelete"
                    >
                        {{ t('common.delete') }}
                    </v-btn>
                </v-card-actions>
            </v-card>
        </v-dialog>
    </v-container>
</template>

<script setup lang="ts">
    import { ref, computed, onMounted, onUnmounted } from 'vue'
    import { useI18n } from 'vue-i18n'
    import { useConfigStore } from '@/stores/config'
    import { usePublishStore } from '@/stores/publish'
    import { useAuth } from '@/composables/useAuth'
    import { getPublicWebs, deletePublicWebNode, deletePublicWeb, updatePublicWeb } from '@/api/config'
    import ToolbarFilter from '@/components/common/ToolbarFilter.vue'
    import NewPublicWebNode from '@/components/config/public-web/NewPublicWebNode.vue'
    import NodePanelTitle from '@/components/common/nodes/NodePanelTitle.vue'
    import { useOptimisticToggle } from '@/composables/useOptimisticToggle'
    import NewPublicWeb from '@/components/config/public-web/NewPublicWeb.vue'

    type NodeItem = {
        id: number
        name: string
        description?: string
        status?: string
        last_seen?: string
        [key: string]: unknown
    }
    type WebItem = {
        id: number
        name: string
        hostname?: string
        enabled?: boolean
        config?: { languages?: string[] }
        [key: string]: unknown
    }

    const { t } = useI18n()
    const configStore = useConfigStore()
    const publishStore = usePublishStore()
    const { checkPermission } = useAuth()

    const filter = ref<{ search: string }>({ search: '' })
    const openPanels = ref<number[]>([])
    const websByNode = ref<Record<number, WebItem[]>>({})
    const nodeEditItem = ref<NodeItem | null>(null)
    const webEditItems = ref<Record<number, any>>({})

    // The busy row while a switch is saving; the composable owns it.
    const { busyId: togglingWeb, toggle } = useOptimisticToggle()

    const canUpdate = computed(() => checkPermission('CONFIG_PUBLIC_WEB_NODE_UPDATE'))
    const canDelete = computed(() => checkPermission('CONFIG_PUBLIC_WEB_NODE_DELETE'))

    const nodes = computed<NodeItem[]>(() => (configStore.publicWebNodes.items as NodeItem[]) || [])

    async function loadNodes(): Promise<void> {
        try {
            await configStore.loadPublicWebNodes(filter.value)
            for (const node of nodes.value) {
                await loadWebs(node.id)
            }
            // Expand all node panels so their webs (and the Add web button) are
            // visible without an extra click.
            openPanels.value = nodes.value.map((node) => node.id)
        } catch (error) {
            console.error('Error loading public-web nodes:', error)
        }
    }

    async function loadWebs(nodeId: number): Promise<void> {
        try {
            const response = (await getPublicWebs(nodeId)) as { data?: { items?: WebItem[] } }
            websByNode.value[nodeId] = response.data?.items || []
        } catch (error) {
            console.error('Error loading webs for node', nodeId, error)
            websByNode.value[nodeId] = []
        }
    }

    function handleFilterUpdate(newFilter: { search: string }): void {
        filter.value = newFilter
        loadNodes()
    }

    function editNode(node: NodeItem): void {
        nodeEditItem.value = { ...node }
    }

    function handleNodeSaved(): void {
        nodeEditItem.value = null
        loadNodes()
    }

    function editWeb(nodeId: number, web: WebItem): void {
        webEditItems.value[nodeId] = { ...web }
    }

    // Quick enable/disable from the list. Persists via the normal update (which
    // also pushes a cache reset to the node). The switch is moved locally first
    // so it follows the click immediately, and moved back if the save fails.

    async function toggleWebEnabled(nodeId: number, web: WebItem, value: boolean | null): Promise<void> {
        await toggle(web, value !== false, {
            save: (enabled) => updatePublicWeb(nodeId, { ...web, enabled }),
            reload: () => loadWebs(nodeId),
            onError: (error) => console.error('Error toggling web:', error)
        })
    }

    function handleWebSaved(nodeId: number): void {
        webEditItems.value[nodeId] = null
        loadWebs(nodeId)
    }

    // -- delete confirmation --------------------------------------------------

    const confirmDelete = ref<{
        show: boolean
        message: string
        kind: 'node' | 'web' | null
        node?: NodeItem
        web?: WebItem
        nodeId?: number
    }>({ show: false, message: '', kind: null })

    function askDeleteNode(node: NodeItem): void {
        confirmDelete.value = {
            show: true,
            kind: 'node',
            node,
            message: t('public_web.confirm_delete_node', { name: node.name })
        }
    }

    function askDeleteWeb(nodeId: number, web: WebItem): void {
        confirmDelete.value = {
            show: true,
            kind: 'web',
            nodeId,
            web,
            message: t('public_web.confirm_delete_web', { name: web.name })
        }
    }

    async function performDelete(): Promise<void> {
        const target = confirmDelete.value
        try {
            if (target.kind === 'node' && target.node) {
                await deletePublicWebNode(target.node)
                await loadNodes()
            } else if (target.kind === 'web' && target.web && target.nodeId != null) {
                await deletePublicWeb(target.nodeId, target.web)
                await loadWebs(target.nodeId)
            }
            // Deleting a web (or a whole node with its webs) must invalidate the
            // Publish view's cached targeting options: a stale id saved into a
            // product is silently dropped by the backend and the product turns
            // global (visible on every web).
            publishStore.invalidatePublicWebOptions()
        } catch (error) {
            console.error('Error deleting:', error)
        } finally {
            confirmDelete.value.show = false
        }
    }

    // The status dot is derived server-side from last_seen, which core refreshes by
    // pinging every node once a minute (public_web_manager.schedule). Loaded once, the
    // dot is therefore a snapshot of page-load time: a node that comes up a moment later
    // stays red for as long as the page is open.
    //
    // Re-fetch the node list on a timer to keep it honest. Deliberately NOT loadNodes():
    // that also reloads every node's webs (an N+1 the dot does not need) and re-expands
    // all panels, which on a timer would keep reopening panels the user just collapsed.
    // Refreshing the list alone updates `nodes` - and so the dot - and leaves openPanels
    // and websByNode untouched. The edit dialog works on a copy of the node, so a refresh
    // underneath an open dialog cannot disturb it either.
    const STATUS_POLL_MS = 30_000
    let statusTimer: ReturnType<typeof setInterval> | undefined

    async function refreshStatuses(): Promise<void> {
        // Nothing to show while the tab is in the background; the visibility handler
        // below catches up the moment it is looked at again.
        if (document.hidden) return
        try {
            await configStore.loadPublicWebNodes(filter.value)
        } catch (error) {
            console.error('Error refreshing public-web node status:', error)
        }
    }

    function handleVisibilityChange(): void {
        if (!document.hidden) refreshStatuses()
    }

    onMounted(() => {
        loadNodes()
        statusTimer = setInterval(refreshStatuses, STATUS_POLL_MS)
        document.addEventListener('visibilitychange', handleVisibilityChange)
    })

    onUnmounted(() => {
        clearInterval(statusTimer)
        document.removeEventListener('visibilitychange', handleVisibilityChange)
    })
</script>
