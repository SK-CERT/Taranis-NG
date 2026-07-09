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
                <v-expansion-panel-title>
                    <v-icon
                        :color="statusColor(node.status)"
                        :icon="node.status === 'green' ? 'mdi-circle' : 'mdi-circle-outline'"
                        size="x-small"
                        class="me-2"
                        :title="statusTitle(node)"
                    />
                    <span class="font-weight-medium">{{ node.name }}</span>
                    <span class="text-medium-emphasis ms-2">{{ node.description }}</span>
                    <v-spacer />
                    <v-btn
                        v-if="canUpdate"
                        icon="mdi-pencil"
                        size="small"
                        variant="text"
                        class="me-1"
                        @click.stop="editNode(node)"
                    />
                    <v-btn
                        v-if="canDelete"
                        icon="mdi-delete"
                        size="small"
                        variant="text"
                        color="error"
                        @click.stop="askDeleteNode(node)"
                    />
                </v-expansion-panel-title>

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

                    <div class="d-flex justify-end mt-2">
                        <NewPublicWeb
                            :node-id="node.id"
                            :edit-item="webEditItems[node.id] || null"
                            @saved="handleWebSaved(node.id)"
                        />
                    </div>
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
    import { ref, computed, onMounted } from 'vue'
    import { useI18n } from 'vue-i18n'
    import { useConfigStore } from '@/stores/config'
    import { useAuth } from '@/composables/useAuth'
    import { getPublicWebs, deletePublicWebNode, deletePublicWeb, updatePublicWeb } from '@/api/config'
    import ToolbarFilter from '@/components/common/ToolbarFilter.vue'
    import NewPublicWebNode from '@/components/config/public-web/NewPublicWebNode.vue'
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
    const { checkPermission } = useAuth()

    const filter = ref<{ search: string }>({ search: '' })
    const openPanels = ref<number[]>([])
    const websByNode = ref<Record<number, WebItem[]>>({})
    const nodeEditItem = ref<NodeItem | null>(null)
    const webEditItems = ref<Record<number, any>>({})

    const canUpdate = computed(() => checkPermission('CONFIG_PUBLIC_WEB_NODE_UPDATE'))
    const canDelete = computed(() => checkPermission('CONFIG_PUBLIC_WEB_NODE_DELETE'))

    const nodes = computed<NodeItem[]>(() => (configStore.publicWebNodes.items as NodeItem[]) || [])

    // Health status dot: green (reachable) / orange (late) / red (unreachable or
    // no api_url). Driven by the node's last_seen via the core periodic ping.
    function statusColor(status?: string): string {
        return status === 'green' ? 'success' : status === 'orange' ? 'warning' : 'error'
    }

    function statusTitle(node: NodeItem): string {
        const key = node.status === 'green' ? 'alive' : node.status === 'orange' ? 'late' : 'unreachable'
        const state = t(`public_web.status.${key}`)
        return node.last_seen ? `${state} (${t('public_web.status.last_seen')}: ${node.last_seen})` : state
    }

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
    // also pushes a cache reset to the node), then reloads to reflect server state.
    const togglingWeb = ref<number | null>(null)

    async function toggleWebEnabled(nodeId: number, web: WebItem, value: boolean | null): Promise<void> {
        togglingWeb.value = web.id
        try {
            await updatePublicWeb(nodeId, { ...web, enabled: value !== false })
        } catch (error) {
            console.error('Error toggling web:', error)
        } finally {
            await loadWebs(nodeId)
            togglingWeb.value = null
        }
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
        } catch (error) {
            console.error('Error deleting:', error)
        } finally {
            confirmDelete.value.show = false
        }
    }

    onMounted(loadNodes)
</script>
