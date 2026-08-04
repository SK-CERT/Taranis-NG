<template>
    <v-container
        fluid
        class="pa-0"
    >
        <!-- Toolbar -->
        <ToolbarFilter
            :total-count="configStore.osintSources.total_count"
            total-count-title="collectors.sources.total_count"
            @update-filter="handleFilterUpdate"
        >
            <template #addbutton>
                <div class="d-flex align-center justify-end ga-2 flex-wrap">
                    <OSINTSourceBulkActions
                        :can-import="canImport"
                        :can-export="canExport"
                        :nodes="collectorNodes"
                        :loading-nodes="loadingNodes"
                        :selected-ids="selectedIds"
                        :source-count="sourceItems.length"
                        @load-nodes="loadCollectorNodes"
                        @import-complete="handleImportComplete"
                        @select-all="selectAll"
                        @clear-selection="clearSelection"
                    />
                    <NewOSINTSource
                        :edit-item="editItem"
                        @saved="handleSaved"
                    />
                </div>
            </template>
        </ToolbarFilter>

        <!-- Content -->
        <OSINTSourceBulkList
            :items="sourceItems"
            :loading="loading"
            :selection-enabled="canExport"
            :selected-ids="selectedIds"
            @delete="handleDelete"
            @edit="handleEdit"
            @selection-change="handleSelectionChange"
        />
    </v-container>
</template>

<script setup lang="ts">
    import { computed, ref, onMounted } from 'vue'
    import { useI18n } from 'vue-i18n'
    import { useConfigStore } from '@/stores/config'
    import { deleteOSINTSource } from '@/api/config'
    import { useAuth } from '@/composables/useAuth'
    import ToolbarFilter from '@/components/common/ToolbarFilter.vue'
    import NewOSINTSource from '@/components/config/collectors/NewOSINTSource.vue'
    import OSINTSourceBulkActions from '@/components/config/collectors/OSINTSourceBulkActions.vue'
    import OSINTSourceBulkList from '@/components/config/collectors/OSINTSourceBulkList.vue'

    const { t } = useI18n()
    const configStore = useConfigStore()

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

    const handleEdit = (source: OSINTSourceItem): void => {
        editItem.value = source
    }

    const handleSaved = (): void => {
        editItem.value = null
        loadData()
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

    const handleSelectionChange = (id: string | number, selected: boolean): void => {
        if (!canExport.value) return
        const selection = new Set(selectedIds.value)
        if (selected) selection.add(id)
        else selection.delete(id)
        selectedIds.value = [...selection]
    }

    const selectAll = (): void => {
        if (!canExport.value) return
        selectedIds.value = sourceItems.value.map((source) => source.id)
    }

    const clearSelection = (): void => {
        selectedIds.value = []
    }

    const handleImportComplete = async (): Promise<void> => {
        clearSelection()
        await loadData()
    }

    onMounted(() => {
        loadData()
    })
</script>
