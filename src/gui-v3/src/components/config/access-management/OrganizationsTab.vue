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
                        class="text-end"
                    >
                        <NewOrganization
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
                :items="configStore.organizations.items"
                :search="search"
                item-key="id"
                class="elevation-1"
            >
                <template #item.name="{ item }">
                    <strong
                        ><bdi dir="auto">{{ asOrganizationItem(item).name }}</bdi></strong
                    >
                </template>

                <template #item.description="{ item }">
                    {{ asOrganizationItem(item).description }}
                </template>

                <template #item.actions="{ item }">
                    <ActionButton
                        action="edit"
                        :title="t('common.edit')"
                        class="me-1"
                        @click="handleEdit(asOrganizationItem(item))"
                    />
                    <ActionButton
                        v-if="canDelete"
                        action="delete"
                        :title="t('common.delete')"
                        @click="handleDelete(asOrganizationItem(item))"
                    />
                </template>
            </v-data-table>
        </v-card>

        <ConfirmationDialog
            v-model="deleteDialog"
            :message="isolateAuto(itemToDelete?.name)"
            max-width="600px"
            @confirm="confirmDelete"
        />
    </v-container>
</template>

<script setup lang="ts">
    import { computed, ref, onMounted } from 'vue'
    import { useI18n } from 'vue-i18n'
    import { useConfigStore } from '@/stores/config'
    import { deleteOrganization } from '@/api/config'
    import NewOrganization from '@/components/config/access-management/NewOrganization.vue'
    import ActionButton from '@/components/common/buttons/ActionButton.vue'
    import ConfirmationDialog from '@/components/common/dialogs/ConfirmationDialog.vue'
    import SearchField from '@/components/common/SearchField.vue'
    import { useAuth } from '@/composables/useAuth'

    type HeaderEntry = {
        title: string
        key: string
        sortable?: boolean
        align?: 'start' | 'end' | 'center'
    }

    type OrganizationItem = {
        id: string | number
        name?: string
        description?: string
        [key: string]: unknown
    }

    const { t } = useI18n()
    const configStore = useConfigStore()
    const { checkPermission } = useAuth()
    const canDelete = computed(() => checkPermission('CONFIG_ORGANIZATION_DELETE'))

    const search = ref('')
    const editItem = ref<OrganizationItem | null>(null)
    const deleteDialog = ref(false)
    const itemToDelete = ref<OrganizationItem | null>(null)

    const headers: HeaderEntry[] = [
        { title: t('access_management.organizations.name'), key: 'name' },
        { title: t('access_management.organizations.description'), key: 'description' },
        { title: t('settings.actions'), key: 'actions', sortable: false, align: 'end' }
    ]

    const asOrganizationItem = (item: unknown): OrganizationItem => item as OrganizationItem
    const FIRST_STRONG_ISOLATE = '\u2068'
    const POP_DIRECTIONAL_ISOLATE = '\u2069'
    const isolateAuto = (value: unknown): string =>
        value == null || value === '' ? '' : `${FIRST_STRONG_ISOLATE}${String(value)}${POP_DIRECTIONAL_ISOLATE}`

    const loadData = async (): Promise<void> => {
        try {
            await configStore.loadOrganizations({ search: search.value })
        } catch (error) {
            console.error('Error loading organizations:', error)
        }
    }

    const handleEdit = (item: OrganizationItem): void => {
        // Setting editItem triggers NewOrganization's watcher to open its dialog in edit mode.
        editItem.value = item
    }

    const handleDelete = (item: OrganizationItem): void => {
        if (!canDelete.value) return
        itemToDelete.value = item
        deleteDialog.value = true
    }

    const confirmDelete = async (): Promise<void> => {
        if (!canDelete.value || !itemToDelete.value) {
            return
        }
        try {
            await deleteOrganization(itemToDelete.value)
            await loadData()
        } catch (error) {
            console.error('Error deleting organization:', error)
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
