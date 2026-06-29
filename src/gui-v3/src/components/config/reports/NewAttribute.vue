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
                :title="isEdit ? t('reports.attributes.edit') : t('reports.attributes.add_new')"
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
                        :label="t('reports.attributes.name')"
                        variant="outlined"
                        density="comfortable"
                        class="mb-3"
                        :rules="[(v) => !!v || t('error.required')]"
                        :disabled="saving"
                    />

                    <v-textarea
                        v-model="localItem.description"
                        :label="t('reports.attributes.description')"
                        variant="outlined"
                        density="comfortable"
                        rows="3"
                        class="mb-3"
                        :disabled="saving"
                    />

                    <v-select
                        v-model="localItem.type"
                        :label="t('reports.attributes.type')"
                        :items="attributeTypes"
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
                    {{ t('reports.attributes.error') }}
                </v-alert>
            </v-card-text>
        </v-card>
    </v-dialog>
</template>

<script setup lang="ts">
    import { ref, computed, watch } from 'vue'
    import { useI18n } from 'vue-i18n'
    import { useAuth } from '@/composables/useAuth'
    import { createNewAttribute, updateAttribute } from '@/api/config'
    import AddNewButton from '@/components/common/buttons/AddNewButton.vue'
    import DialogToolbar from '@/components/common/dialogs/DialogToolbar.vue'

    type AttributeType = 'STRING' | 'NUMBER' | 'BOOLEAN' | 'DATE' | 'DATETIME' | 'TEXT' | 'ENUM'

    type AttributeItem = {
        id: string | number | null
        name: string
        description: string
        type: AttributeType
        [key: string]: unknown
    }

    type AttributeTypeItem = {
        title: AttributeType
        value: AttributeType
    }

    type FormValidationResult = {
        valid: boolean
    }

    const props = withDefaults(
        defineProps<{
            editItem?: Record<string, unknown> | null
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

    const formRef = ref<any>(null)
    const showValidationError = ref(false)
    const showError = ref(false)
    const saving = ref(false)
    const dialog = ref(false)

    const attributeTypes: AttributeTypeItem[] = [
        { title: 'STRING', value: 'STRING' },
        { title: 'NUMBER', value: 'NUMBER' },
        { title: 'BOOLEAN', value: 'BOOLEAN' },
        { title: 'DATE', value: 'DATE' },
        { title: 'DATETIME', value: 'DATETIME' },
        { title: 'TEXT', value: 'TEXT' },
        { title: 'ENUM', value: 'ENUM' }
    ]

    const defaultItem: AttributeItem = {
        id: null,
        name: '',
        description: '',
        type: 'STRING'
    }

    const localItem = ref<AttributeItem>({ ...defaultItem })
    const isEdit = computed(() => !!localItem.value.id)

    const canCreate = computed(() => checkPermission('CONFIG_ATTRIBUTE_CREATE'))

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
                await updateAttribute(localItem.value)
            } else {
                // Backend requires an integer id even on create (ignored); null fails validation.
                await createNewAttribute({ ...localItem.value, id: -1 })
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
    }

    watch(
        () => props.editItem,
        (newItem) => {
            if (newItem && Object.keys(newItem).length > 0) {
                const incoming = newItem as Partial<AttributeItem>
                localItem.value = { ...defaultItem, ...incoming }
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
                saving.value = false
            }
        }
    )
</script>
