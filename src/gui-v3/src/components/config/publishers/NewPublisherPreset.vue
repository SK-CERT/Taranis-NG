<template>
    <v-dialog v-model="dialog" max-width="800" persistent scrollable>
        <template #activator="{ props: activatorProps }">
            <v-btn v-if="canCreate" v-bind="activatorProps" color="primary" prepend-icon="mdi-plus">
                {{ t('common.add_btn') }}
            </v-btn>
        </template>

        <v-card>
            <v-card-title>
                <span class="text-h5">
                    {{ isEdit ? t('publisher_preset.edit') : t('publisher_preset.add_new') }}
                </span>
            </v-card-title>

            <v-card-text>
                <v-form ref="formRef" @submit.prevent="handleSubmit">
                    <v-select
                        v-model="selectedNode"
                        :items="nodes"
                        item-title="name"
                        item-value="id"
                        return-object
                        :label="t('publisher_preset.node')"
                        variant="outlined"
                        density="comfortable"
                        class="mb-3"
                        :disabled="isEdit || saving || loadingNodes"
                        :loading="loadingNodes"
                        :rules="[(v) => !!v || t('error.required')]"
                    />

                    <v-select
                        v-if="selectedNode"
                        v-model="selectedPublisher"
                        :items="selectedNode.publishers || []"
                        item-title="name"
                        item-value="id"
                        return-object
                        :label="t('publisher_preset.publisher')"
                        variant="outlined"
                        density="comfortable"
                        class="mb-3"
                        :disabled="isEdit || saving"
                        :rules="[(v) => !!v || t('error.required')]"
                    />

                    <v-text-field
                        v-if="selectedPublisher"
                        v-model="localItem.name"
                        :label="t('publisher_preset.name')"
                        variant="outlined"
                        density="comfortable"
                        class="mb-3"
                        :rules="[(v) => !!v || t('error.required')]"
                        :disabled="saving"
                    />

                    <v-textarea
                        v-if="selectedPublisher"
                        v-model="localItem.description"
                        :label="t('publisher_preset.description')"
                        variant="outlined"
                        density="comfortable"
                        rows="3"
                        class="mb-3"
                        :disabled="saving"
                    />

                    <v-checkbox
                        v-if="selectedPublisher"
                        v-model="localItem.use_for_notifications"
                        :label="t('publisher_preset.use_for_notifications')"
                        color="primary"
                        density="comfortable"
                        class="mb-3"
                        :disabled="saving"
                    />

                    <!-- Dynamic Parameter Fields -->
                    <div v-if="selectedPublisher && selectedPublisher.parameters && selectedPublisher.parameters.length > 0">
                        <v-divider class="my-4" />
                        <h3 class="text-subtitle-1 mb-3">
                            {{ t('publisher_preset.parameters') }}
                        </h3>

                        <div v-for="(param, index) in selectedPublisher.parameters" :key="param.key || index" class="mb-3">
                            <v-row align="center">
                                <v-col cols="11">
                                    <v-text-field
                                        v-model="parameterValues[index]"
                                        :label="param.name"
                                        :type="param.key && param.key.includes('PASSWORD') ? 'password' : 'text'"
                                        variant="outlined"
                                        density="comfortable"
                                        :disabled="saving"
                                        :placeholder="param.default_value"
                                    />
                                </v-col>
                                <v-col cols="1">
                                    <v-tooltip location="top">
                                        <template #activator="{ props }">
                                            <v-icon v-bind="props" color="primary">mdi-help-circle</v-icon>
                                        </template>
                                        <span>{{ param.description }}</span>
                                    </v-tooltip>
                                </v-col>
                            </v-row>
                        </div>
                    </div>

                    <v-alert v-if="showValidationError" type="error" density="compact" class="mb-3">
                        {{ t('error.validation') }}
                    </v-alert>

                    <v-alert v-if="showError" type="error" density="compact" class="mb-3">
                        {{ t('publisher_preset.error') }}
                    </v-alert>
                </v-form>
            </v-card-text>

            <v-card-actions>
                <v-spacer />
                <v-btn color="grey" variant="text" :disabled="saving" @click="cancel">
                    {{ t('common.cancel') }}
                </v-btn>
                <v-btn color="primary" variant="text" :loading="saving" :disabled="saving || !selectedPublisher" @click="handleSubmit">
                    <v-icon start>mdi-content-save</v-icon>
                    {{ t('common.save') }}
                </v-btn>
            </v-card-actions>
        </v-card>
    </v-dialog>
</template>

