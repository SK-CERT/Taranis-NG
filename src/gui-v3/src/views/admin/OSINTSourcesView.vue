<template>
    <v-container
        fluid
        class="pa-2"
    >
        <!-- Toolbar -->
        <ToolbarFilter
            :total-count="configStore.osintSources.total_count"
            :selected-count="selectedIds.length"
            :show-selected-count="selectionEnabled"
            total-count-title="collectors.sources.total_count"
            @update-filter="handleFilterUpdate"
        >
            <!-- Selection, import, export and bulk delete share the search bar's line, ahead of
                 it: they act on the list the search produces. -->
            <template #prepend>
                <ToolbarGroup
                    ref="toolbarGroup"
                    view="collectors.sources"
                    :current-filter="filter"
                    @select-all="selectAll"
                    @clear-selection="clearSelection"
                    @osint-import="openImportDialog"
                    @osint-export="exportSources"
                    @osint-delete="askDeleteSelected"
                />
            </template>
            <template #addbutton>
                <NodeDialog
                    type="collectors"
                    :edit-item="nodeEditItem"
                    @saved="handleNodeSaved"
                />
            </template>
        </ToolbarFilter>
        <!-- Content. This is the only thing that scrolls: the toolbars above stay put because
             they sit outside the scroll area, and the node titles stick to its top. -->
        <div
            ref="scrollArea"
            class="osint-scroll"
            :style="{ height: scrollHeight ? `${scrollHeight}px` : undefined }"
        >
            <ContentDataOSINTSource
                :items="sourceItems"
                :nodes="collectorNodes"
                :loading="loading"
                :selection-enabled="selectionEnabled"
                :selected-ids="selectedIds"
                :collecting-id="collectingId"
                :toggling-id="togglingId"
                @delete="handleDelete"
                @edit="handleEdit"
                @collect="handleCollect"
                @toggle-enabled="handleToggleEnabled"
                @selection-change="handleSelectionChange"
                @edit-node="handleEditNode"
                @delete-node="handleDeleteNode"
            >
                <template #add-source="{ node }">
                    <NewOSINTSource
                        :preselect-node-id="node.id"
                        @saved="handleSaved"
                    />
                </template>
            </ContentDataOSINTSource>
        </div>

        <ConfirmationDialog
            v-model="deleteSelectedDialog"
            :message="t('collectors.sources.delete_selected_confirm', { count: selectedIds.length })"
            @confirm="deleteSelected"
        />

        <!-- One edit dialog for the whole list. The Add buttons live per node, so this instance
             renders no activator and opens only when a row is picked for editing. -->
        <NewOSINTSource
            :edit-item="editItem"
            hide-activator
            @saved="handleSaved"
        />
    </v-container>
    <v-dialog
        v-model="dialog"
        max-width="600"
        persistent
    >
        <v-card>
            <v-card-title>{{ t('collectors.sources.dialog_import') }}</v-card-title>
            <v-card-text>
                <v-form
                    ref="formRef"
                    @submit.prevent="importSources"
                >
                    <v-select
                        v-model="selectedNodeId"
                        :items="collectorNodes"
                        :item-title="nodeTitle"
                        item-value="id"
                        :label="t('collectors.sources.node')"
                        :loading="loadingNodes"
                        :disabled="importing"
                        :rules="[(value) => value !== null || t('collectors.sources.node_required')]"
                        variant="outlined"
                    />
                    <v-file-input
                        v-model="importFile"
                        accept="application/json,.json"
                        :label="t('collectors.sources.file')"
                        :disabled="importing || selectedNodeId === null"
                        :rules="[(value) => hasFile(value) || t('collectors.sources.file_required')]"
                        variant="outlined"
                    />
                </v-form>
            </v-card-text>
            <v-card-actions>
                <v-spacer />
                <v-btn
                    :disabled="importing"
                    @click="closeImportDialog"
                >
                    {{ t('common.cancel') }}
                </v-btn>
                <v-btn
                    color="primary"
                    :loading="importing"
                    :disabled="importing"
                    @click="importSources"
                >
                    {{ t('collectors.sources.import') }}
                </v-btn>
            </v-card-actions>
        </v-card>
    </v-dialog>
</template>

