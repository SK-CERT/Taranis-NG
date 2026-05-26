<template>
    <v-container fluid class="pa-0">
        <!-- Toolbar -->
        <ToolbarFilter
            title="nav_menu.collectors_nodes"
            :total-count="configStore.collectorsNodes.total_count"
            total-count-title="collectors_node.total_count"
            @update-filter="handleFilterUpdate"
        >
            <template #addbutton>
                <NewCollectorsNode :edit-item="editItem" @saved="handleSaved" />
            </template>
        </ToolbarFilter>

        <!-- Content -->
        <ContentData
            :items="configStore.collectorsNodes.items"
            card-item="CardCompact"
            delete-permission="CONFIG_COLLECTORS_NODE_DELETE"
            :loading="loading"
            @delete="handleDelete"
            @edit="handleEdit"
            @refresh="loadData"
        />
    </v-container>
</template>

<script setup lang="ts">
    import { ref, onMounted } from 'vue'
    import { useI18n } from 'vue-i18n'
    import { useConfigStore } from '@/stores/config'
    import { deleteCollectorsNode } from '@/api/config'
    import ToolbarFilter from '@/components/common/ToolbarFilter.vue'
    import ContentData from '@/components/common/ContentData.vue'
    import NewCollectorsNode from '@/components/config/collectors/NewCollectorsNode.vue'

    const { t } = useI18n()
    const configStore = useConfigStore()

    type FilterState = {
        search: string
    }

    type CollectorsNodeItem = {
        id?: string | number | null
        name?: string
        description?: string
        api_url?: string
        api_key?: string
        [key: string]: unknown
    }

    const loading = ref(false)
    const filter = ref<FilterState>({ search: '' })
    const editItem = ref<CollectorsNodeItem | null>(null)

    const loadData = async (): Promise<void> => {
        loading.value = true
        try {
            await configStore.loadCollectorsNodes(filter.value)
        } catch (error) {
            console.error('Error loading collectors nodes:', error)
        } finally {
            loading.value = false
        }
    }

    const handleFilterUpdate = (newFilter: FilterState): void => {
        filter.value = newFilter
        loadData()
    }

    const handleDelete = async (node: CollectorsNodeItem): Promise<void> => {
        try {
            await deleteCollectorsNode(node)
            console.log('Collectors node deleted successfully')
            await loadData()
        } catch (error) {
            console.error('Error deleting collectors node:', error)
        }
    }

    const handleEdit = (item: CollectorsNodeItem): void => {
        editItem.value = item
    }

    const handleSaved = (): void => {
        editItem.value = null
        loadData()
    }

    onMounted(() => {
        loadData()
    })
</script>