<script setup lang="ts">
    import { ref, computed, watch, onMounted } from 'vue'
    import { useI18n } from 'vue-i18n'
    import AddNewButton from '@/components/common/buttons/AddNewButton.vue'
    import { useAuth } from '@/composables/useAuth'
    import { createNewPublisherPreset, updatePublisherPreset, getAllPublishersNodes } from '@/api/config'

    type PresetParameter = {
        id?: string | number
        key?: string
        name?: string
        description?: string
        default_value?: string
        [key: string]: unknown
    }

    type Publisher = {
        id: string | number
        name?: string
        parameters?: PresetParameter[]
        [key: string]: unknown
    }

    type PublishersNode = {
        id: string | number
        name?: string
        publishers?: Publisher[]
        [key: string]: unknown
    }

    type PublisherPresetParameterValue = {
        value?: string
        parameter?: PresetParameter
        [key: string]: unknown
    }

    type PublisherPresetItem = {
        id: string | number | null
        name: string
        description: string
        use_for_notifications: boolean
        publisher_id: string | number | null
        parameter_values: PublisherPresetParameterValue[]
        [key: string]: unknown
    }

    type FormValidationResult = {
        valid: boolean
    }

    const props = withDefaults(
        defineProps<{
            modelValue?: boolean
            editItem?: Record<string, unknown> | null
        }>(),
        {
            modelValue: false,
            editItem: null
        }
    )

    const emit = defineEmits<{
        (e: 'update:modelValue', value: boolean): void
        (e: 'saved'): void
    }>()

    const { t } = useI18n()
    const { checkPermission } = useAuth()

    const dialog = ref(false)
    const formRef = ref<any>(null)
    const saving = ref(false)
    const loadingNodes = ref(false)
    const showValidationError = ref(false)
    const showError = ref(false)

    const nodes = ref<PublishersNode[]>([])
    const selectedNode = ref<PublishersNode | null>(null)
    const selectedPublisher = ref<Publisher | null>(null)
    const parameterValues = ref<string[]>([])

    const defaultItem: PublisherPresetItem = {
        id: null,
        name: '',
        description: '',
        use_for_notifications: false,
        publisher_id: null,
        parameter_values: []
    }

    const localItem = ref<PublisherPresetItem>({ ...defaultItem })

    const isEdit = computed(() => !!localItem.value.id)
    const canCreate = computed(() => checkPermission('CONFIG_PUBLISHER_PRESET_CREATE'))

    // Watch for edit item changes
    watch(
        () => props.editItem,
        (newVal) => {
            if (newVal) {
                const incoming = newVal as Partial<PublisherPresetItem> & {
                    publisher_id?: string | number | null
                    parameter_values?: PublisherPresetParameterValue[]
                }

                localItem.value = { ...defaultItem, ...incoming }

                // Find and set the node and publisher
                for (const node of nodes.value) {
                    const publisher = node.publishers?.find((p) => p.id === incoming.publisher_id)
                    if (publisher) {
                        selectedNode.value = node
                        selectedPublisher.value = publisher as Publisher

                        // Map parameter values
                        parameterValues.value =
                            publisher.parameters?.map((param) => {
                                const paramValue = incoming.parameter_values?.find((pv) => pv.parameter?.id === param.id)
                                return String(paramValue?.value ?? param.default_value ?? '')
                            }) || []
                        break
                    }
                }

                dialog.value = true
            }
        },
        { immediate: true, deep: true }
    )

    // Watch dialog state
    watch(dialog, (newVal) => {
        if (!newVal) {
            resetForm()
        }
        emit('update:modelValue', newVal)
    })

    // Watch selected publisher to initialize parameter values
    watch(selectedPublisher, (newPublisher: Publisher | null) => {
        if (!isEdit.value && newPublisher && newPublisher.parameters) {
            parameterValues.value = newPublisher.parameters.map((param) => String(param.default_value ?? ''))
        }
    })

    // Load publishers nodes on mount
    onMounted(async () => {
        await loadNodes()
    })

    const loadNodes = async (): Promise<void> => {
        loadingNodes.value = true
        try {
            const response = (await getAllPublishersNodes({ search: '' })) as {
                items?: PublishersNode[]
                data?: { items?: PublishersNode[] }
            }
            nodes.value = response.items || response.data?.items || []

            // Auto-select first node and publisher if available
            if (!isEdit.value && nodes.value.length > 0) {
                const firstNode = nodes.value[0]
                if (!firstNode) {
                    return
                }
                selectedNode.value = firstNode
                const publishers = firstNode.publishers ?? []
                if (publishers.length > 0) {
                    selectedPublisher.value = publishers[0] as Publisher
                }
            }
        } catch (error) {
            console.error('Error loading publishers nodes:', error)
        } finally {
            loadingNodes.value = false
        }
    }

    const resetForm = (): void => {
        localItem.value = { ...defaultItem }
        selectedNode.value = null
        selectedPublisher.value = null
        parameterValues.value = []
        showValidationError.value = false
        showError.value = false
        if (formRef.value?.resetValidation) {
            formRef.value.resetValidation()
        }
    }

    const cancel = (): void => {
        dialog.value = false
    }

    const handleSubmit = async (): Promise<void> => {
        showValidationError.value = false
        showError.value = false

        if (!formRef.value?.validate) {
            return
        }
        const { valid } = (await formRef.value.validate()) as FormValidationResult

        if (!valid || !selectedPublisher.value) {
            showValidationError.value = true
            return
        }

        saving.value = true

        try {
            // Prepare parameter values
            const paramValues =
                selectedPublisher.value.parameters?.map((param, index) => ({
                    value: String(parameterValues.value[index] ?? param.default_value ?? ''),
                    parameter: param
                })) || []

            const payload: PublisherPresetItem = {
                ...localItem.value,
                publisher_id: selectedPublisher.value.id,
                parameter_values: paramValues
            }

            if (isEdit.value) {
                await updatePublisherPreset(payload)
                window.dispatchEvent(
                    new CustomEvent('notification', {
                        detail: { type: 'success', loc: 'common.updated_successfully' }
                    })
                )
            } else {
                await createNewPublisherPreset(payload)
                window.dispatchEvent(
                    new CustomEvent('notification', {
                        detail: { type: 'success', loc: 'common.created_successfully' }
                    })
                )
            }

            dialog.value = false
            emit('saved')
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
</script>
