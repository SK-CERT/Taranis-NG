<template>
    <v-container
        fluid
        class="pa-0"
    >
        <!-- Toolbar -->
        <ToolbarFilter
            :total-count="configStore.remoteAccess.total_count"
            total-count-title="remote.access.total_count"
            @update-filter="handleFilterUpdate"
        >
            <template #addbutton>
                <NewRemoteAccess
                    :edit-item="editItem"
                    @saved="handleSaved"
                />
            </template>
        </ToolbarFilter>

        <!-- Content -->
        <ContentData
            :items="configStore.remoteAccess.items"
            card-item="CardCompact"
            delete-permission="CONFIG_REMOTE_ACCESS_DELETE"
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
    import { deleteRemoteAccess } from '@/api/config'
    import ToolbarFilter from '@/components/common/ToolbarFilter.vue'
    import ContentData from '@/components/common/ContentData.vue'
    import NewRemoteAccess from '@/components/config/remote/NewRemoteAccess.vue'

    const { t } = useI18n()
    const configStore = useConfigStore()

    type RemoteFilter = {
        search: string
    }

    type RemoteAccessItem = {
        id?: string | number | null
        name?: string
        description?: string
        access_key?: string
        enabled?: boolean
        [key: string]: unknown
    }

    const loading = ref(false)
    const filter = ref<RemoteFilter>({ search: '' })
    const editItem = ref<RemoteAccessItem | null>(null)

    const loadData = async (): Promise<void> => {
        loading.value = true
        try {
            await configStore.loadRemoteAccesses(filter.value)
        } catch (error) {
            console.error('Error loading remote accesses:', error)
        } finally {
            loading.value = false
        }
    }

    const handleFilterUpdate = (newFilter: RemoteFilter): void => {
        filter.value = newFilter
        loadData()
    }

    const handleDelete = async (remoteAccess: RemoteAccessItem): Promise<void> => {
        try {
            await deleteRemoteAccess(remoteAccess)
            console.log('Remote access deleted successfully')
            await loadData()
        } catch (error) {
            console.error('Error deleting remote access:', error)
        }
    }

    const handleEdit = (item: RemoteAccessItem): void => {
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
