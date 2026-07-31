<template>
    <v-dialog
        v-model="dialog"
        max-width="800"
        persistent
        scrollable
        @keydown.esc="requestClose"
    >
        <template #activator="{ props: activatorProps }">
            <AddNewButton
                :show="canCreate"
                v-bind="activatorProps"
                @click="openCreateDialog"
            />
        </template>

        <v-card>
            <DialogToolbar
                :title="isEdit ? t('publishers.presets.edit') : t('publishers.presets.add_new')"
                :saving="saving"
                :save-disabled="!selectedPublisher"
                @cancel="requestClose"
                @save="saveAndClose"
            />

            <v-card-text>
                <v-form
                    ref="formRef"
                    @submit.prevent="saveAndClose"
                >
                    <v-select
                        v-model="selectedNode"
                        :items="nodes"
                        item-title="name"
                        item-value="id"
                        return-object
                        :label="t('publishers.presets.node')"
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
                        :label="t('publishers.presets.publisher')"
                        variant="outlined"
                        density="comfortable"
                        class="mb-3"
                        :disabled="isEdit || saving"
                        :rules="[(v) => !!v || t('error.required')]"
                    />

                    <v-text-field
                        v-if="selectedPublisher"
                        v-model="localItem.name"
                        :label="t('publishers.presets.name')"
                        variant="outlined"
                        density="comfortable"
                        class="mb-3"
                        :rules="[(v) => !!v || t('error.required')]"
                        :disabled="saving"
                    />

                    <v-textarea
                        v-if="selectedPublisher"
                        v-model="localItem.description"
                        :label="t('publishers.presets.description')"
                        variant="outlined"
                        density="comfortable"
                        rows="3"
                        class="mb-3"
                        :disabled="saving"
                    />

                    <v-checkbox
                        v-if="selectedPublisher"
                        v-model="localItem.use_for_notifications"
                        :label="t('publishers.presets.use_for_notifications')"
                        color="primary"
                        density="comfortable"
                        class="mb-3"
                        :disabled="saving"
                    />

                    <!-- Dynamic Parameter Fields -->
                    <div v-if="selectedPublisher && selectedPublisher.parameters && selectedPublisher.parameters.length > 0">
                        <v-divider class="my-4" />
                        <h3 class="text-subtitle-1 mb-3">
                            {{ t('publishers.presets.parameters') }}
                        </h3>

                        <div
                            v-for="(param, index) in selectedPublisher.parameters"
                            :key="param.key || index"
                            class="mb-3"
                        >
                            <v-text-field
                                v-model="parameterValues[index]"
                                :label="param.name"
                                :type="param.key && param.key.includes('PASSWORD') ? 'password' : 'text'"
                                variant="outlined"
                                density="comfortable"
                                :disabled="saving"
                                :placeholder="param.default_value"
                            >
                                <template
                                    v-if="param.description"
                                    #append-inner
                                >
                                    <v-icon
                                        color="primary"
                                        :title="param.description"
                                        >mdi-help-circle</v-icon
                                    >
                                </template>
                            </v-text-field>
                        </div>
                    </div>

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
                        {{ t('publishers.presets.error') }}
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
    import AddNewButton from '@/components/common/buttons/AddNewButton.vue'
    import DialogToolbar from '@/components/common/dialogs/DialogToolbar.vue'
    import UnsavedChangesDialog from '@/components/common/dialogs/UnsavedChangesDialog.vue'
    import { useUnsavedChanges } from '@/composables/useUnsavedChanges'
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
        // Empty string (not null): backend requires a string id even on create (ignored), null fails validation.
        id: '',
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
        } else {
            // Snapshot the freshly-loaded form as the clean baseline for dirty-tracking.
            capture()
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

    const openCreateDialog = (): void => {
        localItem.value = { ...defaultItem }
        showValidationError.value = false
        showError.value = false

        // Re-select the first node/publisher on every open. resetForm() (called on close) nulls
        // these, so without re-seeding here the second+ open shows ONLY the Publishers Node field
        // (the publisher select / parameter fields are gated behind v-if="selectedNode/selectedPublisher").
        selectedNode.value = nodes.value[0] ?? null
        selectedPublisher.value = selectedNode.value?.publishers?.[0] ?? null
        // Initialize parameter values synchronously from the freshly-selected publisher's defaults
        // rather than in the deferred selectedPublisher watcher. The watcher is queued AFTER the
        // dialog watcher (which calls capture() to snapshot the dirty-tracking baseline) because
        // dialog=true is mutated first, so leaving this to the async watcher would snapshot
        // params:[] while the live state becomes the publisher's defaults — every subsequent
        // create-open would spuriously report unsaved changes.
        parameterValues.value = selectedPublisher.value?.parameters?.map((param) => String(param.default_value ?? '')) || []
    }

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

    const closeDialog = (): void => {
        dialog.value = false
    }

    // Persists the form. Returns true on success so the guard can decide whether to close.
    const persist = async (): Promise<boolean> => {
        showValidationError.value = false
        showError.value = false

        if (!formRef.value?.validate) {
            return false
        }
        const { valid } = (await formRef.value.validate()) as FormValidationResult

        if (!valid || !selectedPublisher.value) {
            showValidationError.value = true
            return false
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
        getState: () => ({ item: localItem.value, publisher: selectedPublisher.value?.id ?? null, params: parameterValues.value }),
        save: persist,
        close: closeDialog
    })
</script>
