<template>
    <v-container fluid>
        <v-card>
            <v-card-title class="d-flex align-center">
                <span>{{ t('nav_menu.external_users') }}</span>
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
                        <NewExternalUser @saved="handleSaved" />
                    </v-col>
                </v-row>
            </v-card-text>

            <!-- Data Table -->
            <v-data-table :headers="headers" :items="configStore.users.items" :search="search" item-key="id" class="elevation-1">
                <template #item.username="{ item }">
                    <strong>{{ asExternalUserItem(item).username }}</strong>
                </template>

                <template #item.name="{ item }">
                    {{ asExternalUserItem(item).name }}
                </template>

                <template #item.actions="{ item }">
                    <ActionButton action="edit" :title="t('common.edit')" class="mr-1" @click="handleEdit(asExternalUserItem(item))" />
                    <ActionButton action="delete" :title="t('common.delete')" @click="handleDelete(asExternalUserItem(item))" />
                </template>
            </v-data-table>
        </v-card>

        <!-- Edit Dialog -->
        <v-dialog v-model="showEditDialog" max-width="800">
            <NewExternalUser :edit-item="editItem" @saved="handleSaved" />
        </v-dialog>
    </v-container>
</template>

<script setup lang="ts">
    import { ref, onMounted } from 'vue'
    import { useI18n } from 'vue-i18n'
    import { useConfigStore } from '@/stores/config'
    import { deleteExternalUser } from '@/api/config'
    import NewExternalUser from '@/components/config/external/NewExternalUser.vue'
    import ActionButton from '@/components/common/buttons/ActionButton.vue'

    type HeaderEntry = {
        title: string
        key: string
        sortable?: boolean
    }

    type ExternalUserItem = {
        id?: string | number | null
        username?: string
        name?: string
        description?: string
        [key: string]: unknown
    }

    const { t } = useI18n()
    const configStore = useConfigStore()

    const search = ref('')
    const showEditDialog = ref(false)
    const editItem = ref<ExternalUserItem | null>(null)

    const headers: HeaderEntry[] = [
        { title: t('external_user.username'), key: 'username' },
        { title: t('external_user.name'), key: 'name' },
        { title: t('settings.actions'), key: 'actions', sortable: false }
    ]

    const asExternalUserItem = (item: unknown): ExternalUserItem => item as ExternalUserItem

    const loadData = async (): Promise<void> => {
        try {
            await configStore.loadExternalUsers({ search: search.value })
        } catch (error) {
            console.error('Error loading external users:', error)
        }
    }

    const handleEdit = (item: ExternalUserItem): void => {
        editItem.value = item
        showEditDialog.value = true
    }

    const handleDelete = async (item: ExternalUserItem): Promise<void> => {
        if (confirm(t('common.messagebox.delete_confirm', { name: item.username }))) {
            try {
                await deleteExternalUser(item)
                await loadData()
            } catch (error) {
                console.error('Error deleting external user:', error)
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
