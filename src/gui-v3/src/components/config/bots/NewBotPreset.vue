<template>
    <v-dialog v-model="dialog" max-width="800" persistent scrollable>
        <template #activator="{ props: activatorProps }">
            <AddNewButton :show="canCreate" v-bind="activatorProps" />
        </template>

        <v-card>
            <DialogToolbar
                :title="isEdit ? t('bots.presets.edit') : t('bots.presets.add_new')"
                :saving="saving"
                :save-disabled="!selectedBot"
                @cancel="cancel"
                @save="handleSubmit"
            />

            <v-card-text>
                <v-form ref="formRef" @submit.prevent="handleSubmit">
                    <v-select
                        v-model="selectedNode"
                        :items="nodes"
                        item-title="name"
                        item-value="id"
                        return-object
                        :label="t('bots.presets.node')"
                        variant="outlined"
                        density="comfortable"
                        class="mb-3"
                        :disabled="isEdit || saving || loadingNodes"
                        :loading="loadingNodes"
                        :rules="[(v) => !!v || t('error.required')]"
                    />

                    <v-select
                        v-if="selectedNode"
                        v-model="selectedBot"
                        :items="selectedNode.bots || []"
                        item-title="name"
                        item-value="id"
                        return-object
                        :label="t('bots.presets.bot')"
                        variant="outlined"
                        density="comfortable"
                        class="mb-3"
                        :disabled="isEdit || saving"
                        :rules="[(v) => !!v || t('error.required')]"
                    />

                    <v-text-field
                        v-if="selectedBot"
                        v-model="localItem.name"
                        :label="t('bots.presets.name')"
                        variant="outlined"
                        density="comfortable"
                        class="mb-3"
                        :rules="[(v) => !!v || t('error.required')]"
                        :disabled="saving"
                    />

                    <v-textarea
                        v-if="selectedBot"
                        v-model="localItem.description"
                        :label="t('bots.presets.description')"
                        variant="outlined"
                        density="comfortable"
                        rows="3"
                        class="mb-3"
                        :disabled="saving"
                    />

                    <!-- Dynamic Parameter Fields -->
                    <div v-if="selectedBot && selectedBot.parameters && selectedBot.parameters.length > 0">
                        <v-divider class="my-4" />
                        <h3 class="text-subtitle-1 mb-3">
                            {{ t('bots.presets.parameters') }}
                        </h3>

                        <div v-for="(param, index) in selectedBot.parameters" :key="param.key || index" class="mb-3">
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
                                    <v-icon color="primary" :title="param.description">mdi-help-circle</v-icon>
                                </v-col>
                            </v-row>
                        </div>
                    </div>

                    <v-alert v-if="showValidationError" type="error" density="compact" class="mb-3">
                        {{ t('error.validation') }}
                    </v-alert>

                    <v-alert v-if="showError" type="error" density="compact" class="mb-3">
                        {{ t('bots.presets.error') }}
                    </v-alert>
                </v-form>
            </v-card-text>
        </v-card>
    </v-dialog>
</template>

<script setup lang="ts">
    import { ref, computed, watch, onMounted } from 'vue'
    import { useI18n } from 'vue-i18n'
    import AddNewButton from '@/components/common/buttons/AddNewButton.vue'
    import DialogToolbar from '@/components/common/dialogs/DialogToolbar.vue'
    import { useAuth } from '@/composables/useAuth'
    import { createNewBotPreset, updateBotPreset, getAllBotsNodes } from '@/api/config'

    type PresetParameter = {
        id?: string | number
        key?: string
        name?: string
        description?: string
        default_value?: string
        [key: string]: unknown
    }

    type Bot = {
        id: string | number
        name?: string
        parameters?: PresetParameter[]
        [key: string]: unknown
    }

    type BotsNode = {
        id: string | number
        name?: string
        bots?: Bot[]
        [key: string]: unknown
    }

    type BotPresetParameterValue = {
        value?: string
        parameter?: PresetParameter
        [key: string]: unknown
    }

    type BotPresetItem = {
        id: string | number | null
        name: string
        description: string
        bot_id: string | number | null
        parameter_values: BotPresetParameterValue[]
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

    const nodes = ref<BotsNode[]>([])
    const selectedNode = ref<BotsNode | null>(null)
    const selectedBot = ref<Bot | null>(null)
    const parameterValues = ref<string[]>([])

    const defaultItem: BotPresetItem = {
        // Empty string (not null): backend requires a string id even on create (ignored), null fails validation.
        id: '',
        name: '',
        description: '',
        bot_id: null,
        parameter_values: []
    }

    const localItem = ref<BotPresetItem>({ ...defaultItem })

    const isEdit = computed(() => !!localItem.value.id)
    const canCreate = computed(() => checkPermission('CONFIG_BOT_PRESET_CREATE'))

    // Watch for edit item changes
    watch(
        () => props.editItem,
        (newVal) => {
            if (newVal) {
                const incoming = newVal as Partial<BotPresetItem> & {
                    bot_id?: string | number | null
                    parameter_values?: BotPresetParameterValue[]
                }

                localItem.value = { ...defaultItem, ...incoming }

                // Find and set the node and bot
                for (const node of nodes.value) {
                    const bot = node.bots?.find((b) => b.id === incoming.bot_id)
                    if (bot) {
                        selectedNode.value = node
                        selectedBot.value = bot as Bot

                        // Map parameter values
                        parameterValues.value =
                            bot.parameters?.map((param) => {
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

    // Watch selected bot to initialize parameter values
    watch(selectedBot, (newBot: Bot | null) => {
        if (!isEdit.value && newBot && newBot.parameters) {
            parameterValues.value = newBot.parameters.map((param) => String(param.default_value ?? ''))
        }
    })

    // Load bots nodes on mount
    onMounted(async () => {
        await loadNodes()
    })

    const loadNodes = async (): Promise<void> => {
        loadingNodes.value = true
        try {
            const response = (await getAllBotsNodes({ search: '' })) as { items?: BotsNode[]; data?: { items?: BotsNode[] } }
            nodes.value = response.items || response.data?.items || []

            // Auto-select first node and bot if available
            if (!isEdit.value && nodes.value.length > 0) {
                const firstNode = nodes.value[0]
                if (!firstNode) {
                    return
                }
                selectedNode.value = firstNode
                const bots = firstNode.bots ?? []
                if (bots.length > 0) {
                    selectedBot.value = bots[0] as Bot
                }
            }
        } catch (error) {
            console.error('Error loading bots nodes:', error)
        } finally {
            loadingNodes.value = false
        }
    }

    const resetForm = (): void => {
        localItem.value = { ...defaultItem }
        selectedNode.value = null
        selectedBot.value = null
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

        if (!valid || !selectedBot.value) {
            showValidationError.value = true
            return
        }

        saving.value = true

        try {
            // Prepare parameter values
            const paramValues =
                selectedBot.value.parameters?.map((param, index) => ({
                    value: String(parameterValues.value[index] ?? param.default_value ?? ''),
                    parameter: param
                })) || []

            const payload: BotPresetItem = {
                ...localItem.value,
                bot_id: selectedBot.value.id,
                parameter_values: paramValues
            }

            if (isEdit.value) {
                await updateBotPreset(payload)
                window.dispatchEvent(
                    new CustomEvent('notification', {
                        detail: { type: 'success', loc: 'common.updated_successfully' }
                    })
                )
            } else {
                await createNewBotPreset(payload)
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
