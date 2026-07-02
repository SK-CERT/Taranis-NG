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
                        <NewAiProvider
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
                :items="configStore.aiProviders.items"
                :search="search"
                item-key="id"
                class="elevation-1"
            >
                <template #item.name="{ item }">
                    <strong>{{ asAiProviderItem(item).name }}</strong>
                </template>

                <template #item.api_type="{ item }">
                    <v-chip size="small">
                        {{ asAiProviderItem(item).api_type }}
                    </v-chip>
                </template>

                <template #item.model="{ item }">
                    {{ asAiProviderItem(item).model }}
                </template>

                <template #item.api_key="{ item }">
                    {{ asAiProviderItem(item).api_key ? '••••••••' : '-' }}
                </template>

                <template #item.updated_at="{ item }">
                    {{ asAiProviderItem(item).updated_at ? new Date(String(asAiProviderItem(item).updated_at)).toLocaleString() : '' }}
                </template>

                <template #item.actions="{ item }">
                    <ActionButton
                        action="edit"
                        :title="t('common.edit')"
                        class="mr-1"
                        @click="handleEdit(asAiProviderItem(item))"
                    />
                    <ActionButton
                        action="delete"
                        :title="t('common.delete')"
                        @click="handleDelete(asAiProviderItem(item))"
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
    import { deleteAiProvider } from '@/api/config'
    import NewAiProvider from '@/components/config/data-providers/NewAiProvider.vue'
    import ActionButton from '@/components/common/buttons/ActionButton.vue'
    import SearchField from '@/components/common/SearchField.vue'
    import ConfirmationDialog from '@/components/common/dialogs/ConfirmationDialog.vue'

    type HeaderEntry = {
        title: string
        key: string
        sortable?: boolean
    }

    type AiProviderItem = {
        id: string | number
        name?: string
        api_type?: string
        model?: string
        api_key?: string
        updated_by?: string
        updated_at?: string
        [key: string]: unknown
    }

    const { t } = useI18n()
    const configStore = useConfigStore()

    const search = ref('')
    const editItem = ref<AiProviderItem | null>(null)
    const deleteDialog = ref(false)
    const itemToDelete = ref<AiProviderItem | null>(null)

    const headers: HeaderEntry[] = [
        { title: t('data_providers.ai.name'), key: 'name' },
        { title: t('data_providers.ai.api_type'), key: 'api_type' },
        { title: t('data_providers.ai.model'), key: 'model' },
        { title: t('settings.api_key'), key: 'api_key', sortable: false },
        { title: t('settings.updated_by'), key: 'updated_by' },
        { title: t('settings.updated_at'), key: 'updated_at', sortable: false },
        { title: t('settings.actions'), key: 'actions', sortable: false }
    ]

    const asAiProviderItem = (item: unknown): AiProviderItem => item as AiProviderItem

    const loadData = async (): Promise<void> => {
        try {
            await configStore.loadAiProviders({ search: search.value })
        } catch (error) {
            console.error('Error loading AI providers:', error)
        }
    }

    const handleEdit = (item: AiProviderItem): void => {
        // Setting editItem triggers NewAiProvider's watcher to open its dialog in edit mode.
        editItem.value = item
    }

    const handleDelete = (item: AiProviderItem): void => {
        itemToDelete.value = item
        deleteDialog.value = true
    }

    const confirmDelete = async (): Promise<void> => {
        if (!itemToDelete.value) {
            return
        }
        try {
            await deleteAiProvider(itemToDelete.value)
            await loadData()
        } catch (error) {
            console.error('Error deleting AI provider:', error)
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
