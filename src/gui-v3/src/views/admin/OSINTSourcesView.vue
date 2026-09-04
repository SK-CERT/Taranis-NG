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
            <template #addbutton>
                <NewOSINTSource
                    :edit-item="editItem"
                    @saved="handleSaved"
                />
            </template>
        </ToolbarFilter>
        <v-toolbar
            flat
            color="surface"
            density="compact"
        >
            <ToolbarGroup
                ref="toolbarGroup"
                view="collectors.sources"
                :current-filter="filter"
                @select-all="selectAll"
                @clear-selection="clearSelection"
                @osint-import="openImportDialog"
                @osint-export="exportSources"
            />
        </v-toolbar>
        <!-- Content -->
        <ContentDataOSINTSource
            :items="sourceItems"
            :loading="loading"
            :selection-enabled="selectionEnabled"
            :selected-ids="selectedIds"
            @delete="handleDelete"
            @edit="handleEdit"
            @selection-change="handleSelectionChange"
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
    import { computed, ref, onMounted, nextTick } from 'vue'
    import { useI18n } from 'vue-i18n'
    import { useConfigStore } from '@/stores/config'
    import { useOSINTSourceStore } from '@/stores/osint_source'
    import { deleteOSINTSource } from '@/api/config'
    import { useAuth } from '@/composables/useAuth'
    import ToolbarFilter from '@/components/common/ToolbarFilter.vue'
    import ToolbarGroup from '@/components/common/ToolbarGroup.vue'
    import NewOSINTSource from '@/components/config/collectors/NewOSINTSource.vue'
    import ContentDataOSINTSource from '@/components/config/collectors/ContentDataOSINTSource.vue'
    import { exportOSINTSources, importOSINTSources } from '@/api/config'

    const { t } = useI18n()
    const configStore = useConfigStore()
    const osintSourceStore = useOSINTSourceStore()

    type FilterState = {
        search: string
    }

    type OSINTSourceItem = {
        id: string | number
        name?: string
        description?: string
        feed_url?: string
        collector?: string
        refresh_interval?: number
        enabled?: boolean
        [key: string]: unknown
    }

    const loading = ref(false)
    const loadingNodes = ref(false)
    const filter = ref<FilterState>({ search: '' })
    const editItem = ref<OSINTSourceItem | null>(null)
    const selectedIds = ref<Array<string | number>>([])
    const { checkPermission } = useAuth()

    const canImport = computed(() => checkPermission('CONFIG_OSINT_SOURCE_CREATE'))
    const canExport = computed(() => checkPermission('CONFIG_OSINT_SOURCE_ACCESS'))
    const selectionEnabled = computed(() => canExport.value && osintSourceStore.getOSINTSourcesMultiSelect)
    const sourceItems = computed(() => configStore.osintSources.items as OSINTSourceItem[])
    const collectorNodes = computed(() => configStore.collectorsNodes.items as Array<{ id: string | number; name?: string }>)

    const loadData = async (): Promise<void> => {
        loading.value = true
        try {
            await configStore.loadOSINTSources(filter.value)
        } catch (error) {
            console.error('Error loading OSINT sources:', error)
        } finally {
            loading.value = false
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

    const loadCollectorNodes = async (): Promise<void> => {
        if (!canImport.value || loadingNodes.value || collectorNodes.value.length > 0) return
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

    onMounted(() => {
        loadData()
    })
</script>
