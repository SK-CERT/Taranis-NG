<template>
    <v-dialog
        v-model="dialog"
        max-width="1000"
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
                :title="isEdit ? t('access_management.users.edit') : t('access_management.users.add_new')"
                :saving="saving"
                @cancel="requestClose"
                @save="saveAndClose"
            />

            <v-card-text>
                <v-form
                    ref="formRef"
                    @submit.prevent="saveAndClose"
                >
                    <v-row>
                        <v-col cols="6">
                            <v-text-field
                                v-model="localItem.username"
                                :label="t('access_management.users.username')"
                                variant="outlined"
                                density="comfortable"
                                :rules="[(v) => !!v || t('error.required')]"
                                :disabled="saving"
                            />
                        </v-col>
                        <v-col cols="6">
                            <v-text-field
                                v-model="localItem.name"
                                :label="t('access_management.users.name')"
                                variant="outlined"
                                density="comfortable"
                                :disabled="saving"
                            />
                        </v-col>
                    </v-row>

                    <v-row>
                        <v-col cols="6">
                            <v-text-field
                                v-model="password"
                                :label="t('access_management.users.password')"
                                :type="showPassword ? 'text' : 'password'"
                                variant="outlined"
                                density="comfortable"
                                :rules="passwordRules"
                                :disabled="saving"
                                :append-inner-icon="showPassword ? 'mdi-eye-off' : 'mdi-eye'"
                                @click:append-inner="showPassword = !showPassword"
                            />
                        </v-col>
                        <v-col cols="6">
                            <v-text-field
                                v-model="passwordConfirm"
                                :label="t('access_management.users.password_check')"
                                :type="showPassword ? 'text' : 'password'"
                                variant="outlined"
                                density="comfortable"
                                :rules="passwordConfirmRules"
                                :color="passwordsMatch ? 'success' : undefined"
                                :base-color="passwordsMatch ? 'success' : undefined"
                                :append-inner-icon="showPassword ? 'mdi-eye-off' : 'mdi-eye'"
                                :disabled="saving"
                                @click:append-inner="showPassword = !showPassword"
                            />
                        </v-col>
                    </v-row>

                    <v-divider class="my-4" />

                    <!-- Organizations Selection -->
                    <EntitySelectTable
                        v-model="selectedOrganizations"
                        :title="t('access_management.users.organizations')"
                        :items="organizations"
                        :headers="orgHeaders"
                        :loading="loadingOrganizations"
                        :disabled="saving"
                    />

                    <!-- Roles Selection -->
                    <EntitySelectTable
                        v-model="selectedRoles"
                        :title="t('access_management.users.roles')"
                        :items="roles"
                        :headers="roleHeaders"
                        :loading="loadingRoles"
                        :disabled="saving"
                    />

                    <!-- Permissions Selection -->
                    <EntitySelectTable
                        v-model="selectedPermissions"
                        :title="t('access_management.users.permissions')"
                        :items="permissions"
                        :headers="permissionHeaders"
                        :loading="loadingPermissions"
                        :disabled="saving"
                    />

                    <v-alert
                        v-if="showValidationError"
                        type="error"
                        density="compact"
                        class="mb-3"
                    >
                        {{ t('error.validation') }}
                    </v-alert>

                    <v-alert
                        v-if="showError"
                        type="error"
                        density="compact"
                        class="mb-3"
                    >
                        {{ t('access_management.users.error') }}
                    </v-alert>
                </v-form>
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
    import { createNewUser, updateUser, getAllOrganizations, getAllRoles, getAllPermissions } from '@/api/config'

    type SelectableEntity = {
        id: string | number
        name?: string
        description?: string
        [key: string]: unknown
    }

    type UserFormItem = {
        id: string | number | null
        username: string
        name: string
        organizations: SelectableEntity[]
        roles: SelectableEntity[]
        permissions: SelectableEntity[]
        password?: string
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
            editItem?: Partial<UserFormItem> | null
        }>(),
        {
            modelValue: false,
            editItem: null
        }
    )

    const emit = defineEmits(['update:modelValue', 'saved'])

    const { t } = useI18n()
    const { checkPermission } = useAuth()

    const dialog = ref(false)
    const formRef = ref<any>(null)
    const saving = ref(false)
    const showValidationError = ref(false)
    const showError = ref(false)
    const showPassword = ref(false)

    const password = ref('')
    const passwordConfirm = ref('')

    const organizations = ref<SelectableEntity[]>([])
    const roles = ref<SelectableEntity[]>([])
    const permissions = ref<SelectableEntity[]>([])

    const loadingOrganizations = ref(false)
    const loadingRoles = ref(false)
    const loadingPermissions = ref(false)

    const selectedOrganizations = ref<IdSelection>([])
    const selectedRoles = ref<IdSelection>([])
    const selectedPermissions = ref<IdSelection>([])

    const defaultItem: UserFormItem = {
        id: null,
        username: '',
        name: '',
        organizations: [],
        roles: [],
        permissions: []
    }

    const localItem = ref<UserFormItem>({ ...defaultItem })

    const isEdit = computed(() => !!localItem.value.id)
    const canCreate = computed(() => checkPermission('CONFIG_USER_CREATE'))

    const passwordRules = computed(() => {
        if (isEdit.value) {
            // For edit, password is optional unless filled
            return password.value ? [(v: string) => !!v || t('error.required')] : []
        }
        // For new user, password is required
        return [(v: string) => !!v || t('error.required')]
    })

    const passwordConfirmRules = computed(() => {
        if (isEdit.value && !password.value) {
            return []
        }
        return [
            (v: string) => !!v || t('error.required'),
            (v: string) => v === password.value || t('access_management.users.password_mismatch')
        ]
    })

    // True when both password fields are filled and identical, used to turn the confirm field green.
    const passwordsMatch = computed(() => !!passwordConfirm.value && passwordConfirm.value === password.value)

    const orgHeaders: TableHeader[] = [
        { title: t('access_management.users.name'), key: 'name', sortable: true },
        { title: t('access_management.organizations.description'), key: 'description', sortable: false }
    ]

    const roleHeaders: TableHeader[] = [
        { title: t('access_management.users.name'), key: 'name', sortable: true },
        { title: t('access_management.roles.description'), key: 'description', sortable: false }
    ]

    const permissionHeaders: TableHeader[] = [
        { title: t('access_management.users.name'), key: 'name', sortable: true },
        { title: t('access_management.acls.description'), key: 'description', sortable: false }
    ]

    // Watch for edit item changes
    watch(
        () => props.editItem,
        (newVal) => {
            if (newVal) {
                localItem.value = { ...defaultItem, ...newVal }

                // Set selected items
                selectedOrganizations.value = newVal.organizations?.map((org) => org.id) || []
                selectedRoles.value = newVal.roles?.map((role) => role.id) || []
                selectedPermissions.value = newVal.permissions?.map((perm) => perm.id) || []

                // Reset passwords
                password.value = ''
                passwordConfirm.value = ''

                dialog.value = true
            }
        },
        { immediate: true, deep: true }
    )

    // Watch dialog state
    watch(dialog, (newVal) => {
        if (!newVal) {
            resetForm()
        } else {
            // Snapshot the freshly-loaded form as the clean baseline for dirty-tracking.
            capture()
        }
        emit('update:modelValue', newVal)
    })

    // Load data on mount
    onMounted(async () => {
        await loadAllData()
    })

    const loadAllData = async (): Promise<void> => {
        loadingOrganizations.value = true
        loadingRoles.value = true
        loadingPermissions.value = true

        try {
            const [orgsResponse, rolesResponse, permsResponse] = await Promise.all([
                getAllOrganizations({ search: '' }),
                getAllRoles({ search: '' }),
                getAllPermissions({ search: '' })
            ])

            organizations.value = (orgsResponse as ListResponse).data?.items || []
            roles.value = (rolesResponse as ListResponse).data?.items || []
            permissions.value = (permsResponse as ListResponse).data?.items || []
        } catch (error) {
            console.error('Error loading user data:', error)
        } finally {
            loadingOrganizations.value = false
            loadingRoles.value = false
            loadingPermissions.value = false
        }
    }

    const resetForm = (): void => {
        localItem.value = { ...defaultItem }
        password.value = ''
        passwordConfirm.value = ''
        selectedOrganizations.value = []
        selectedRoles.value = []
        selectedPermissions.value = []
        showValidationError.value = false
        showError.value = false
        showPassword.value = false
        if (formRef.value) {
            formRef.value.resetValidation()
        }
    }

    const closeDialog = (): void => {
        dialog.value = false
    }

    // Persists the form. Returns true on success so the guard can decide whether to close.
    const persist = async (): Promise<boolean> => {
        showValidationError.value = false
        showError.value = false

        const { valid } = (await formRef.value.validate()) as FormValidationResult

        if (!valid) {
            showValidationError.value = true
            return false
        }

        saving.value = true

        try {
            // The backend requires an integer id even on create (it is ignored and the DB assigns
            // the real id); a null id fails schema validation, so send -1 as the "new" sentinel.
            const { id: currentId, ...rest } = localItem.value
            const payload: Record<string, unknown> = {
                ...rest,
                id: isEdit.value ? currentId : -1,
                organizations: selectedOrganizations.value.map((id) => ({ id })),
                roles: selectedRoles.value.map((id) => ({ id })),
                permissions: selectedPermissions.value.map((id) => ({ id }))
            }

            // Add password if provided
            if (password.value) {
                payload['password'] = password.value
            }

            if (isEdit.value) {
                await updateUser(payload)
                window.dispatchEvent(
                    new CustomEvent('notification', {
                        detail: { type: 'success', loc: 'common.updated_successfully' }
                    })
                )
            } else {
                await createNewUser(payload)
                window.dispatchEvent(
                    new CustomEvent('notification', {
                        detail: { type: 'success', loc: 'common.created_successfully' }
                    })
                )
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

    const { confirmVisible, capture, requestClose, continueEditing, saveAndClose, discardAndClose } = useUnsavedChanges({
        getState: () => ({
            item: localItem.value,
            password: password.value,
            passwordConfirm: passwordConfirm.value,
            organizations: selectedOrganizations.value,
            roles: selectedRoles.value,
            permissions: selectedPermissions.value
        }),
        save: persist,
        close: closeDialog
    })
</script>
