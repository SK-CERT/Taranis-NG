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
                    <v-col cols="4" class="text-right">
                        <NewACL :edit-item="editItem" @saved="handleSaved" @update:model-value="onDialogChange" />
                    </v-col>
                </v-row>
            </v-card-text>

            <!-- Data Table -->
            <v-data-table :headers="headers" :items="configStore.acls.items" :search="search" item-key="id" class="elevation-1">
                <template #item.name="{ item }">
                    <strong>{{ asACLItem(item).name }}</strong>
                </template>

                <template #item.description="{ item }">
                    {{ asACLItem(item).description }}
                </template>

                <template #item.item_type="{ item }">
                    {{ aclItemTypeLabel(asACLItem(item).item_type) }}
                </template>

                <template #item.actions="{ item }">
                    <ActionButton action="edit" :title="t('common.edit')" class="mr-1" @click="handleEdit(asACLItem(item))" />
                    <ActionButton action="delete" :title="t('common.delete')" @click="handleDelete(asACLItem(item))" />
                </template>
            </v-data-table>
        </v-card>

        <ConfirmationDialog v-model="deleteDialog" :message="itemToDelete?.name || ''" max-width="600px" @confirm="confirmDelete" />
    </v-container>
</template>

<script setup lang="ts">
    import { ref, onMounted } from 'vue'
    import { useI18n } from 'vue-i18n'
    import { useConfigStore } from '@/stores/config'
    import { deleteACLEntry } from '@/api/config'
    import NewACL from '@/components/config/access-management/NewACL.vue'
    import { aclItemTypeLabel } from '@/components/config/access-management/aclItemTypes'
    import ActionButton from '@/components/common/buttons/ActionButton.vue'
    import ConfirmationDialog from '@/components/common/dialogs/ConfirmationDialog.vue'

    type HeaderEntry = {
        title: string
        key: string
        sortable?: boolean
        align?: 'start' | 'end' | 'center'
    }

    type ACLItem = {
        id: string | number
        name?: string
        description?: string
        item_type?: string
        [key: string]: unknown
    }

    const { t } = useI18n()
    const configStore = useConfigStore()

    const search = ref('')
    const editItem = ref<ACLItem | null>(null)
    const deleteDialog = ref(false)
    const itemToDelete = ref<ACLItem | null>(null)

    const headers: HeaderEntry[] = [
        { title: t('access_management.acls.name'), key: 'name' },
        { title: t('access_management.acls.description'), key: 'description' },
        { title: t('access_management.acls.item_type'), key: 'item_type' },
        { title: t('settings.actions'), key: 'actions', sortable: false, align: 'end' }
    ]

    const asACLItem = (item: unknown): ACLItem => item as ACLItem

    const loadData = async (): Promise<void> => {
        try {
            await configStore.loadACLEntries({ search: search.value })
        } catch (error) {
            console.error('Error loading ACL entries:', error)
        }
    }

    const handleEdit = (item: ACLItem): void => {
        // Setting editItem triggers NewACL's watcher to open its dialog in edit mode.
        editItem.value = item
    }

    const handleDelete = (item: ACLItem): void => {
        itemToDelete.value = item
        deleteDialog.value = true
    }

    const confirmDelete = async (): Promise<void> => {
        if (!itemToDelete.value) {
            return
        }
        try {
            await deleteACLEntry(itemToDelete.value)
            await loadData()
        } catch (error) {
            console.error('Error deleting ACL entry:', error)
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
