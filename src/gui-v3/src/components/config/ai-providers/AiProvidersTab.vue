<template>
    <v-container fluid>
        <v-card>
            <v-card-title class="d-flex align-center">
                <v-tooltip location="right">
                    <template #activator="{ props }">
                        <v-icon v-bind="props" color="blue" class="me-2"> mdi-help-circle </v-icon>
                    </template>
                    <span>{{ t('data_provider.ai_providers.tab_description') }}</span>
                </v-tooltip>
                <span>{{ t('nav_menu.ai_providers') }}</span>
            </v-card-title>

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
                    <v-col cols="4" class="text-right">
                        <NewAiProvider @saved="handleSaved" />
                    </v-col>
                </v-row>
            </v-card-text>

            <!-- Data Table -->
            <v-data-table :headers="headers" :items="configStore.aiProviders.items" :search="search" item-key="id" class="elevation-1">
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
                    <ActionButton action="edit" :title="t('common.edit')" class="mr-1" @click="handleEdit(asAiProviderItem(item))" />
                    <ActionButton action="delete" :title="t('common.delete')" @click="handleDelete(asAiProviderItem(item))" />
                </template>
            </v-data-table>
        </v-card>

        <!-- Edit Dialog -->
        <v-dialog v-model="showEditDialog" max-width="600">
            <NewAiProvider :edit-item="editItem" @saved="handleSaved" />
        </v-dialog>
    </v-container>
</template>

<script setup lang="ts">
    import { ref, onMounted } from 'vue'
    import { useI18n } from 'vue-i18n'
    import { useConfigStore } from '@/stores/config'
    import { deleteAiProvider } from '@/api/config'
    import NewAiProvider from '@/components/config/ai-providers/NewAiProvider.vue'
    import ActionButton from '@/components/common/buttons/ActionButton.vue'

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
    const showEditDialog = ref(false)
    const editItem = ref<AiProviderItem | null>(null)

    const headers: HeaderEntry[] = [
        { title: t('ai_provider.name'), key: 'name' },
        { title: t('ai_provider.api_type'), key: 'api_type' },
        { title: t('ai_provider.model'), key: 'model' },
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
        editItem.value = item
        showEditDialog.value = true
    }

    const handleDelete = async (item: AiProviderItem): Promise<void> => {
        if (confirm(t('common.messagebox.delete_confirm', { name: item.name }))) {
            try {
                await deleteAiProvider(item)
                await loadData()
            } catch (error) {
                console.error('Error deleting AI provider:', error)
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
