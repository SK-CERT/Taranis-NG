<template>
    <v-container fluid class="pa-0">
        <!-- Toolbar -->
        <ToolbarFilter
            :total-count="configStore.osintSources.total_count"
            total-count-title="collectors.sources.total_count"
            @update-filter="handleFilterUpdate"
        >
            <template #addbutton>
                <NewOSINTSource :edit-item="editItem" @saved="handleSaved" />
            </template>
        </ToolbarFilter>

        <!-- Content -->
        <ContentData
            :items="configStore.osintSources.items"
            card-item="CardCompact"
            delete-permission="CONFIG_OSINT_SOURCE_DELETE"
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
    import { deleteOSINTSource } from '@/api/config'
    import ToolbarFilter from '@/components/common/ToolbarFilter.vue'
    import ContentData from '@/components/common/ContentData.vue'
    import NewOSINTSource from '@/components/config/collectors/NewOSINTSource.vue'

    const { t } = useI18n()
    const configStore = useConfigStore()

    type FilterState = {
        search: string
    }

    type OSINTSourceItem = {
        id?: string | number | null
        name?: string
        description?: string
        feed_url?: string
        collector?: string
        refresh_interval?: number
        enabled?: boolean
        [key: string]: unknown
    }

    const loading = ref(false)
    const filter = ref<FilterState>({ search: '' })
    const editItem = ref<OSINTSourceItem | null>(null)

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

    onMounted(() => {
        loadData()
    })
</script>
