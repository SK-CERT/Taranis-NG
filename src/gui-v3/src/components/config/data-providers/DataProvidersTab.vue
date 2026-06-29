<template>
    <v-container fluid>
        <v-card>
            <!-- Toolbar -->
            <v-card-text>
                <v-row>
                    <v-col cols="8">
                        <v-text-field
                            v-model="search"
                            :label="t('toolbar_filter.search')"
                            prepend-inner-icon="mdi-magnify"
                            variant="outlined"
                            density="compact"
                            hide-details
                            single-line
                        />
                    </v-col>
                    <v-col
                        cols="4"
                        class="text-right"
                    >
                        <NewDataProvider @saved="handleSaved" />
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

        <!-- Edit Dialog -->
        <v-dialog
            v-model="showEditDialog"
            max-width="800"
        >
            <NewDataProvider
                :edit-item="editItem"
                @saved="handleSaved"
            />
        </v-dialog>
    </v-container>
</template>

<script setup lang="ts">
    import { ref, onMounted } from 'vue'
    import { useI18n } from 'vue-i18n'
    import { useConfigStore } from '@/stores/config'
    import { deleteDataProvider } from '@/api/config'
    import NewDataProvider from '@/components/config/data-providers/NewDataProvider.vue'
    import ActionButton from '@/components/common/buttons/ActionButton.vue'

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
    const showEditDialog = ref(false)
    const editItem = ref<DataProviderItem | null>(null)

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
        editItem.value = item
        showEditDialog.value = true
    }

    const handleDelete = async (item: DataProviderItem): Promise<void> => {
        if (confirm(t('common.messagebox.delete_confirm', { name: item.name }))) {
            try {
                await deleteDataProvider(item)
                await loadData()
            } catch (error) {
                console.error('Error deleting data provider:', error)
            }
        }
    }

    const handleSaved = (): void => {
        showEditDialog.value = false
        editItem.value = null
        loadData()
    }

    onMounted(() => {
        loadData()
    })
</script>
