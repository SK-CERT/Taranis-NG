<template>
    <v-dialog
        v-model="dialog"
        max-width="600"
        persistent
        scrollable
    >
        <template #activator="{ props: activatorProps }">
            <AddNewButton
                :show="canCreate"
                v-bind="activatorProps"
            />
        </template>

        <v-card>
            <DialogToolbar
                :title="isEdit ? t(`${config.i18nPrefix}.edit`) : t(`${config.i18nPrefix}.add_new`)"
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
                        :label="t(`${config.i18nPrefix}.name`)"
                        variant="outlined"
                        density="comfortable"
                        class="mb-3"
                        :rules="[(v) => !!v || t('error.required')]"
                        :disabled="saving"
                    />

                    <v-textarea
                        v-model="localItem.description"
                        :label="t(`${config.i18nPrefix}.description`)"
                        variant="outlined"
                        density="comfortable"
                        rows="3"
                        class="mb-3"
                        :disabled="saving"
                    />

                    <v-text-field
                        v-model="localItem.api_url"
                        :label="t(`${config.i18nPrefix}.api_url`)"
                        variant="outlined"
                        density="comfortable"
                        class="mb-3"
                        :rules="[(v) => !!v || t('error.required')]"
                        :disabled="saving"
                    />

                    <v-text-field
                        v-model="localItem.api_key"
                        :label="t(`${config.i18nPrefix}.api_key`)"
                        variant="outlined"
                        density="comfortable"
                        :type="showApiKey ? 'text' : 'password'"
                        :rules="config.apiKeyRequired ? [(v) => !!v || t('error.required')] : []"
                        :append-inner-icon="showApiKey ? 'mdi-eye-off' : 'mdi-eye'"
                        :disabled="saving"
                        @click:append-inner="showApiKey = !showApiKey"
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
                    {{ t(`${config.i18nPrefix}.error`) }}
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
    import type { PermissionKey } from '@/types/permissions'
    import { NODE_TYPES, type NodeType } from './nodeTypes'

    type NodeItem = {
        id: string | number | null
        name: string
        description: string
        api_url: string
        api_key: string
        [key: string]: unknown
    }

    type FormValidationResult = {
        valid: boolean
    }

    const props = withDefaults(
        defineProps<{
            type: NodeType
            editItem?: Partial<NodeItem> | null
        }>(),
        {
            editItem: null
        }
    )

    const emit = defineEmits<{
        (e: 'saved'): void
    }>()

    const { t } = useI18n()
    const { checkPermission } = useAuth()

    const config = computed(() => NODE_TYPES[props.type])

    const formRef = ref<any>(null)
    const showValidationError = ref(false)
    const showError = ref(false)
    const saving = ref(false)
    const dialog = ref(false)
    const showApiKey = ref(false)

    const defaultItem: NodeItem = {
        // Empty string (not null): the backend requires a string id even on create (it is ignored
        // and replaced by a generated UUID), and a null id fails schema validation.
        id: '',
        name: '',
        description: '',
        api_url: '',
        api_key: ''
    }

    const localItem = ref<NodeItem>({ ...defaultItem })
    const isEdit = computed(() => !!localItem.value.id)

    const canCreate = computed(() => checkPermission(`${config.value.permissionPrefix}_CREATE` as PermissionKey))

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
                await config.value.updateFn(localItem.value)
            } else {
                await config.value.createFn(localItem.value)
            }
            window.dispatchEvent(
                new CustomEvent('notification', {
                    detail: { type: 'success', loc: isEdit.value ? 'common.updated_successfully' : 'common.created_successfully' }
                })
            )
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
        showApiKey.value = false
        formRef.value?.reset()
        localItem.value = { ...defaultItem }
        dialog.value = false
    }

    watch(
        () => props.editItem,
        (newItem) => {
            if (newItem && Object.keys(newItem).length > 0) {
                localItem.value = { ...defaultItem, ...newItem }
                dialog.value = true
            } else {
                localItem.value = { ...defaultItem }
            }
        },
        { immediate: true, deep: true }
    )

    watch(
        () => dialog.value,
        (newVal: boolean) => {
            if (!newVal) {
                showValidationError.value = false
                showError.value = false
                showApiKey.value = false
                saving.value = false
            }
        }
    )
</script>
