<template>
    <v-dialog
        v-model="dialog"
        max-width="900"
        persistent
        scrollable
        @keydown.esc="requestClose"
    >
        <template #activator="{ props: activatorProps }">
            <AddNewButton
                :show="canCreate"
                v-bind="activatorProps"
            />
        </template>

        <v-card>
            <DialogToolbar
                :title="isEdit ? t('access_management.roles.edit') : t('access_management.roles.add_new')"
                :saving="saving"
                @cancel="requestClose"
                @save="saveAndClose"
            />

            <v-card-text>
                <v-form
                    ref="formRef"
                    @submit.prevent="saveAndClose"
                >
                    <v-text-field
                        v-model="localItem.name"
                        :label="t('access_management.roles.title')"
                        variant="outlined"
                        density="comfortable"
                        class="mb-3"
                        :rules="[(v) => !!v || t('error.required')]"
                        :disabled="saving"
                    />

                    <v-textarea
                        v-model="localItem.description"
                        :label="t('access_management.roles.description')"
                        variant="outlined"
                        density="comfortable"
                        rows="3"
                        :disabled="saving"
                    />

                    <!-- Permissions Selection -->
                    <EntitySelectTable
                        v-model="selectedPermissions"
                        :title="t('access_management.roles.permissions')"
                        :items="permissions"
                        :headers="permissionHeaders"
                        :loading="loadingPermissions"
                        :disabled="saving"
                    />
                </v-form>

                <v-alert
                    v-if="showValidationError"
                    type="error"
                    variant="tonal"
                    class="mt-4"
                    closable
                    @click:close="showValidationError = false"
                >
                    {{ t('error.validation') }}
                </v-alert>

                <v-alert
                    v-if="showError"
                    type="error"
                    variant="tonal"
                    class="mt-4"
                    closable
                    @click:close="showError = false"
                >
                    {{ t('access_management.roles.error') }}
                </v-alert>
            </v-card-text>
        </v-card>

        <UnsavedChangesDialog
            v-model="confirmVisible"
            @continue="continueEditing"
            @save="saveAndClose"
            @discard="discardAndClose"
        />
    </v-dialog>
</template>

<script setup lang="ts">
    import { ref, computed, watch, onMounted } from 'vue'
    import { useI18n } from 'vue-i18n'
    import { useAuth } from '@/composables/useAuth'
    import AddNewButton from '@/components/common/buttons/AddNewButton.vue'
    import DialogToolbar from '@/components/common/dialogs/DialogToolbar.vue'
    import UnsavedChangesDialog from '@/components/common/dialogs/UnsavedChangesDialog.vue'
    import { useUnsavedChanges } from '@/composables/useUnsavedChanges'
    import EntitySelectTable from '@/components/common/EntitySelectTable.vue'
    import { createNewRole, updateRole, getAllPermissions } from '@/api/config'

    type SelectableEntity = {
        id: string | number
        name?: string
        description?: string
        [key: string]: unknown
    }

    type RoleItem = {
        id: string | number | null
        name: string
        description: string
        permissions: unknown[]
        [key: string]: unknown
    }

    type FormValidationResult = {
        valid: boolean
    }

    type TableHeader = {
        title: string
        key: string
        sortable: boolean
    }

    type IdSelection = Array<string | number>

    type ListResponse = {
        data?: {
            items?: SelectableEntity[]
        }
    }

    const props = withDefaults(
        defineProps<{
            modelValue?: boolean
            editItem?: Partial<RoleItem> | null
        }>(),
        {
            modelValue: false,
            editItem: null
        }
    )

    const emit = defineEmits(['update:modelValue', 'saved'])

    const { t } = useI18n()
    const { checkPermission } = useAuth()

    const formRef = ref<any>(null)
    const showValidationError = ref(false)
    const showError = ref(false)
    const saving = ref(false)
    const dialog = ref(false)

    const permissions = ref<SelectableEntity[]>([])
    const loadingPermissions = ref(false)
    const selectedPermissions = ref<IdSelection>([])

    const permissionHeaders: TableHeader[] = [
        { title: t('access_management.roles.name'), key: 'name', sortable: true },
        { title: t('access_management.roles.description'), key: 'description', sortable: false }
    ]

    const defaultItem: RoleItem = {
        // Empty string (not null): backend requires a string id even on create (ignored), null fails validation.
        id: '',
        name: '',
        description: '',
        permissions: []
    }

    const localItem = ref<RoleItem>({ ...defaultItem })

    const isEdit = computed(() => !!localItem.value.id)
    const canCreate = computed(() => checkPermission('CONFIG_ROLE_CREATE'))
    const canUpdate = computed(() => checkPermission('CONFIG_ROLE_UPDATE') || !isEdit.value)

    const loadPermissions = async (): Promise<void> => {
        loadingPermissions.value = true
        try {
            const response = await getAllPermissions({ search: '' })
            permissions.value = (response as ListResponse).data?.items || []
        } catch (error) {
            console.error('Error loading permissions:', error)
        } finally {
            loadingPermissions.value = false
        }
    }

    onMounted(loadPermissions)

    // Persists the form. Returns true on success so the guard can decide whether to close.
    async function persist(): Promise<boolean> {
        showValidationError.value = false
        showError.value = false

        const { valid } = (await formRef.value.validate()) as FormValidationResult
        if (!valid) {
            showValidationError.value = true
            return false
        }

        saving.value = true
        try {
            const payload: RoleItem = {
                ...localItem.value,
                permissions: selectedPermissions.value.map((id) => ({ id }))
            }
            if (isEdit.value) {
                await updateRole(payload)
            } else {
                await createNewRole(payload)
            }
            emit('saved')
            return true
        } catch (error) {
            window.dispatchEvent(
                new CustomEvent('notification', {
                    detail: { type: 'error', loc: 'common.error_saving' }
                })
            )
            showError.value = true
            return false
        } finally {
            saving.value = false
        }
    }

    function closeDialog(): void {
        showValidationError.value = false
        showError.value = false
        formRef.value?.reset()
        localItem.value = { ...defaultItem }
        selectedPermissions.value = []
        dialog.value = false
    }

    const { confirmVisible, capture, requestClose, continueEditing, saveAndClose, discardAndClose } = useUnsavedChanges({
        getState: () => ({ item: localItem.value, permissions: selectedPermissions.value }),
        save: persist,
        close: closeDialog
    })

    watch(
        () => props.editItem,
        (newItem) => {
            if (newItem && Object.keys(newItem).length > 0) {
                localItem.value = { ...defaultItem, ...newItem }
                selectedPermissions.value = Array.isArray(newItem.permissions)
                    ? (newItem.permissions as SelectableEntity[]).map((perm) => perm.id)
                    : []
                // Opening the dialog automatically when an item to edit is provided.
                dialog.value = true
            } else {
                localItem.value = { ...defaultItem }
                selectedPermissions.value = []
            }
        },
        { immediate: true, deep: true }
    )

    watch(
        () => dialog.value,
        (newVal) => {
            if (!newVal) {
                showValidationError.value = false
                showError.value = false
                saving.value = false
                formRef.value?.reset()
                localItem.value = { ...defaultItem }
                selectedPermissions.value = []
            } else {
                // Snapshot the freshly-loaded form as the clean baseline for dirty-tracking.
                capture()
            }
            emit('update:modelValue', newVal)
        }
    )
</script>
