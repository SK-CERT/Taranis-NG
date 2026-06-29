<template>
    <v-dialog
        v-model="dialog"
        max-width="600"
        persistent
    >
        <template #activator="{ props: activatorProps }">
            <AddNewButton
                :show="canCreate"
                v-bind="activatorProps"
            />
        </template>

        <v-card>
            <DialogToolbar
                :title="isEdit ? t('data_providers.ai.edit') : t('data_providers.ai.add_new')"
                :saving="saving"
                @cancel="handleCancel"
                @save="handleSubmit"
            />

            <v-card-text>
                <v-form
                    ref="formRef"
                    @submit.prevent="handleSubmit"
                >
                    <v-text-field
                        v-model="localItem.name"
                        :label="t('data_providers.ai.name')"
                        variant="outlined"
                        density="comfortable"
                        class="mb-3"
                        :rules="[(v) => !!v || t('error.required')]"
                        :disabled="saving"
                    />

                    <v-select
                        v-model="localItem.api_type"
                        :label="t('data_providers.ai.api_type')"
                        :items="['openai']"
                        variant="outlined"
                        density="comfortable"
                        class="mb-3"
                        :rules="[(v) => !!v || t('error.required')]"
                        :disabled="saving"
                    />

                    <v-text-field
                        v-model="localItem.api_url"
                        :label="t('data_providers.ai.api_url')"
                        variant="outlined"
                        density="comfortable"
                        class="mb-3"
                        :rules="[(v) => !!v || t('error.required')]"
                        :disabled="saving"
                    />

                    <v-text-field
                        v-model="localItem.api_key"
                        :label="t('settings.api_key')"
                        variant="outlined"
                        density="comfortable"
                        :type="showApiKey ? 'text' : 'password'"
                        class="mb-3"
                        :append-inner-icon="showApiKey ? 'mdi-eye-off' : 'mdi-eye'"
                        :rules="[(v) => !!v || t('error.required')]"
                        :disabled="saving"
                        @click:append-inner="showApiKey = !showApiKey"
                    />

                    <v-text-field
                        v-model="localItem.model"
                        :label="t('data_providers.ai.model')"
                        variant="outlined"
                        density="comfortable"
                        :rules="[(v) => !!v || t('error.required')]"
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
                    {{ t('data_providers.ai.error') }}
                </v-alert>
            </v-card-text>
        </v-card>
    </v-dialog>
</template>

<script setup lang="ts">
    import { ref, computed, watch } from 'vue'
    import { useI18n } from 'vue-i18n'
    import AddNewButton from '@/components/common/buttons/AddNewButton.vue'
    import DialogToolbar from '@/components/common/dialogs/DialogToolbar.vue'
    import { useAuth } from '@/composables/useAuth'
    import { createNewAiProvider, updateAiProvider } from '@/api/config'

    type AiProviderItem = {
        id: string | number | null
        name: string
        api_type: string
        api_url: string
        api_key: string
        model: string
        [key: string]: unknown
    }

    type FormValidationResult = {
        valid: boolean
    }

    const props = withDefaults(
        defineProps<{
            editItem?: Partial<AiProviderItem> | null
        }>(),
        {
            editItem: null
        }
    )

    const emit = defineEmits(['saved'])

    const { t } = useI18n()
    const { checkPermission } = useAuth()

    const formRef = ref<any>(null)
    const showValidationError = ref(false)
    const showError = ref(false)
    const saving = ref(false)
    const dialog = ref(false)
    const showApiKey = ref(false)

    const defaultItem: AiProviderItem = {
        id: null,
        name: '',
        api_type: 'openai',
        api_url: '',
        api_key: '',
        model: ''
    }

    const localItem = ref<AiProviderItem>({ ...defaultItem })

    const isEdit = computed(() => !!localItem.value.id)
    const canCreate = computed(() => checkPermission('CONFIG_AI_CREATE'))

    async function handleSubmit(): Promise<void> {
        showValidationError.value = false
        showError.value = false

        const { valid } = (await formRef.value.validate()) as FormValidationResult
        if (!valid) {
            showValidationError.value = true
            return
        }

        saving.value = true
        try {
            if (isEdit.value) {
                await updateAiProvider(localItem.value)
            } else {
                // Backend create schema has no id field for the constructor; omit it (null fails validation).
                const payload: Record<string, unknown> = { ...localItem.value }
                delete payload['id']
                await createNewAiProvider(payload)
            }
            emit('saved')
            handleCancel()
        } catch (error) {
            window.dispatchEvent(
                new CustomEvent('notification', {
                    detail: { type: 'error', loc: 'common.error_saving' }
                })
            )
            showError.value = true
        } finally {
            saving.value = false
        }
    }

    function handleCancel(): void {
        showValidationError.value = false
        showError.value = false
        formRef.value?.reset()
        localItem.value = { ...defaultItem }
        dialog.value = false
        showApiKey.value = false
    }

    watch(
        () => props.editItem,
        (newItem) => {
            if (newItem && Object.keys(newItem).length > 0) {
                localItem.value = { ...defaultItem, ...newItem }
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
            }
        }
    )
</script>
