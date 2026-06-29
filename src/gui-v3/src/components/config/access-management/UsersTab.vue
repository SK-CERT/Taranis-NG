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
                        <NewUser :edit-item="editItem" @saved="handleSaved" @update:model-value="onDialogChange" />
                    </v-col>
                </v-row>
            </v-card-text>

            <!-- Data Table -->
            <v-data-table :headers="headers" :items="configStore.users.items" :search="search" item-key="id" class="elevation-1">
                <template #item.username="{ item }">
                    <strong>{{ asUserItem(item).username }}</strong>
                </template>

                <template #item.name="{ item }">
                    {{ asUserItem(item).name }}
                </template>

                <template #item.organizations="{ item }">
                    <v-chip v-for="org in asUserItem(item).organizations || []" :key="org.id" size="small" class="mr-1">
                        {{ org.name }}
                    </v-chip>
                </template>

                <template #item.actions="{ item }">
                    <ActionButton action="edit" :title="t('common.edit')" class="mr-1" @click="handleEdit(asUserItem(item))" />
                    <ActionButton action="delete" :title="t('common.delete')" @click="handleDelete(asUserItem(item))" />
                </template>
            </v-data-table>
        </v-card>

        <ConfirmationDialog v-model="deleteDialog" :message="itemToDelete?.username || ''" max-width="600px" @confirm="confirmDelete" />
    </v-container>
</template>

<script setup lang="ts">
    import { ref, onMounted } from 'vue'
    import { useI18n } from 'vue-i18n'
    import { useConfigStore } from '@/stores/config'
    import { deleteUser } from '@/api/config'
    import NewUser from '@/components/config/access-management/NewUser.vue'
    import ActionButton from '@/components/common/buttons/ActionButton.vue'
    import ConfirmationDialog from '@/components/common/dialogs/ConfirmationDialog.vue'

    type HeaderEntry = {
        title: string
        key: string
        sortable?: boolean
        align?: 'start' | 'end' | 'center'
    }

    type OrganizationItem = {
        id: string | number
        name?: string
    }

    type UserItem = {
        id: string | number
        username?: string
        name?: string
        organizations?: OrganizationItem[]
        [key: string]: unknown
    }

    const { t } = useI18n()
    const configStore = useConfigStore()

    const search = ref('')
    const editItem = ref<UserItem | null>(null)
    const deleteDialog = ref(false)
    const itemToDelete = ref<UserItem | null>(null)

    const headers: HeaderEntry[] = [
        { title: t('access_management.users.username'), key: 'username' },
        { title: t('access_management.users.name'), key: 'name' },
        { title: t('access_management.users.organizations'), key: 'organizations' },
        { title: t('settings.actions'), key: 'actions', sortable: false, align: 'end' }
    ]

    const asUserItem = (item: unknown): UserItem => item as UserItem

    const loadData = async (): Promise<void> => {
        try {
            await configStore.loadUsers({ search: search.value })
        } catch (error) {
            console.error('Error loading users:', error)
        }
    }

    const handleEdit = (item: UserItem): void => {
        // Setting editItem triggers NewUser's watcher to open its dialog in edit mode.
        editItem.value = item
    }

    const handleDelete = (item: UserItem): void => {
        itemToDelete.value = item
        deleteDialog.value = true
    }

    const confirmDelete = async (): Promise<void> => {
        if (!itemToDelete.value) {
            return
        }
        try {
            await deleteUser(itemToDelete.value)
            await loadData()
        } catch (error) {
            console.error('Error deleting user:', error)
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
