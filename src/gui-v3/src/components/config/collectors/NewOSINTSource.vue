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
                @click="openCreateDialog"
            />
        </template>

        <v-card>
            <DialogToolbar
                :title="isEdit ? t('collectors.sources.edit') : t('collectors.sources.add_new')"
                :saving="saving"
                :save-disabled="!selectedCollector"
                :show-save="canSave"
                @cancel="requestClose"
                @save="saveAndClose"
            />

            <v-card-text>
                <v-form
                    ref="formRef"
                    :disabled="!canSave"
                    @submit.prevent="saveAndClose"
                >
                    <v-select
                        v-model="selectedNode"
                        :items="nodes"
                        item-title="name"
                        item-value="id"
                        return-object
                        :label="t('collectors.sources.node')"
                        variant="outlined"
                        density="comfortable"
                        class="mb-3"
                        :disabled="saving || loadingNodes || !canSave"
                        :loading="loadingNodes"
                        :rules="[(v) => !!v || t('error.required')]"
                    />

                    <v-select
                        v-if="selectedNode"
                        v-model="selectedCollector"
                        :items="selectedNode.collectors || []"
                        item-title="name"
                        item-value="id"
                        return-object
                        :label="t('collectors.sources.collector')"
                        variant="outlined"
                        density="comfortable"
                        class="mb-3"
                        :disabled="saving || !canSave"
                        :rules="[(v) => !!v || t('error.required')]"
                    />

                    <v-text-field
                        v-if="selectedCollector"
                        v-model="localItem.name"
                        :spellcheck="spellcheck"
                        :label="t('collectors.sources.name')"
                        variant="outlined"
                        density="comfortable"
                        class="mb-3"
                        :rules="[(v) => !!v || t('error.required')]"
                        :disabled="saving || !canSave"
                    />

                    <v-textarea
                        v-if="selectedCollector"
                        v-model="localItem.description"
                        :spellcheck="spellcheck"
                        :label="t('collectors.sources.description')"
                        variant="outlined"
                        density="comfortable"
                        rows="3"
                        class="mb-3"
                        :disabled="saving || !canSave"
                    />

                    <div v-if="selectedCollector && selectedCollector.parameters && selectedCollector.parameters.length > 0">
                        <v-divider class="my-4" />
                        <h3 class="text-subtitle-1 mb-3">{{ t('collectors.sources.parameters') }}</h3>

                        <div
                            v-for="(param, index) in selectedCollector.parameters"
                            :key="param.id ?? param.key ?? index"
                            class="mb-3"
                        >
                            <v-text-field
                                v-model="parameterValues[index]"
                                :spellcheck="false"
                                :label="String(param.name || param.key || '')"
                                :type="typeof param.key === 'string' && param.key.includes('PASSWORD') ? 'password' : 'text'"
                                variant="outlined"
                                density="comfortable"
                                :disabled="saving || !canSave"
                                :placeholder="String(param.default_value ?? '')"
                                :rules="dynamicParameterRules(param, t('error.required'))"
                            >
                                <template
                                    v-if="param.description"
                                    #append-inner
                                >
                                    <v-icon
                                        color="primary"
                                        :title="String(param.description)"
                                        >mdi-help-circle</v-icon
                                    >
                                </template>
                            </v-text-field>
                        </div>
                    </div>

                    <div
                        v-if="selectedCollector"
                        class="mt-4"
                    >
                        <EntitySelectTable
                            v-model="selectedOSINTSourceGroupIds"
                            :title="t('collectors.sources.osint_source_groups')"
                            :items="osintSourceGroupItems"
                            :headers="groupHeaders"
                            :loading="loadingGroups"
                            :disabled="saving || !canSave"
                        >
                            <template #header-append>
                                <NewOSINTSourceGroup @saved="handleGroupSaved" />
                            </template>
                        </EntitySelectTable>

                        <EntitySelectTable
                            v-model="selectedWordListIds"
                            :title="t('collectors.sources.filter_wordlist')"
                            :items="wordListItems"
                            :headers="wordListHeaders"
                            :loading="loadingWordLists"
                            :disabled="saving || !canSave"
                        />
                    </div>
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
                    {{ t('collectors.sources.error') }}
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
    import { ref, computed, watch, onMounted } from 'vue'
    import { useI18n } from 'vue-i18n'
    import { useSpellcheck } from '@/composables/useSpellcheck'
    import AddNewButton from '@/components/common/buttons/AddNewButton.vue'
    import DialogToolbar from '@/components/common/dialogs/DialogToolbar.vue'
    import UnsavedChangesDialog from '@/components/common/dialogs/UnsavedChangesDialog.vue'
    import { useUnsavedChanges } from '@/composables/useUnsavedChanges'
    import { useAuth } from '@/composables/useAuth'
    import { useConfigStore } from '@/stores/config'
    import EntitySelectTable from '@/components/common/EntitySelectTable.vue'
    import { createNewOSINTSource, updateOSINTSource, getAllCollectorsNodes } from '@/api/config'
    import NewOSINTSourceGroup from '@/components/config/collectors/NewOSINTSourceGroup.vue'
    import { dynamicParameterRules } from '@/utils/dynamicParameterValidation'

    type CollectorParameter = {
        id?: string | number
        key?: string
        name?: string
        description?: string
        default_value?: string
        required?: boolean
        [key: string]: unknown
    }

    type Collector = {
        id: string | number
        name?: string
        // Collector rows are per-node, so `type` — not `id` — is what identifies
        // the equivalent collector on another node.
        type?: string
        parameters?: CollectorParameter[]
        [key: string]: unknown
    }

    type CollectorNode = {
        id: string | number
        name?: string
        collectors?: Collector[]
        [key: string]: unknown
    }

    type ParameterValue = {
        value?: string
        parameter?: CollectorParameter
        [key: string]: unknown
    }

    type IdItem = {
        id: string | number
        name?: string
        description?: string
        default?: boolean
        [key: string]: unknown
    }

    type OSINTSourceItem = {
        id: string | number | null
        name: string
        description: string
        collector_id: string | number | null
        parameter_values: ParameterValue[]
        word_lists: Array<{ id: string | number }>
        osint_source_groups: Array<{ id: string | number }>
        [key: string]: unknown
    }

    // Exactly the editable fields the backend's NewOSINTSourceSchema accepts.
    // The OSINTSource db-model __init__ takes ONLY these kwargs; any extra
    // runtime field (last_attempted, last_collected, state, modified, nested
    // collector, ...) sent back in the PUT payload crashes the constructor with
    // `__init__() got an unexpected keyword argument '<field>'`.
    const EDITABLE_KEYS: ReadonlyArray<keyof OSINTSourceItem> = [
        'id',
        'name',
        'description',
        'collector_id',
        'parameter_values',
        'word_lists',
        'osint_source_groups'
    ]

    type FormValidationResult = {
        valid: boolean
    }

    const props = withDefaults(
        defineProps<{
            editItem?: Partial<OSINTSourceItem> | null
        }>(),
        {
            editItem: null
        }
    )

    const emit = defineEmits<{
        (e: 'saved'): void
    }>()

    const { t } = useI18n()
    const spellcheck = useSpellcheck()
    const { checkPermission } = useAuth()
    const configStore = useConfigStore()

    const formRef = ref<any>(null)
    const showValidationError = ref(false)
    const showError = ref(false)
    const saving = ref(false)
    const dialog = ref(false)
    const loadingNodes = ref(false)
    const loadingWordLists = ref(false)
    const loadingGroups = ref(false)

    const nodes = ref<CollectorNode[]>([])
    const selectedNode = ref<CollectorNode | null>(null)
    const selectedCollector = ref<Collector | null>(null)
    // Collector type the source is bound to, captured when the dialog opens.
    // Switching nodes uses it to find the equivalent collector on the target
    // node; the backend only permits moves between collectors of the same type.
    const boundCollectorType = ref<string | null>(null)
    const parameterValues = ref<string[]>([])
    const selectedWordListIds = ref<Array<string | number>>([])
    const selectedOSINTSourceGroupIds = ref<Array<string | number>>([])

    const wordListHeaders = [
        { title: t('card_item.name'), key: 'name' },
        { title: t('card_item.description'), key: 'description' }
    ]

    const groupHeaders = [
        { title: t('card_item.name'), key: 'name' },
        { title: t('card_item.description'), key: 'description' }
    ]

    const defaultItem: OSINTSourceItem = {
        // Empty string (not null): backend requires a string id even on create (ignored), null fails validation.
        id: '',
        name: '',
        description: '',
        collector_id: null,
        parameter_values: [],
        word_lists: [],
        osint_source_groups: []
    }

    const localItem = ref<OSINTSourceItem>({ ...defaultItem })

    const isEdit = computed(() => !!localItem.value.id)
    const canCreate = computed(() => checkPermission('CONFIG_OSINT_SOURCE_CREATE'))
    const canSave = computed(() => checkPermission(isEdit.value ? 'CONFIG_OSINT_SOURCE_UPDATE' : 'CONFIG_OSINT_SOURCE_CREATE'))

    const wordListItems = computed(() => configStore.wordLists.items as IdItem[])
    const osintSourceGroupItems = computed(() => {
        const items = configStore.osintSourceGroups.items as IdItem[]
        return items.filter((item) => item.default !== true)
    })

    const extractIds = (items: unknown): Array<string | number> => {
        if (!Array.isArray(items)) {
            return []
        }
        return items
            .map((item) => {
                if (item && typeof item === 'object' && 'id' in item) {
                    return (item as { id?: string | number }).id
                }
                return undefined
            })
            .filter((id): id is string | number => id !== undefined && id !== null)
    }

    const mapParameterValues = (collector: Collector, incomingValues: ParameterValue[] = []): string[] => {
        return (
            collector.parameters?.map((param) => {
                // Match by parameter.id first (same collector, re-edit case)…
                let paramValue = incomingValues.find((value) => value.parameter?.id === param.id)
                // …then fall back to parameter.key (moving the source to a
                // collector on a different node — same parameter set, different ids).
                if (!paramValue && param.key) {
                    paramValue = incomingValues.find((value) => value.parameter?.key === param.key)
                }
                return String(paramValue?.value ?? param.default_value ?? '')
            }) || []
        )
    }

    // Which collector the values currently held in `parameterValues` belong to. This is NOT
    // the same as the selectedCollector watcher's `oldValue`: syncCollectorSelection writes
    // the record's values for the INCOMING collector synchronously, while the outgoing
    // selection is still whatever create mode left behind (the first node's first collector).
    // Labelling the record's values with that unrelated collector's keys is what blanked
    // every parameter on the first open of the dialog.
    const parameterValuesKeyedTo = ref<Collector | null>(null)

    // Snapshot what is currently in the parameter inputs, shaped like the record's own
    // parameter_values so mapParameterValues can match it. The inputs are bound by index to
    // `collector.parameters` (see the v-for in the template), so the collector they were
    // rendered from is what supplies their keys.
    const liveParameterValues = (collector: Collector): ParameterValue[] =>
        collector.parameters?.map((param, index) => ({
            value: String(parameterValues.value[index] ?? ''),
            parameter: param
        })) ?? []

    const syncCollectorSelection = (collectorId: string | number | null | undefined): void => {
        if (collectorId === undefined || collectorId === null) {
            selectedNode.value = nodes.value[0] ?? null
            selectedCollector.value = selectedNode.value?.collectors?.[0] ?? null
            // Initialize parameter values from the freshly-selected collector's defaults here, not
            // in the selectedCollector watcher. The watcher is queued AFTER the dialog watcher
            // (which calls capture() to snapshot the dirty-tracking baseline) because dialog=true
            // is mutated first, so leaving this to the async watcher snapshots params:[] while the
            // live state becomes the collector's defaults — every subsequent create-open would
            // spuriously report unsaved changes. The edit path below already sets this synchronously.
            parameterValues.value = selectedCollector.value?.parameters?.map((param) => String(param.default_value ?? '')) || []
            parameterValuesKeyedTo.value = selectedCollector.value
            boundCollectorType.value = null
            return
        }

        for (const node of nodes.value) {
            const collector = node.collectors?.find((entry) => entry.id === collectorId)
            if (collector) {
                selectedNode.value = node
                selectedCollector.value = collector
                boundCollectorType.value = collector.type ?? null
                parameterValues.value = mapParameterValues(collector, localItem.value.parameter_values)
                parameterValuesKeyedTo.value = collector
                return
            }
        }

        selectedNode.value = null
        selectedCollector.value = null
        boundCollectorType.value = null
        parameterValues.value = []
        parameterValuesKeyedTo.value = null
    }

    const openCreateDialog = (): void => {
        localItem.value = { ...defaultItem }
        selectedWordListIds.value = []
        selectedOSINTSourceGroupIds.value = []
        showValidationError.value = false
        showError.value = false
        syncCollectorSelection(null)
    }

    const loadNodes = async (): Promise<void> => {
        loadingNodes.value = true
        try {
            const response = (await getAllCollectorsNodes({ search: '' })) as {
                items?: CollectorNode[]
                data?: { items?: CollectorNode[] }
            }
            nodes.value = response.items || response.data?.items || []
            if (isEdit.value) {
                syncCollectorSelection(localItem.value.collector_id)
            } else if (!selectedNode.value && nodes.value.length > 0) {
                selectedNode.value = nodes.value[0] ?? null
                selectedCollector.value = selectedNode.value?.collectors?.[0] ?? null
            }
        } catch (error) {
            console.error('Error loading collectors nodes:', error)
        } finally {
            loadingNodes.value = false
        }
    }

    const loadWordLists = async (): Promise<void> => {
        loadingWordLists.value = true
        try {
            await configStore.loadWordLists({ search: '' })
        } catch (error) {
            console.error('Error loading word lists:', error)
        } finally {
            loadingWordLists.value = false
        }
    }

    const loadSourceGroups = async (): Promise<void> => {
        loadingGroups.value = true
        try {
            await configStore.loadOSINTSourceGroups({ search: '' })
        } catch (error) {
            console.error('Error loading OSINT source groups:', error)
        } finally {
            loadingGroups.value = false
        }
    }

    const resetFormState = (): void => {
        localItem.value = { ...defaultItem }
        selectedNode.value = null
        selectedCollector.value = null
        boundCollectorType.value = null
        parameterValues.value = []
        parameterValuesKeyedTo.value = null
        selectedWordListIds.value = []
        selectedOSINTSourceGroupIds.value = []
        showValidationError.value = false
        showError.value = false
        saving.value = false
        formRef.value?.resetValidation?.()
    }

    const handleGroupSaved = async (): Promise<void> => {
        await loadSourceGroups()
    }

    // Persists the form. Returns true on success so the guard can decide whether to close.
    async function persist(): Promise<boolean> {
        if (!canSave.value) return false
        showValidationError.value = false
        showError.value = false

        if (!formRef.value?.validate) {
            return false
        }

        const { valid } = (await formRef.value.validate()) as FormValidationResult
        if (!valid || !selectedCollector.value) {
            showValidationError.value = true
            return false
        }

        saving.value = true
        try {
            // Minimal payload: only the editable fields the backend's
            // NewOSINTSourceSchema + OSINTSource.__init__ accept. Do NOT spread
            // localItem wholesale — it (and the source API record for edits)
            // may carry runtime fields (last_attempted, last_collected,
            // state, modified, nested collector, ...) that crash
            // OSINTSource(**data) on the server.
            const payload: OSINTSourceItem = {
                id: localItem.value.id,
                name: localItem.value.name,
                description: localItem.value.description,
                collector_id: selectedCollector.value.id,
                parameter_values:
                    selectedCollector.value.parameters?.map((param, index) => ({
                        value: String(parameterValues.value[index] ?? param.default_value ?? ''),
                        parameter: param
                    })) || [],
                word_lists: selectedWordListIds.value.map((id) => ({ id })),
                osint_source_groups: selectedOSINTSourceGroupIds.value.map((id) => ({ id }))
            }

            if (isEdit.value) {
                await updateOSINTSource(payload)
                window.dispatchEvent(
                    new CustomEvent('notification', {
                        detail: { type: 'success', loc: 'collectors.sources.successful_edit' }
                    })
                )
            } else {
                await createNewOSINTSource(payload)
                window.dispatchEvent(
                    new CustomEvent('notification', {
                        detail: { type: 'success', loc: 'collectors.sources.successful' }
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

    function closeDialog(): void {
        dialog.value = false
    }

    const { confirmVisible, capture, requestClose, continueEditing, saveAndClose, discardAndClose } = useUnsavedChanges({
        getState: () => ({
            item: localItem.value,
            collector: selectedCollector.value?.id ?? null,
            params: parameterValues.value,
            wordLists: selectedWordListIds.value,
            groups: selectedOSINTSourceGroupIds.value
        }),
        save: persist,
        close: closeDialog
    })

    watch(
        () => props.editItem,
        (newItem) => {
            if (newItem && Object.keys(newItem).length > 0) {
                // Whitelist editable keys: the API record also carries runtime
                // fields (last_attempted, last_collected, state, modified, nested
                // collector, ...) that the backend's NewOSINTSourceSchema would
                // forward to OSINTSource(**data), crashing the model __init__.
                // Keep only the keys the db model accepts.
                const sanitized: Partial<OSINTSourceItem> = { ...defaultItem }
                for (const key of EDITABLE_KEYS) {
                    if (newItem[key] !== undefined) {
                        sanitized[key] = newItem[key] as OSINTSourceItem[typeof key]
                    }
                }
                localItem.value = sanitized as OSINTSourceItem
                selectedWordListIds.value = extractIds(newItem.word_lists)
                selectedOSINTSourceGroupIds.value = extractIds(newItem.osint_source_groups)
                syncCollectorSelection(localItem.value.collector_id)
                dialog.value = true
            }
        },
        { immediate: true, deep: true }
    )

    watch(selectedNode, (newNode) => {
        if (!newNode) {
            selectedCollector.value = null
            parameterValues.value = []
            return
        }

        const collectors = newNode.collectors || []
        if (isEdit.value && localItem.value.collector_id != null) {
            const collector = collectors.find((entry) => entry.id === localItem.value.collector_id)
            if (collector) {
                selectedCollector.value = collector
                return
            }
        }

        // Moving an existing source to another node. Collector rows are per-node,
        // so the id above never matches here — match on TYPE instead. That is
        // what makes the move work at all: the backend rejects a move between
        // collectors of different types, and only a same-type collector has the
        // parameter keys mapParameterValues needs to carry the values over.
        // Falling back to collectors[0] would silently land on an unrelated
        // collector, blank every field, and then fail to save.
        if (isEdit.value && boundCollectorType.value) {
            selectedCollector.value = collectors.find((entry) => entry.type === boundCollectorType.value) ?? null
            return
        }

        selectedCollector.value = collectors[0] ?? null
    })

    watch(selectedCollector, (newCollector) => {
        if (!newCollector) {
            parameterValues.value = []
            parameterValuesKeyedTo.value = null
            return
        }

        if (isEdit.value) {
            // Carry over what the operator can actually see, keyed by the collector those
            // values belong to rather than by the watcher's outgoing value. When the operator
            // switches node this is the collector they were just editing, so in-progress edits
            // survive the move; during (re)initialisation syncCollectorSelection has already
            // pointed it at the incoming collector, so this re-maps the record's own values
            // onto themselves and leaves them intact. Before the first resolve it is null and
            // the values come straight off the loaded record.
            const source = parameterValuesKeyedTo.value
            const incoming = source ? liveParameterValues(source) : localItem.value.parameter_values
            parameterValues.value = mapParameterValues(newCollector, incoming)
            parameterValuesKeyedTo.value = newCollector
            return
        }

        parameterValues.value = newCollector.parameters?.map((param) => String(param.default_value ?? '')) || []
        parameterValuesKeyedTo.value = newCollector
    })

    watch(dialog, (newValue) => {
        if (!newValue) {
            resetFormState()
        } else {
            // Snapshot the freshly-loaded form as the clean baseline for dirty-tracking.
            capture()
        }
    })

    onMounted(async () => {
        await Promise.all([loadNodes(), loadWordLists(), loadSourceGroups()])
    })
</script>
