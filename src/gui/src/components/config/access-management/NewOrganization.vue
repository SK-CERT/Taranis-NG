<template>
    <v-dialog
        v-model="dialog"
        max-width="600"
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
                :title="isEdit ? t('access_management.organizations.edit') : t('access_management.organizations.add_new')"
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
                        :label="t('access_management.organizations.name')"
                        variant="outlined"
                        density="comfortable"
                        class="mb-3"
                        :rules="[(v) => !!v || t('error.required')]"
                        :disabled="saving"
                    />

                    <v-textarea
                        v-model="localItem.description"
                        :label="t('access_management.organizations.description')"
                        variant="outlined"
                        density="comfortable"
                        rows="3"
                        :disabled="saving"
                    />

                    <v-text-field
                        v-model="localItem.street"
                        :label="t('access_management.organizations.street')"
                        variant="outlined"
                        density="comfortable"
                        class="mb-3"
                        :disabled="saving"
                    />

                    <v-text-field
                        v-model="localItem.city"
                        :label="t('access_management.organizations.city')"
                        variant="outlined"
                        density="comfortable"
                        class="mb-3"
                        :disabled="saving"
                    />

                    <v-text-field
                        v-model="localItem.zip"
                        :label="t('access_management.organizations.zip')"
                        variant="outlined"
                        density="comfortable"
                        class="mb-3"
                        :disabled="saving"
                    />

                    <v-text-field
                        v-model="localItem.country"
                        :label="t('access_management.organizations.country')"
                        variant="outlined"
                        density="comfortable"
                        :disabled="saving"
                    />

                    <v-switch
                        v-model="localItem.require_mfa"
                        :label="t('access_management.organizations.require_mfa')"
                        :hint="t('access_management.organizations.require_mfa_hint')"
                        persistent-hint
                        color="primary"
                        :disabled="saving"
                        data-test="organization-require-mfa"
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
                    {{ t('access_management.organizations.error') }}
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
    import { ref, computed, watch } from 'vue'
    import { useI18n } from 'vue-i18n'
    import { useAuth } from '@/composables/useAuth'
    import AddNewButton from '@/components/common/buttons/AddNewButton.vue'
    import DialogToolbar from '@/components/common/dialogs/DialogToolbar.vue'
    import UnsavedChangesDialog from '@/components/common/dialogs/UnsavedChangesDialog.vue'
    import { useUnsavedChanges } from '@/composables/useUnsavedChanges'
    import { createNewOrganization, updateOrganization } from '@/api/config'

    type OrganizationItem = {
        id: string | number | null
        name: string
        description: string
        require_mfa: boolean
        street: string
        city: string
        zip: string
        country: string
        [key: string]: unknown
    }

    type FormValidationResult = {
        valid: boolean
    }

    const props = withDefaults(
        defineProps<{
            modelValue?: boolean
            editItem?: Partial<OrganizationItem> | null
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

    const defaultItem: OrganizationItem = {
        id: null,
        name: '',
        description: '',
        require_mfa: false,
        street: '',
        city: '',
        zip: '',
        country: ''
    }

    const localItem = ref<OrganizationItem>({ ...defaultItem })

    const isEdit = computed(() => !!localItem.value.id)
    const canCreate = computed(() => checkPermission('CONFIG_ORGANIZATION_CREATE'))

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
            // The backend expects the address as a nested object and a (non-null) integer id;
            // the id is ignored on create, so -1 is used as the "new" sentinel.
            const payload = {
                id: isEdit.value ? localItem.value.id : -1,
                name: localItem.value.name,
                description: localItem.value.description,
                require_mfa: localItem.value.require_mfa,
                address: {
                    street: localItem.value.street,
                    city: localItem.value.city,
                    zip: localItem.value.zip,
                    country: localItem.value.country
                }
            }

            if (isEdit.value) {
                await updateOrganization(payload)
            } else {
                await createNewOrganization(payload)
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
        dialog.value = false
    }

    const { confirmVisible, capture, requestClose, continueEditing, saveAndClose, discardAndClose } = useUnsavedChanges({
        getState: () => localItem.value,
        save: persist,
        close: closeDialog
    })

    watch(
        () => props.editItem,
        (newItem) => {
            if (newItem && Object.keys(newItem).length > 0) {
                // The backend returns the address as a nested object; flatten it into the form fields.
                const address = (newItem as { address?: { street?: string; city?: string; zip?: string; country?: string } }).address
                localItem.value = {
                    ...defaultItem,
                    ...newItem,
                    street: address?.street ?? '',
                    city: address?.city ?? '',
                    zip: address?.zip ?? '',
                    country: address?.country ?? ''
                }
                // Opening the dialog automatically when an item to edit is provided.
                dialog.value = true
            } else {
                localItem.value = { ...defaultItem }
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
            } else {
                // Snapshot the freshly-loaded form as the clean baseline for dirty-tracking.
                capture()
            }
            emit('update:modelValue', newVal)
        }
    )
</script>
