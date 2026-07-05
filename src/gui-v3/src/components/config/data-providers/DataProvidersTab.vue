<template>
    <v-container fluid>
        <v-card>
            <!-- Toolbar -->
            <v-card-text>
                <v-row>
                    <v-col cols="8">
                        <SearchField
                            v-model="search"
                            :width="350"
                        />
                    </v-col>
                    <v-col
                        cols="4"
                        class="text-right"
                    >
                        <NewDataProvider
                            :edit-item="editItem"
                            @saved="handleSaved"
                            @update:model-value="onDialogChange"
                        />
                    </v-col>
                </v-row>
            </v-card-text>

            <!-- Data Table -->
            <v-data-table
                :headers="headers"
                :items="configStore.dataProviders.items"
                :search="search"
                item-key="id"
                class="elevation-1"
            >
                <template #item.name="{ item }">
                    <strong>{{ asDataProviderItem(item).name }}</strong>
                </template>

                <template #item.api_key="{ item }">
                    {{ asDataProviderItem(item).api_key ? '••••••••' : '' }}
                </template>

                <template #item.updated_at="{ item }">
                    {{ asDataProviderItem(item).updated_at ? new Date(String(asDataProviderItem(item).updated_at)).toLocaleString() : '' }}
                </template>

                <template #item.actions="{ item }">
                    <ActionButton
                        action="edit"
                        :title="t('common.edit')"
                        class="mr-1"
                        @click="handleEdit(asDataProviderItem(item))"
                    />
                    <ActionButton
                        action="delete"
                        :title="t('common.delete')"
                        @click="handleDelete(asDataProviderItem(item))"
                    />
                </template>
            </v-data-table>
        </v-card>

        <ConfirmationDialog
            v-model="deleteDialog"
            :message="itemToDelete?.name || ''"
            max-width="600px"
            @confirm="confirmDelete"
        />
    </v-container>
</template>

<script setup lang="ts">
    import { ref, onMounted } from 'vue'
    import { useI18n } from 'vue-i18n'
    import { useConfigStore } from '@/stores/config'
    import { deleteDataProvider } from '@/api/config'
    import NewDataProvider from '@/components/config/data-providers/NewDataProvider.vue'
    import ActionButton from '@/components/common/buttons/ActionButton.vue'
    import SearchField from '@/components/common/SearchField.vue'
    import ConfirmationDialog from '@/components/common/dialogs/ConfirmationDialog.vue'

    type HeaderEntry = {
        title: string
        key: string
        sortable?: boolean
    }

    type DataProviderItem = {
        id: string | number
        name?: string
        api_type?: string
        api_url?: string
        api_key?: string
        user_agent?: string
        web_url?: string
        updated_by?: string
        updated_at?: string
        [key: string]: unknown
    }

    const { t } = useI18n()
    const configStore = useConfigStore()

    const search = ref('')
    const editItem = ref<DataProviderItem | null>(null)
    const deleteDialog = ref(false)
    const itemToDelete = ref<DataProviderItem | null>(null)

    const headers: HeaderEntry[] = [
        { title: t('data_providers.data.name'), key: 'name' },
        { title: t('data_providers.data.api_type'), key: 'api_type' },
        { title: t('data_providers.data.api_url'), key: 'api_url' },
        { title: t('settings.api_key'), key: 'api_key', sortable: false },
        { title: t('data_providers.data.user_agent'), key: 'user_agent' },
        { title: t('data_providers.data.web_url'), key: 'web_url' },
        { title: t('settings.updated_by'), key: 'updated_by' },
        { title: t('settings.updated_at'), key: 'updated_at', sortable: false },
        { title: t('settings.actions'), key: 'actions', sortable: false }
    ]

    const asDataProviderItem = (item: unknown): DataProviderItem => item as DataProviderItem

    const loadData = async (): Promise<void> => {
        try {
            await configStore.loadDataProviders({ search: search.value })
        } catch (error) {
            console.error('Error loading data providers:', error)
        }
    }

    const handleEdit = (item: DataProviderItem): void => {
        // Setting editItem triggers NewDataProvider's watcher to open its dialog in edit mode.
        editItem.value = item
    }

    const handleDelete = (item: DataProviderItem): void => {
        itemToDelete.value = item
        deleteDialog.value = true
    }

    const confirmDelete = async (): Promise<void> => {
        if (!itemToDelete.value) {
            return
        }
        try {
            await deleteDataProvider(itemToDelete.value)
            await loadData()
        } catch (error) {
            console.error('Error deleting data provider:', error)
        } finally {
            itemToDelete.value = null
        }
    }

    const handleSaved = (): void => {
        editItem.value = null
        loadData()
    }

    // Reset editItem when the dialog closes so the same row can be edited again,
    // and so the Add New button opens a blank form.
    const onDialogChange = (open: boolean): void => {
        if (!open) {
            editItem.value = null
        }
    }

    onMounted(() => {
        loadData()
    })
</script>
