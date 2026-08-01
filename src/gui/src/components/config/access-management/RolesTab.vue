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
                        <NewRole
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
                :items="configStore.roles.items"
                :search="search"
                item-key="id"
                class="elevation-1"
            >
                <template #item.name="{ item }">
                    <strong>{{ asRoleItem(item).name }}</strong>
                </template>

                <template #item.description="{ item }">
                    {{ asRoleItem(item).description }}
                </template>

                <template #item.actions="{ item }">
                    <ActionButton
                        action="edit"
                        :title="t('common.edit')"
                        class="mr-1"
                        @click="handleEdit(asRoleItem(item))"
                    />
                    <ActionButton
                        action="delete"
                        :title="t('common.delete')"
                        @click="handleDelete(asRoleItem(item))"
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
    import { deleteRole } from '@/api/config'
    import NewRole from '@/components/config/access-management/NewRole.vue'
    import ActionButton from '@/components/common/buttons/ActionButton.vue'
    import ConfirmationDialog from '@/components/common/dialogs/ConfirmationDialog.vue'
    import SearchField from '@/components/common/SearchField.vue'

    type HeaderEntry = {
        title: string
        key: string
        sortable?: boolean
        align?: 'start' | 'end' | 'center'
    }

    type RoleItem = {
        id: string | number
        name?: string
        description?: string
        [key: string]: unknown
    }

    const { t } = useI18n()
    const configStore = useConfigStore()

    const search = ref('')
    const editItem = ref<RoleItem | null>(null)
    const deleteDialog = ref(false)
    const itemToDelete = ref<RoleItem | null>(null)

    const headers: HeaderEntry[] = [
        { title: t('access_management.roles.name'), key: 'name' },
        { title: t('access_management.roles.description'), key: 'description' },
        { title: t('settings.actions'), key: 'actions', sortable: false, align: 'end' }
    ]

    const asRoleItem = (item: unknown): RoleItem => item as RoleItem

    const loadData = async (): Promise<void> => {
        try {
            await configStore.loadRoles({ search: search.value })
        } catch (error) {
            console.error('Error loading roles:', error)
        }
    }

    const handleEdit = (item: RoleItem): void => {
        // Setting editItem triggers NewRole's watcher to open its dialog in edit mode.
        editItem.value = item
    }

    const handleDelete = (item: RoleItem): void => {
        itemToDelete.value = item
        deleteDialog.value = true
    }

    const confirmDelete = async (): Promise<void> => {
        if (!itemToDelete.value) {
            return
        }
        try {
            await deleteRole(itemToDelete.value)
            await loadData()
        } catch (error) {
            console.error('Error deleting role:', error)
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
