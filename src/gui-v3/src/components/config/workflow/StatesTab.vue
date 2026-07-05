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
                        <AddNewButton
                            :show="canCreate"
                            @click="addItem"
                        />
                    </v-col>
                </v-row>
            </v-card-text>

            <!-- Data Table -->
            <v-data-table
                :headers="headers"
                :items="filteredRecords"
                :search="search"
                item-key="id"
                class="elevation-1"
            >
                <template #item.display_name="{ item }">
                    {{ $te(`workflow.states.${item.display_name}`) ? $t(`workflow.states.${item.display_name}`) : item.display_name }}
                </template>

                <template #item.color="{ item }">
                    <v-chip
                        :color="item.color"
                        label
                        :text-color="getContrastColor(item.color)"
                    >
                        {{ item.color }}
                    </v-chip>
                </template>

                <template #item.icon="{ item }">
                    <v-icon :color="item.color">
                        {{ item.icon }}
                    </v-icon>
                </template>

                <template #item.actions="{ item }">
                    <template v-if="item.editable">
                        <ActionButton
                            action="edit"
                            :title="t('common.edit')"
                            class="mr-1"
                            @click="editItem(item)"
                        />
                        <ActionButton
                            action="delete"
                            :title="t('common.delete')"
                            @click="deleteItem(item)"
                        />
                    </template>
                    <template v-else>
                        <ActionButton
                            action="lock"
                            :title="t('workflow.states.cannot_edit_system_state')"
                        />
                    </template>
                </template>
            </v-data-table>
        </v-card>

        <!-- Delete Dialog -->
        <ConfirmationDialog
            v-model="dialogDelete"
            :message="editedItem.display_name"
            max-width="500"
            @confirm="deleteRecord"
        />

        <!-- Edit Dialog - Simplified for now -->
        <v-dialog
            v-model="dialogEdit"
            max-width="700"
            scrollable
        >
            <v-card>
                <DialogToolbar
                    :title="editedIndex === -1 ? t('workflow.states.add_new') : t('workflow.states.edit')"
                    :show-save="isEditable"
                    @cancel="closeEdit"
                    @save="saveRecord"
                />
                <v-card-text>
                    <v-form ref="formRef">
                        <v-text-field
                            v-model="editedItem.display_name"
                            :label="t('workflow.states.display_name')"
                            :disabled="!isEditable"
                            variant="outlined"
                            density="comfortable"
                            class="mb-3"
                            :rules="[(v) => !!v || t('error.required')]"
                        />

                        <v-textarea
                            v-model="editedItem.description"
                            :label="t('workflow.states.description')"
                            :disabled="!isEditable"
                            variant="outlined"
                            density="comfortable"
                            rows="3"
                            class="mb-3"
                        />

                        <v-text-field
                            v-model="editedItem.color"
                            :label="t('workflow.states.color')"
                            :disabled="!isEditable"
                            variant="outlined"
                            type="color"
                            density="comfortable"
                            class="mb-3"
                        />

                        <v-text-field
                            v-model="editedItem.icon"
                            :label="t('workflow.states.icon')"
                            :disabled="!isEditable"
                            variant="outlined"
                            density="comfortable"
                            placeholder="mdi-circle"
                        />
                    </v-form>
                </v-card-text>
            </v-card>
        </v-dialog>
    </v-container>
</template>

