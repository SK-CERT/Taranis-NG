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
                                v-model="email"
                                :label="t('access_management.users.email')"
                                type="email"
                                variant="outlined"
                                density="comfortable"
                                :disabled="saving"
                            />
                        </v-col>
                        <v-col cols="3">
                            <v-select
                                v-model="status"
                                :items="statusOptions"
                                :label="t('access_management.users.status')"
                                variant="outlined"
                                density="comfortable"
                                :disabled="saving"
                            />
                        </v-col>
                        <v-col
                            cols="3"
                            class="d-flex align-center"
                        >
                            <v-btn
                                v-if="isEdit && hasMfa"
                                color="warning"
                                variant="outlined"
                                prepend-icon="mdi-shield-off"
                                :disabled="saving"
                                @click="resetMfaDialog = true"
                            >
                                {{ t('access_management.users.reset_mfa') }}
                            </v-btn>
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
                                :hint="t('access_management.users.password_hint')"
                                :disabled="saving || clearPassword"
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
                                :disabled="saving || clearPassword"
                                @click:append-inner="showPassword = !showPassword"
                            />
                        </v-col>
                    </v-row>

                    <v-row v-if="isEdit && hasStoredPassword">
                        <v-col cols="12">
                            <v-checkbox
                                v-model="clearPassword"
                                :label="t('access_management.users.clear_password')"
                                color="warning"
                                density="compact"
                                hide-details
                                :disabled="saving || !!password"
                            />
                        </v-col>
                    </v-row>

                    <v-row>
                        <v-col cols="12">
                            <v-switch
                                v-model="localItem.require_mfa"
                                :label="t('access_management.users.require_mfa')"
                                :hint="t('access_management.users.require_mfa_hint')"
                                persistent-hint
                                color="primary"
                                :disabled="saving"
                                data-test="user-require-mfa"
                            />
                        </v-col>
                    </v-row>

                    <v-divider class="my-4" />

                    <!-- Login identities at external providers -->
                    <EditableEntityTable
                        v-if="externalProviders.length > 0"
                        v-model="identities"
                        :title="t('access_management.users.identities')"
                        :headers="identityHeaders"
                        :default-item="newIdentity"
                        :add-title="t('access_management.users.add_identity')"
                        :edit-title="t('access_management.users.edit_identity')"
                        :no-data-text="t('access_management.users.no_identities')"
                        :disabled="saving"
                        dialog-max-width="600"
                    >
                        <template #item.auth_provider_id="{ item }">
                            {{ providerName(item.auth_provider_id) }}
                        </template>
                        <template #item.last_login_at="{ item }">
                            {{ item.last_login_at || '-' }}
                        </template>

                        <template #form="{ item }">
                            <v-select
                                v-model="item.auth_provider_id"
                                :items="externalProviders"
                                item-title="name"
                                item-value="id"
                                :label="t('access_management.users.identity_provider')"
                                variant="outlined"
                                density="comfortable"
                                class="mb-3"
                                :rules="[(v) => !!v || t('error.required')]"
                            />
                            <v-text-field
                                v-model="item.external_username"
                                :label="t('access_management.users.external_username')"
                                variant="outlined"
                                density="comfortable"
                                :hint="t('access_management.users.external_username_hint')"
                                persistent-hint
                                :rules="[(v) => !!v || t('error.required')]"
                            />
                        </template>
                    </EditableEntityTable>

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

                    <!-- The backend explains what to fix (e.g. an identity already linked
                         to another account); fall back to the generic text if it did not. -->
                    <v-alert
                        v-if="showError"
                        type="error"
                        density="compact"
                        class="mb-3"
                        data-test="user-error"
                    >
                        {{ errorMessage || t('access_management.users.error') }}
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

        <!-- Reset MFA: choose what to reset (TOTP only, passkeys only, or both) -->
        <v-dialog
            v-model="resetMfaDialog"
            max-width="500"
        >
            <v-card>
                <v-card-title>{{ t('access_management.users.reset_mfa') }}</v-card-title>
                <v-card-text>
                    <p class="text-body-2 mb-3">
                        {{ t('access_management.users.reset_mfa_choose', { username: localItem.username }) }}
                    </p>
                    <v-radio-group v-model="resetMfaChoice">
                        <v-radio
                            v-if="userMfa.totp"
                            value="totp"
                            :label="t('access_management.users.reset_mfa_totp_only')"
                        />
                        <v-radio
                            v-if="(userMfa.passkeys ?? 0) > 0"
                            value="passkeys"
                            :label="t('access_management.users.reset_mfa_passkeys_only')"
                        />
                        <v-radio
                            v-if="userMfa.totp && (userMfa.passkeys ?? 0) > 0"
                            value="both"
                            :label="t('access_management.users.reset_mfa_both')"
                        />
                    </v-radio-group>
                </v-card-text>
                <v-card-actions>
                    <v-spacer />
                    <v-btn
                        variant="text"
                        @click="resetMfaDialog = false"
                    >
                        {{ t('common.cancel') }}
                    </v-btn>
                    <v-btn
                        color="warning"
                        variant="flat"
                        :disabled="!resetMfaChoice"
                        @click="handleResetMfa"
                    >
                        {{ t('access_management.users.reset_mfa') }}
                    </v-btn>
                </v-card-actions>
            </v-card>
        </v-dialog>
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
    import EditableEntityTable from '@/components/common/EditableEntityTable.vue'
    import {
        createNewUser,
        updateUser,
        getAllOrganizations,
        getAllRoles,
        getAllPermissions,
        getAllAuthProviders,
        resetUserMfa
    } from '@/api/config'

    type SelectableEntity = {
        id: string | number
        name?: string
        description?: string
        [key: string]: unknown
    }

    type IdentityRow = {
        auth_provider_id?: number | null
        external_username?: string
        last_login_at?: string | null
        [key: string]: unknown
    }

    type AuthProviderEntity = {
        id: number
        name?: string
        kind?: string
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
        email?: string | null
        status?: string
        require_mfa?: boolean
        identities?: IdentityRow[]
        has_password?: boolean
        mfa?: { totp?: boolean; passkeys?: number }
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
    const errorMessage = ref('')
    const showPassword = ref(false)

    const password = ref('')
    const passwordConfirm = ref('')
    const email = ref('')
    const status = ref('active')
    const clearPassword = ref(false)
    const identities = ref<IdentityRow[]>([])
    const resetMfaDialog = ref(false)
    const resetMfaChoice = ref<'totp' | 'passkeys' | 'both' | ''>('')
    const hasStoredPassword = ref(false)
    const userMfa = ref<{ totp?: boolean; passkeys?: number }>({})

    const organizations = ref<SelectableEntity[]>([])
    const roles = ref<SelectableEntity[]>([])
    const permissions = ref<SelectableEntity[]>([])
    const authProviders = ref<AuthProviderEntity[]>([])

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
        require_mfa: false,
        organizations: [],
        roles: [],
        permissions: []
    }

    const localItem = ref<UserFormItem>({ ...defaultItem })

    const isEdit = computed(() => !!localItem.value.id)
    const canCreate = computed(() => checkPermission('CONFIG_USER_CREATE'))
    const hasMfa = computed(() => !!(userMfa.value.totp || (userMfa.value.passkeys ?? 0) > 0))
    // Only external kinds can be linked as identities (local login is the password itself)
    const externalProviders = computed(() =>
        authProviders.value.filter((provider) => ['oidc', 'oauth2', 'saml', 'ldap'].includes(provider.kind || ''))
    )

    const statusOptions = computed(() => [
        { title: t('access_management.users.statuses.pending'), value: 'pending' },
        { title: t('access_management.users.statuses.active'), value: 'active' },
        { title: t('access_management.users.statuses.disabled'), value: 'disabled' }
    ])

    const passwordRules = computed(() => {
        if (isEdit.value) {
            // For edit, password is optional unless filled
            return password.value ? [(v: string) => !!v || t('error.required')] : []
        }
        if (identities.value.length > 0) {
            // Users with external identities do not need a local password
            return []
        }
        // For new user without identities, password is required
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

    const identityHeaders = [
        { title: t('access_management.users.identity_provider'), key: 'auth_provider_id', sortable: false },
        { title: t('access_management.users.external_username'), key: 'external_username', sortable: false },
        { title: t('access_management.users.last_login'), key: 'last_login_at', sortable: false },
        { title: t('settings.actions'), key: 'actions', sortable: false, width: '15%', align: 'end' as const }
    ]

    const newIdentity = (): IdentityRow => ({ auth_provider_id: null, external_username: '' })

    const providerName = (providerId: number | null): string => {
        const provider = authProviders.value.find((candidate) => candidate.id === providerId)
        return provider?.name || String(providerId ?? '')
    }

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

                email.value = (newVal.email as string) || ''
                status.value = (newVal.status as string) || 'active'
                identities.value = JSON.parse(JSON.stringify(newVal.identities || [])) as IdentityRow[]
                hasStoredPassword.value = !!newVal.has_password
                userMfa.value = (newVal.mfa as { totp?: boolean; passkeys?: number }) || {}
                clearPassword.value = false
                resetMfaChoice.value = ''

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

        // Providers require a separate permission; identity linking is hidden without it
        if (checkPermission('CONFIG_AUTH_PROVIDER_ACCESS')) {
            try {
                const providersResponse = await getAllAuthProviders({ search: '' })
                authProviders.value = ((providersResponse as ListResponse).data?.items || []) as AuthProviderEntity[]
            } catch (error) {
                console.error('Error loading auth providers:', error)
            }
        }
    }

    const handleResetMfa = async (): Promise<void> => {
        if (!localItem.value.id || !resetMfaChoice.value) {
            return
        }
        const reset_totp = resetMfaChoice.value === 'totp' || resetMfaChoice.value === 'both'
        const reset_passkeys = resetMfaChoice.value === 'passkeys' || resetMfaChoice.value === 'both'
        try {
            await resetUserMfa(localItem.value.id, { reset_totp, reset_passkeys })
            // Reflect the reset in the local state so the Reset MFA button hides when nothing is left.
            if (reset_totp) {
                userMfa.value = { ...userMfa.value, totp: false }
            }
            if (reset_passkeys) {
                userMfa.value = { ...userMfa.value, passkeys: 0 }
            }
            window.dispatchEvent(new CustomEvent('notification', { detail: { type: 'success', loc: 'common.updated_successfully' } }))
        } catch (error) {
            console.error('Error resetting MFA:', error)
            window.dispatchEvent(new CustomEvent('notification', { detail: { type: 'error', loc: 'common.error_saving' } }))
        } finally {
            resetMfaChoice.value = ''
            resetMfaDialog.value = false
        }
    }

    const resetForm = (): void => {
        localItem.value = { ...defaultItem }
        password.value = ''
        passwordConfirm.value = ''
        email.value = ''
        status.value = 'active'
        clearPassword.value = false
        identities.value = []
        hasStoredPassword.value = false
        userMfa.value = {}
        resetMfaChoice.value = ''
        selectedOrganizations.value = []
        selectedRoles.value = []
        selectedPermissions.value = []
        showValidationError.value = false
        showError.value = false
        errorMessage.value = ''
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
        errorMessage.value = ''

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
                email: email.value || null,
                status: status.value,
                organizations: selectedOrganizations.value.map((id) => ({ id })),
                roles: selectedRoles.value.map((id) => ({ id })),
                permissions: selectedPermissions.value.map((id) => ({ id })),
                identities: identities.value
                    .filter((identity) => identity.auth_provider_id && identity.external_username)
                    .map((identity) => ({
                        auth_provider_id: identity.auth_provider_id,
                        external_username: identity.external_username
                    }))
            }

            // Add password if provided
            if (password.value) {
                payload['password'] = password.value
            } else if (isEdit.value && clearPassword.value) {
                payload['clear_password'] = true
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
            errorMessage.value = (error as { response?: { data?: { error?: string } } })?.response?.data?.error || ''
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
            email: email.value,
            status: status.value,
            clearPassword: clearPassword.value,
            identities: identities.value,
            organizations: selectedOrganizations.value,
            roles: selectedRoles.value,
            permissions: selectedPermissions.value
        }),
        save: persist,
        close: closeDialog
    })
</script>
