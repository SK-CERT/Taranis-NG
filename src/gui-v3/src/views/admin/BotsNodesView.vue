<template>
    <v-container fluid class="pa-0">
        <!-- Toolbar -->
        <ToolbarFilter
            title="nav_menu.bots_nodes"
            :total-count="configStore.botsNodes.total_count"
            total-count-title="bots_node.total_count"
            @update-filter="handleFilterUpdate"
        >
            <template #addbutton>
                <NewBotsNode :edit-item="editItem" @saved="handleSaved" />
            </template>
        </ToolbarFilter>

        <!-- Content -->
        <ContentData
            :items="configStore.botsNodes.items"
            card-item="CardCompact"
            delete-permission="CONFIG_BOTS_NODE_DELETE"
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
    import { deleteBotsNode } from '@/api/config'
    import ToolbarFilter from '@/components/common/ToolbarFilter.vue'
    import ContentData from '@/components/common/ContentData.vue'
    import NewBotsNode from '@/components/config/bots/NewBotsNode.vue'

    const { t } = useI18n()
    const configStore = useConfigStore()

    type FilterState = {
        search: string
    }

    type BotsNodeItem = {
        id?: string | number | null
        name?: string
        description?: string
        api_url?: string
        api_key?: string
        [key: string]: unknown
    }

    const loading = ref(false)
    const filter = ref<FilterState>({ search: '' })
    const editItem = ref<BotsNodeItem | null>(null)

    const loadData = async (): Promise<void> => {
        loading.value = true
        try {
            await configStore.loadBotsNodes(filter.value)
        } catch (error) {
            console.error('Error loading bots nodes:', error)
        } finally {
            loading.value = false
        }
    }

    const handleFilterUpdate = (newFilter: FilterState): void => {
        filter.value = newFilter
        loadData()
    }

    const handleDelete = async (node: BotsNodeItem): Promise<void> => {
        try {
            await deleteBotsNode(node)
            console.log('Bots node deleted successfully')
            await loadData()
        } catch (error) {
            console.error('Error deleting bots node:', error)
        }
    }

    const handleEdit = (item: BotsNodeItem): void => {
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
