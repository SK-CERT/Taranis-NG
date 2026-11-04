<template>
    <v-container
        fluid
        class="pa-0"
    >
        <!-- Toolbar -->
        <ToolbarFilter
            :total-count="configStore.publishingChannels.total_count"
            total-count-title="publishers.channels.total_count"
            @update-filter="handleFilterUpdate"
        >
            <template #addbutton>
                <NewPublishingChannel
                    :edit-item="editItem"
                    @saved="handleSaved"
                />
            </template>
        </ToolbarFilter>

        <!-- Content -->
        <ContentData
            :items="configStore.publishingChannels.items"
            card-item="CardCompact"
            delete-permission="CONFIG_PUBLISHING_CHANNEL_DELETE"
            :loading="loading"
            @delete="handleDelete"
            @edit="handleEdit"
            @refresh="loadData"
        />
    </v-container>
</template>

<script setup lang="ts">
    import { ref, onMounted, nextTick } from 'vue'
    import { useI18n } from 'vue-i18n'
    import { useConfigStore } from '@/stores/config'
    import { deletePublishingChannel } from '@/api/config'
    import ToolbarFilter from '@/components/common/ToolbarFilter.vue'
    import ContentData from '@/components/common/ContentData.vue'
    import NewPublishingChannel from '@/components/config/publishers/NewPublishingChannel.vue'
    import { notifyDeleteError } from '@/utils/deleteError'

    const { t } = useI18n()
    const configStore = useConfigStore()

    type FilterState = {
        search: string
    }

    type PublishingChannelItem = {
        id?: string | number | null
        name?: string
        description?: string
        use_for_notifications?: boolean
        publisher_id?: string | number | null
        parameter_values?: unknown[]
        [key: string]: unknown
    }

    const loading = ref(false)
    const filter = ref<FilterState>({ search: '' })
    const editItem = ref<PublishingChannelItem | null>(null)

    const loadData = async (): Promise<void> => {
        loading.value = true
        try {
            await configStore.loadPublishingChannels(filter.value)
        } catch (error) {
            console.error('Error loading publishing channels:', error)
        } finally {
            loading.value = false
        }
    }

    const handleFilterUpdate = (newFilter: FilterState): void => {
        filter.value = newFilter
        loadData()
    }

    const handleDelete = async (channel: PublishingChannelItem): Promise<void> => {
        try {
            await deletePublishingChannel(channel)
            console.log('Publishing channel deleted successfully')
            await loadData()
        } catch (error) {
            console.error('Error deleting publishing channel:', error)
            notifyDeleteError(error, { inUse: 'publishers.channels.removed_error' })
        }
    }

    const handleEdit = async (item: PublishingChannelItem): Promise<void> => {
        // Reset first so re-selecting the same row reopens the dialog. The dialog
        // watches `editItem` by reference; assigning the same object again is not a
        // change, so after closing without saving a second click would do nothing.
        editItem.value = null
        await nextTick()
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