<script setup lang="ts">
    import { computed, ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
    import { useI18n } from 'vue-i18n'
    import { useConfigStore } from '@/stores/config'
    import { useOSINTSourceStore } from '@/stores/osint_source'
    import { collectOSINTSourceNow, deleteCollectorsNode, deleteOSINTSource, setOSINTSourceEnabled } from '@/api/config'
    import { useAuth } from '@/composables/useAuth'
    import { useOptimisticToggle } from '@/composables/useOptimisticToggle'
    import type { CollectorsNodeItem, OSINTSourceItem } from '@/types/collectors'
    import ToolbarFilter from '@/components/common/ToolbarFilter.vue'
    import ToolbarGroup from '@/components/common/ToolbarGroup.vue'
    import NewOSINTSource from '@/components/config/collectors/NewOSINTSource.vue'
    import ContentDataOSINTSource from '@/components/config/collectors/ContentDataOSINTSource.vue'
    import NodeDialog from '@/components/common/nodes/NodeDialog.vue'
    import ConfirmationDialog from '@/components/common/dialogs/ConfirmationDialog.vue'
    import { exportOSINTSources, importOSINTSources } from '@/api/config'

    const { t } = useI18n()
    const configStore = useConfigStore()
    const osintSourceStore = useOSINTSourceStore()

    type FilterState = {
        search: string
    }

    const loading = ref(false)
    const loadingNodes = ref(false)
    /** The source whose collect request is in flight, so its button can show a spinner. */
    const collectingId = ref<string | number | null>(null)
    /** The source whose enable/disable request is in flight. */
    // The row whose switch is saving; the composable owns it.
    const { busyId: togglingId, toggle } = useOptimisticToggle()
    /** The node being edited, which opens the node dialog the toolbar hosts. */
    const nodeEditItem = ref<Record<string, unknown> | null>(null)
    const COLLECT_POLL_MS = 5000
    let pollTimer: number | null = null
    const scrollArea = ref<HTMLElement | null>(null)
    const scrollHeight = ref<number | null>(null)

    /**
     * Size the scroll area to whatever space is left below it.
     *
     * Measured rather than a calc() of the chrome above, because that chrome varies: the app bar,
     * the tab strip and two toolbars, any of which can wrap on a narrow window.
     */
    const measureScrollArea = (): void => {
        const element = scrollArea.value
        if (!element) return
        const top = element.getBoundingClientRect().top
        scrollHeight.value = Math.max(240, window.innerHeight - top - 8)
    }
    const filter = ref<FilterState>({ search: '' })
    const editItem = ref<OSINTSourceItem | null>(null)
    const selectedIds = ref<Array<string | number>>([])
    const { checkPermission } = useAuth()

    const canImport = computed(() => checkPermission('CONFIG_OSINT_SOURCE_CREATE'))
    const canExport = computed(() => checkPermission('CONFIG_OSINT_SOURCE_ACCESS'))
    const selectionEnabled = computed(() => canExport.value && osintSourceStore.getOSINTSourcesMultiSelect)
    const sourceItems = computed(() => configStore.osintSources.items as OSINTSourceItem[])
    const collectorNodes = computed(() => configStore.collectorsNodes.items as CollectorsNodeItem[])

    const loadData = async ({ quiet = false }: { quiet?: boolean } = {}): Promise<void> => {
        // quiet is for the background refresh while something is collecting: showing the spinner
        // every few seconds would make the list flicker for no reason.
        if (!quiet) loading.value = true
        try {
            await configStore.loadOSINTSources(filter.value)
        } catch (error) {
            console.error('Error loading OSINT sources:', error)
        } finally {
            if (!quiet) loading.value = false
        }
    }

    const handleFilterUpdate = (newFilter: FilterState): void => {
        filter.value = newFilter
        loadData()
    }

    const handleDelete = async (source: OSINTSourceItem): Promise<void> => {
        try {
            await deleteOSINTSource(source)
            console.log('OSINT source deleted successfully')
            await loadData()
        } catch (error) {
            console.error('Error deleting OSINT source:', error)
        }
    }

    const deleteSelectedDialog = ref(false)

    const askDeleteSelected = (): void => {
        if (selectedIds.value.length === 0) return
        deleteSelectedDialog.value = true
    }

    /**
     * Delete every selected source.
     *
     * Sequential rather than concurrent: each delete refreshes the owning collector node, and
     * firing forty of those at once would have the node rebuild its schedule forty times over.
     * One failure does not abandon the rest - the others were asked for just as explicitly - so
     * the outcome is counted and reported once at the end.
     */
    const deleteSelected = async (): Promise<void> => {
        const doomed = sourceItems.value.filter((source) => selectedIds.value.includes(source.id))
        let failed = 0
        for (const source of doomed) {
            try {
                await deleteOSINTSource(source)
            } catch (error) {
                failed += 1
                console.error('Error deleting OSINT source:', error)
            }
        }
        clearSelection()
        await loadData()
        if (failed > 0) {
            notify('error', 'collectors.sources.delete_selected_error')
        } else {
            notify('success', 'collectors.sources.delete_selected_success')
        }
    }

    const handleEdit = async (source: OSINTSourceItem): Promise<void> => {
        // Reset first so re-selecting the same row reopens the dialog. The dialog
        // watches `editItem` by reference; assigning the same object again is not a
        // change, so after closing without saving a second click would do nothing.
        editItem.value = null
        await nextTick()
        editItem.value = source
    }

    const handleSaved = (): void => {
        editItem.value = null
        loadData()
    }

    const handleSelectionChange = (id: string | number, selected: boolean): void => {
        if (!canExport.value) return
        const selection = new Set(selectedIds.value)
        if (selected) {
            selection.add(id)
            osintSourceStore.selectOSINTSource({ id, type: 'osint-source' })
        } else {
            selection.delete(id)
            osintSourceStore.deselectOSINTSource({ id, type: 'osint-source' })
        }
        selectedIds.value = [...selection]
    }

    const selectAll = (): void => {
        if (!canExport.value) return
        selectedIds.value = sourceItems.value.map((source) => source.id)
        osintSourceStore.selection = sourceItems.value.map((source) => ({ id: source.id, type: 'osint-source' }))
    }

    const clearSelection = (): void => {
        selectedIds.value = []
        osintSourceStore.selection = []
    }

    // Import / Export code

    const dialog = ref(false)
    const importing = ref(false)
    const exporting = ref(false)
    const selectedNodeId = ref<string | number | null>(null)
    const importFile = ref<File | File[] | null>(null)
    const formRef = ref<{ validate: () => Promise<FormValidationResult>; resetValidation: () => void } | null>(null)
    const FIRST_STRONG_ISOLATE = '\u2068'
    const POP_DIRECTIONAL_ISOLATE = '\u2069'
    const isolateAuto = (value: unknown): string => `${FIRST_STRONG_ISOLATE}${String(value ?? '')}${POP_DIRECTIONAL_ISOLATE}`
    const nodeTitle = (node: CollectorNode): string => isolateAuto(node.name)

    const hasFile = (value: File | File[] | null): boolean => Boolean(Array.isArray(value) ? value[0] : value)

    type CollectorNode = {
        id: string | number
        name?: string
    }

    type FormValidationResult = {
        valid: boolean
    }

    type ExportResponse = {
        data: Blob
        headers?: Record<string, string>
    }

    const notify = (type: 'success' | 'error' | 'info', loc: string, timeout?: number): void => {
        window.dispatchEvent(
            new CustomEvent('notification', {
                detail: { id: 'osint-source-bulk-operation', type, loc, timeout }
            })
        )
    }

    const selectedFile = (): File | null => {
        if (Array.isArray(importFile.value)) return importFile.value[0] ?? null
        return importFile.value
    }

    const reloadCollectorNodes = async (): Promise<void> => {
        loadingNodes.value = true
        try {
            await configStore.loadCollectorsNodes({ search: '' })
        } finally {
            loadingNodes.value = false
        }
    }

    const loadCollectorNodes = async (): Promise<void> => {
        // Not gated on the import permission any more: the list groups sources by the node that
        // collects them, so anyone who can see sources needs the nodes.
        if (loadingNodes.value || collectorNodes.value.length > 0) return
        loadingNodes.value = true
        try {
            await configStore.loadCollectorsNodes({ search: '' })
        } catch {
            window.dispatchEvent(new CustomEvent('notification', { detail: { type: 'error', loc: 'collectors.sources.import_error' } }))
        } finally {
            loadingNodes.value = false
        }
    }

    const openImportDialog = (): void => {
        if (!canImport.value) return
        dialog.value = true
        loadCollectorNodes()
    }

    const closeImportDialog = (): void => {
        if (importing.value) return
        dialog.value = false
        selectedNodeId.value = null
        importFile.value = null
        formRef.value?.resetValidation()
    }

    const importSources = async (): Promise<void> => {
        if (!canImport.value || importing.value || !formRef.value) return

        const { valid } = await formRef.value.validate()
        const file = selectedFile()
        if (!valid || selectedNodeId.value === null || !file) return

        const formData = new FormData()
        formData.append('file', file)
        formData.append('collectors_node_id', String(selectedNodeId.value))

        importing.value = true
        notify('info', 'collectors.sources.import_progress', 0)
        try {
            await importOSINTSources(formData)
            notify('success', 'collectors.sources.import_success')
            importing.value = false
            closeImportDialog()
            clearSelection()
            await loadData()
        } catch {
            notify('error', 'collectors.sources.import_error')
        } finally {
            importing.value = false
        }
    }

    const filenameFromResponse = (response: ExportResponse): string => {
        const disposition = response.headers?.['content-disposition']
        const match = disposition?.match(/filename\*?=(?:UTF-8'')?["]?([^";\r\n]+)["]?/i)
        return match?.[1] ? decodeURIComponent(match[1]) : 'osint_sources_export.json'
    }

    const triggerDownload = (response: ExportResponse): void => {
        const url = window.URL.createObjectURL(new Blob([response.data], { type: 'application/json' }))
        const link = document.createElement('a')
        link.href = url
        link.download = filenameFromResponse(response)
        document.body.appendChild(link)
        link.click()
        link.remove()
        window.URL.revokeObjectURL(url)
    }

    const exportSources = async (): Promise<void> => {
        if (!canExport.value || exporting.value) return

        exporting.value = true
        notify('info', 'collectors.sources.export_progress', 0)
        try {
            const payload = selectedIds.value.length > 0 ? { selection: selectedIds.value } : {}
            const response = (await exportOSINTSources(payload)) as ExportResponse
            triggerDownload(response)
            notify('success', 'collectors.sources.export_success')
        } catch {
            notify('error', 'collectors.sources.export_error')
        } finally {
            exporting.value = false
        }
    }

    const handleCollect = async (source: OSINTSourceItem): Promise<void> => {
        collectingId.value = source.id
        try {
            await collectOSINTSourceNow(source as { id: string })
            // Show the source as busy at once; the reload below replaces it with what core says.
            source.collecting = true
            notify('success', 'collectors.sources.collect_started')
        } catch (error: unknown) {
            const status = (error as { response?: { status?: number } })?.response?.status
            notify('error', status === 409 ? 'collectors.sources.collect_conflict' : 'collectors.sources.collect_error')
        } finally {
            collectingId.value = null
            await loadData({ quiet: true })
        }
    }

    const handleToggleEnabled = async (source: OSINTSourceItem, enabled: boolean): Promise<void> => {
        await toggle(source as { id: string; enabled?: boolean }, enabled, {
            save: (value) => setOSINTSourceEnabled(source as { id: string }, value),
            reload: () => loadData({ quiet: true }),
            onError: () => notify('error', 'collectors.sources.enable_error')
        })
    }

    const handleEditNode = async (node: Record<string, unknown>): Promise<void> => {
        // Reset first so re-selecting the same node reopens the dialog, as the source edit does.
        nodeEditItem.value = null
        await nextTick()
        nodeEditItem.value = node
    }

    const handleNodeSaved = async (): Promise<void> => {
        nodeEditItem.value = null
        await reloadCollectorNodes()
        await loadData()
    }

    const handleDeleteNode = async (node: Record<string, unknown>): Promise<void> => {
        try {
            await deleteCollectorsNode(node)
            await reloadCollectorNodes()
            await loadData()
        } catch (error) {
            console.error('Error deleting collectors node:', error)
            notify('error', 'collectors.nodes.delete_error')
        }
    }

    // Poll only while something is actually collecting, so a quiet page makes no requests at all.
    const anyCollecting = computed(() => sourceItems.value.some((item: OSINTSourceItem) => item.collecting === true))

    const stopPolling = (): void => {
        if (pollTimer !== null) {
            window.clearInterval(pollTimer)
            pollTimer = null
        }
    }

    const startPolling = (): void => {
        if (pollTimer !== null) return
        pollTimer = window.setInterval(() => {
            // A background tab does not need to keep asking; visibilitychange catches it up.
            if (!document.hidden) loadData({ quiet: true })
        }, COLLECT_POLL_MS)
    }

    const handleVisibility = (): void => {
        if (!document.hidden && anyCollecting.value) loadData({ quiet: true })
    }

    watch(anyCollecting, (collecting: boolean) => (collecting ? startPolling() : stopPolling()), { immediate: true })

    onMounted(() => {
        measureScrollArea()
        window.addEventListener('resize', measureScrollArea)
        loadData()
        // The table groups sources by the node that collects them, so the nodes are needed up
        // front, not only when the import dialog opens.
        loadCollectorNodes()
        document.addEventListener('visibilitychange', handleVisibility)
    })

    onUnmounted(() => {
        window.removeEventListener('resize', measureScrollArea)
        stopPolling()
        document.removeEventListener('visibilitychange', handleVisibility)
    })
</script>

<style scoped>
    /* Sticky positioning cannot be used for the toolbars here: the tab lives inside a v-window,
       which sets overflow:hidden, and that becomes the nearest scrolling ancestor - so a sticky
       toolbar simply scrolls away with the page. Giving the list its own scroll area leaves the
       toolbars outside it, where they do not move at all. */
    .osint-scroll {
        overflow-y: auto;
        overscroll-behavior: contain;
    }
</style>
