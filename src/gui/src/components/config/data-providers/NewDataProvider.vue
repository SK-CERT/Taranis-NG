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
                :title="isEdit ? t('data_providers.data.edit') : t('data_providers.data.add_new')"
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
                        :label="t('data_providers.data.name')"
                        variant="outlined"
                        density="comfortable"
                        class="mb-3"
                        :rules="[(v) => !!v || t('error.required')]"
                        :disabled="saving"
                    />

                    <v-select
                        v-model="localItem.api_type"
                        :label="t('data_providers.data.api_type')"
                        :items="['CVE', 'CWE', 'CPE', 'EUVD', 'EPSS']"
                        variant="outlined"
                        density="comfortable"
                        class="mb-3"
                        :rules="[(v) => !!v || t('error.required')]"
                        :disabled="saving"
                    />

                    <v-text-field
                        v-model="localItem.api_url"
                        :label="t('data_providers.data.api_url')"
                        variant="outlined"
                        density="comfortable"
                        class="mb-3"
                        :rules="[(v) => !!v || t('error.required')]"
                        :disabled="saving"
                    />

                    <v-row class="mb-2">
                        <v-col cols="6">
                            <v-text-field
                                v-model="localItem.api_key"
                                :label="t('settings.api_key')"
                                variant="outlined"
                                density="comfortable"
                                :type="showApiKey ? 'text' : 'password'"
                                :append-inner-icon="showApiKey ? 'mdi-eye-off' : 'mdi-eye'"
                                :disabled="saving"
                                @click:append-inner="showApiKey = !showApiKey"
                            />
                        </v-col>
                        <v-col cols="6">
                            <v-text-field
                                v-model="localItem.user_agent"
                                :label="t('data_providers.data.user_agent')"
                                variant="outlined"
                                density="comfortable"
                                :disabled="saving"
                            />
                        </v-col>
                    </v-row>

                    <v-text-field
                        v-model="localItem.web_url"
                        :label="t('data_providers.data.web_url')"
                        variant="outlined"
                        density="comfortable"
                        class="mb-3"
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
                    {{ t('data_providers.data.error') }}
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
    import AddNewButton from '@/components/common/buttons/AddNewButton.vue'
    import DialogToolbar from '@/components/common/dialogs/DialogToolbar.vue'
    import UnsavedChangesDialog from '@/components/common/dialogs/UnsavedChangesDialog.vue'
    import { useAuth } from '@/composables/useAuth'
    import { useUnsavedChanges } from '@/composables/useUnsavedChanges'
    import { createNewDataProvider, updateDataProvider } from '@/api/config'

    type DataProviderItem = {
        id: string | number | null
        name: string
        api_type: string
        api_url: string
        api_key: string
        user_agent: string
        web_url: string
        [key: string]: unknown
    }

    type FormValidationResult = {
        valid: boolean
    }

    const props = withDefaults(
        defineProps<{
            editItem?: Partial<DataProviderItem> | null
        }>(),
        {
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
    const showApiKey = ref(false)

    const defaultItem: DataProviderItem = {
        id: null,
        name: 'ENISA EUVD',
        api_type: 'EUVD',
        api_url: 'https://euvdservices.enisa.europa.eu/api/',
        api_key: '',
        user_agent: '',
        web_url: ''
    }

    const localItem = ref<DataProviderItem>({ ...defaultItem })

    const canCreate = computed(() => checkPermission('CONFIG_DATA_PROVIDER_CREATE'))
    const isEdit = computed(() => !!localItem.value.id)

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
            if (isEdit.value) {
                await updateDataProvider(localItem.value)
            } else {
                // Backend create schema has no id field for the constructor; omit it (null fails validation).
                const payload: Record<string, unknown> = { ...localItem.value }
                delete payload['id']
                await createNewDataProvider(payload)
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
        showApiKey.value = false
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
                localItem.value = { ...defaultItem, ...newItem }
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
                showApiKey.value = false
            } else {
                // Snapshot the freshly-loaded form as the clean baseline for dirty-tracking.
                capture()
            }
            emit('update:modelValue', newVal)
        }
    )
</script>
