<template>
    <v-container
        fluid
        class="pa-0"
    >
        <!-- Toolbar -->
        <ToolbarFilter
            :total-count="list.total_count"
            :total-count-title="`${config.i18nPrefix}.total_count`"
            @update-filter="handleFilterUpdate"
        >
            <template #addbutton>
                <NodeDialog
                    :type="type"
                    :edit-item="editItem"
                    @saved="handleSaved"
                />
            </template>
        </ToolbarFilter>

        <!-- Content -->
        <ContentData
            :items="list.items"
            card-item="CardCompact"
            :delete-permission="`${config.permissionPrefix}_DELETE`"
            :loading="loading"
            @delete="handleDelete"
            @edit="handleEdit"
            @refresh="loadData"
        />
    </v-container>
</template>

<script setup lang="ts">
    import { ref, computed, onMounted, nextTick } from 'vue'
    import { useConfigStore } from '@/stores/config'
    import ToolbarFilter from '@/components/common/ToolbarFilter.vue'
    import ContentData from '@/components/common/ContentData.vue'
    import NodeDialog from './NodeDialog.vue'
    import { NODE_TYPES, type NodeType } from './nodeTypes'

    const props = defineProps<{ type: NodeType }>()

    const config = computed(() => NODE_TYPES[props.type])
    const configStore = useConfigStore()
    // Access the per-type store slice/action by name from the registry.
    const storeAny = configStore as unknown as Record<string, any>

    type FilterState = {
        search: string
    }

    type NodeItem = {
        id?: string | number | null
        [key: string]: unknown
    }

    type NodeListState = {
        items: NodeItem[]
        total_count: number
    }

    const loading = ref(false)
    const filter = ref<FilterState>({ search: '' })
    const editItem = ref<NodeItem | null>(null)

    const list = computed<NodeListState>(() => storeAny[config.value.listKey] as NodeListState)

    const loadData = async (): Promise<void> => {
        loading.value = true
        try {
            await storeAny[config.value.loadAction](filter.value)
        } catch (error) {
            console.error(`Error loading ${props.type} nodes:`, error)
        } finally {
            loading.value = false
        }
    }

    const handleFilterUpdate = (newFilter: FilterState): void => {
        filter.value = newFilter
        loadData()
    }

    const handleDelete = async (node: NodeItem): Promise<void> => {
        try {
            await config.value.deleteFn(node)
            await loadData()
        } catch (error) {
            console.error(`Error deleting ${props.type} node:`, error)
        }
    }

    const handleEdit = async (item: NodeItem): Promise<void> => {
        // Reset first so re-selecting the same card is still a change the dialog reacts to.
        editItem.value = null
        await nextTick()
        editItem.value = item
    }

    const handleSaved = (): void => {
        editItem.value = null
        loadData()
    }

    onMounted(loadData)
</script>