<script setup lang="ts">
    import { ref, computed, onMounted } from 'vue'
    import { useI18n } from 'vue-i18n'
    import AddNewButton from '@/components/common/buttons/AddNewButton.vue'
    import ActionButton from '@/components/common/buttons/ActionButton.vue'
    import DialogToolbar from '@/components/common/dialogs/DialogToolbar.vue'
    import ConfirmationDialog from '@/components/common/dialogs/ConfirmationDialog.vue'
    import SearchField from '@/components/common/SearchField.vue'
    import { useConfigStore } from '@/stores/config'
    import { useAuth } from '@/composables/useAuth'
    import { createNewStateDefinition, updateStateDefinition, deleteStateDefinition } from '@/api/config'

    type StateDefinition = {
        id: string | number
        display_name: string
        description: string
        color: string
        icon: string
        editable: boolean
        [key: string]: unknown
    }

    type HeaderEntry = {
        title: string
        key: string
        sortable?: boolean
    }

    type FormValidationResult = {
        valid: boolean
    }

    const { t } = useI18n()
    const configStore = useConfigStore()
    const { checkPermission } = useAuth()

    const search = ref('')
    const dialogEdit = ref(false)
    const dialogDelete = ref(false)
    const editedIndex = ref(-1)
    const formRef = ref<any>(null)

    const defaultItem: StateDefinition = {
        id: -1,
        display_name: '',
        description: '',
        color: '#2196F3',
        icon: 'mdi-circle',
        editable: true
    }

    const editedItem = ref<StateDefinition>({ ...defaultItem })

    const headers: HeaderEntry[] = [
        { title: t('workflow.states.display_name'), key: 'display_name' },
        { title: t('workflow.states.description'), key: 'description' },
        { title: t('workflow.states.color'), key: 'color' },
        { title: t('workflow.states.icon'), key: 'icon' },
        { title: t('settings.actions'), key: 'actions', sortable: false }
    ]

    const canCreate = computed(() => checkPermission('CONFIG_WORKFLOW_CREATE'))

    const isEditable = computed(() => editedIndex.value === -1 || editedItem.value.editable)

    const filteredRecords = computed<StateDefinition[]>(() =>
        Array.isArray(configStore.stateDefinitions.items) ? (configStore.stateDefinitions.items as StateDefinition[]) : []
    )

    function getContrastColor(hexColor?: string): 'white' | 'black' {
        if (!hexColor || hexColor.length < 7) return 'white'
        const r = parseInt(hexColor.slice(1, 3), 16)
        const g = parseInt(hexColor.slice(3, 5), 16)
        const b = parseInt(hexColor.slice(5, 7), 16)
        const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
        return luminance > 0.5 ? 'black' : 'white'
    }

    function addItem(): void {
        editedIndex.value = -1
        editedItem.value = { ...defaultItem }
        dialogEdit.value = true
    }

    function editItem(item: StateDefinition): void {
        const records = filteredRecords.value
        editedIndex.value = records.indexOf(item)
        editedItem.value = { ...item }
        dialogEdit.value = true
    }

    function deleteItem(item: StateDefinition): void {
        if (!item.editable) return
        const records = filteredRecords.value
        editedIndex.value = records.indexOf(item)
        editedItem.value = { ...item }
        dialogDelete.value = true
    }

    // No close-time reset: addItem/editItem/deleteItem fully set editedItem/editedIndex
    // before opening, so resetting here is unnecessary. A deferred reset (to avoid the
    // close-animation flicker) would also race the next dialog open and clobber its state.
    function closeEdit(): void {
        dialogEdit.value = false
    }

    function closeDelete(): void {
        dialogDelete.value = false
    }

    async function saveRecord(): Promise<void> {
        const { valid } = (await formRef.value.validate()) as FormValidationResult
        if (!valid) return

        try {
            // Send only editable fields. On create, omit id entirely so the backend
            // assigns a real auto-increment id; sending id (e.g. -1) inserts a row with
            // that id, which the delete route (/<int>) can then never match -> 404.
            const payload = {
                display_name: editedItem.value.display_name,
                description: editedItem.value.description,
                color: editedItem.value.color,
                icon: editedItem.value.icon,
                editable: editedItem.value.editable
            }
            if (editedIndex.value > -1) {
                await updateStateDefinition({ ...payload, id: editedItem.value.id })
            } else {
                await createNewStateDefinition(payload)
            }
            await configStore.loadStateDefinitions({ search: '' })
            closeEdit()
        } catch (error) {
            window.dispatchEvent(
                new CustomEvent('notification', {
                    detail: { type: 'error', loc: 'common.error_saving' }
                })
            )
        }
    }

    async function deleteRecord(): Promise<void> {
        if (!editedItem.value.editable) {
            closeDelete()
            return
        }

        try {
            await deleteStateDefinition(editedItem.value)
            await configStore.loadStateDefinitions({ search: '' })
            closeDelete()
        } catch (error) {
            console.error('Error deleting state:', error)
        }
    }

    onMounted(() => {
        if (checkPermission('CONFIG_WORKFLOW_ACCESS')) {
            configStore.loadStateDefinitions({ search: '' })
        }
    })
</script>
