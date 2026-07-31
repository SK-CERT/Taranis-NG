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
                :title="isEdit ? t('presenters.types.edit') : t('presenters.types.add_new')"
                :saving="saving"
                :save-disabled="!selectedPresenter || !canUpdate"
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
                        :label="t('presenters.types.node')"
                        variant="outlined"
                        density="comfortable"
                        class="mb-3"
                        :disabled="isEdit || saving || loadingNodes || !canUpdate"
                        :loading="loadingNodes"
                        :rules="[(v) => !!v || t('error.required')]"
                    />

                    <v-select
                        v-if="selectedNode"
                        v-model="selectedPresenter"
                        :items="selectedNode.presenters || []"
                        item-title="name"
                        item-value="id"
                        return-object
                        :label="t('presenters.types.presenter')"
                        variant="outlined"
                        density="comfortable"
                        class="mb-3"
                        :disabled="isEdit || saving || !canUpdate"
                        :rules="[(v) => !!v || t('error.required')]"
                    />

                    <v-text-field
                        v-if="selectedPresenter"
                        v-model="localItem.title"
                        :label="t('presenters.types.name')"
                        variant="outlined"
                        density="comfortable"
                        class="mb-3"
                        :rules="[(v) => !!v || t('error.required')]"
                        :disabled="saving || !canUpdate"
                    />

                    <v-textarea
                        v-if="selectedPresenter"
                        v-model="localItem.description"
                        :label="t('presenters.types.description')"
                        variant="outlined"
                        density="comfortable"
                        rows="3"
                        class="mb-3"
                        :disabled="saving || !canUpdate"
                    />

                    <div v-if="selectedPresenter && selectedPresenter.parameters && selectedPresenter.parameters.length > 0">
                        <v-divider class="my-4" />
                        <div class="d-flex align-center mb-3">
                            <h3 class="text-subtitle-1">{{ t('presenters.types.parameters') }}</h3>
                            <v-spacer />
                            <v-btn
                                color="primary"
                                variant="tonal"
                                size="small"
                                @click="helpDialog = true"
                            >
                                <v-icon start>mdi-help-circle</v-icon>
                                {{ t('presenters.types.help') }}
                            </v-btn>
                        </div>

                        <div
                            v-for="(param, index) in selectedPresenter.parameters"
                            :key="param.id ?? param.key ?? index"
                            class="mb-3"
                        >
                            <v-text-field
                                v-model="parameterValues[index]"
                                :label="String(param.name || param.key || '')"
                                variant="outlined"
                                density="comfortable"
                                :disabled="saving || !canUpdate"
                                :placeholder="String(param.default_value ?? '')"
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
                    {{ t('presenters.types.error') }}
                </v-alert>

                <!-- Template variables help -->
                <v-dialog
                    v-model="helpDialog"
                    max-width="1200"
                    scrollable
                >
                    <v-card>
                        <DialogToolbar
                            :title="t('presenters.types.help')"
                            :show-save="false"
                            @cancel="helpDialog = false"
                        />
                        <v-card-text>
                            <v-select
                                v-model="selectedReportType"
                                :items="reportTypes"
                                item-title="title"
                                return-object
                                :label="t('presenters.types.choose_report_type')"
                                variant="outlined"
                                density="comfortable"
                                class="mb-4"
                            />

                            <div v-if="selectedReportType">
                                <!-- Report items -->
                                <v-card
                                    variant="outlined"
                                    class="mb-3"
                                >
                                    <v-card-title class="text-subtitle-1">{{ t('presenters.types.report_items') }}</v-card-title>
                                    <v-card-text>
                                        <div class="tpl-line">{% for report_item in data.report_items %}</div>
                                        <div
                                            v-for="key in reportItemVars"
                                            :key="key"
                                            class="tpl-row ml-4"
                                        >
                                            <strong>{{ t('presenters.types.report_items_object.' + key) }}</strong
                                            >:
                                            <code class="tpl-var">{{ variableUsage(key) }}</code>
                                        </div>
                                        <div class="tpl-line">{% endfor %}</div>
                                    </v-card-text>
                                </v-card>

                                <!-- News items -->
                                <v-card
                                    variant="outlined"
                                    class="mb-3"
                                >
                                    <v-card-title class="text-subtitle-1">{{ t('presenters.types.news_items') }}</v-card-title>
                                    <v-card-text>
                                        <div class="tpl-line">{% for report_item in data.report_items %}</div>
                                        <div class="tpl-line ml-4">{% for news_item in report_item.news_items %}</div>
                                        <div
                                            v-for="key in newsItemVars"
                                            :key="key"
                                            class="tpl-row ml-8"
                                        >
                                            <strong>{{ t('presenters.types.news_items_object.' + key) }}</strong
                                            >:
                                            <code class="tpl-var">{{ variableUsageNewsItems(key) }}</code>
                                        </div>
                                        <div class="tpl-line ml-4">{% endfor %}</div>
                                        <div class="tpl-line">{% endfor %}</div>
                                    </v-card-text>
                                </v-card>

                                <!-- Attribute groups -->
                                <v-card
                                    v-for="(group, groupIndex) in selectedReportType.attribute_groups || []"
                                    :key="group.id ?? groupIndex"
                                    variant="outlined"
                                    class="mb-3"
                                >
                                    <v-card-title class="text-subtitle-1">{{ group.title }}</v-card-title>
                                    <v-card-text>
                                        <div class="tpl-line">{% for report_item in data.report_items %}</div>
                                        <div
                                            v-for="(item, itemIndex) in group.attribute_group_items || []"
                                            :key="item.id ?? itemIndex"
                                            class="tpl-row ml-4"
                                        >
                                            <strong>{{ item.title }}</strong
                                            >:
                                            <code class="tpl-var">{{ attributeUsage(item) }}</code>
                                        </div>
                                        <div class="tpl-line">{% endfor %}</div>
                                    </v-card-text>
                                </v-card>
                            </div>
                        </v-card-text>
                    </v-card>
                </v-dialog>
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
    import { useConfigStore } from '@/stores/config'
    import { createNewProductType, updateProductType, getAllPresentersNodes } from '@/api/config'

    type PresenterParameter = {
        id?: string | number
        key?: string
        name?: string
        description?: string
        default_value?: string
        [key: string]: unknown
    }

    type Presenter = {
        id: string | number
        name?: string
        parameters?: PresenterParameter[]
        [key: string]: unknown
    }

    type PresenterNode = {
        id: string | number
        name?: string
        presenters?: Presenter[]
        [key: string]: unknown
    }

    type ParameterValue = {
        value?: string
        parameter?: PresenterParameter
        [key: string]: unknown
    }

    type ProductTypeItem = {
        id: string | number | null
        title: string
        description: string
        presenter_id: string | number | null
        parameter_values: ParameterValue[]
        [key: string]: unknown
    }

    type AttributeGroupItem = {
        id?: string | number
        title?: string
        max_occurrence?: number
        [key: string]: unknown
    }

    type AttributeGroup = {
        id?: string | number
        title?: string
        attribute_group_items?: AttributeGroupItem[]
        [key: string]: unknown
    }

    type ReportType = {
        id: string | number
        title?: string
        attribute_groups?: AttributeGroup[]
        [key: string]: unknown
    }

    type FormValidationResult = {
        valid: boolean
    }

    const props = withDefaults(
        defineProps<{
            editItem?: Partial<ProductTypeItem> | null
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
    const configStore = useConfigStore()

    const formRef = ref<any>(null)
    const showValidationError = ref(false)
    const showError = ref(false)
    const saving = ref(false)
    const dialog = ref(false)
    const loadingNodes = ref(false)

    // Template-variables help dialog
    const helpDialog = ref(false)
    const selectedReportType = ref<ReportType | null>(null)
    const reportTypes = computed(() => configStore.reportItemTypesConfig.items as ReportType[])

    const reportItemVars = ['name', 'name_prefix', 'type']
    const newsItemVars = ['title', 'review', 'content', 'author', 'source', 'link', 'published', 'collected']

    const variableUsage = (variable: string): string => `{{ report_item.${variable} | e }}`
    const variableUsageNewsItems = (variable: string): string => `{{ news_item.${variable} | e }}`
    const attributeUsage = (item: AttributeGroupItem): string => {
        const variable = String(item.title ?? '')
            .toLowerCase()
            .replaceAll(' ', '_')
        return (item.max_occurrence ?? 0) > 1
            ? `{% for entry in report_item.attrs.${variable} %}{{ entry | e }}{% endfor %}`
            : `{{ report_item.attrs.${variable} | e }}`
    }

    const nodes = ref<PresenterNode[]>([])
    const selectedNode = ref<PresenterNode | null>(null)
    const selectedPresenter = ref<Presenter | null>(null)
    const parameterValues = ref<string[]>([])

    const defaultItem: ProductTypeItem = {
        id: null,
        title: '',
        description: '',
        presenter_id: null,
        parameter_values: []
    }

    const localItem = ref<ProductTypeItem>({ ...defaultItem })

    const isEdit = computed(() => !!localItem.value.id)
    const canCreate = computed(() => checkPermission('CONFIG_PRODUCT_TYPE_CREATE'))
    const canUpdate = computed(() => checkPermission('CONFIG_PRODUCT_TYPE_UPDATE') || !isEdit.value)

    const mapParameterValues = (presenter: Presenter, incomingValues: ParameterValue[] = []): string[] => {
        return (
            presenter.parameters?.map((param) => {
                const paramValue = incomingValues.find((value) => value.parameter?.id === param.id)
                return String(paramValue?.value ?? param.default_value ?? '')
            }) || []
        )
    }

    const syncPresenterSelection = (presenterId: string | number | null | undefined): void => {
        if (presenterId === undefined || presenterId === null) {
            selectedNode.value = nodes.value[0] ?? null
            selectedPresenter.value = selectedNode.value?.presenters?.[0] ?? null
            // Initialize parameter values from the freshly-selected presenter's defaults here, not
            // in the selectedPresenter watcher. The watcher is queued AFTER the dialog watcher
            // (which calls capture() to snapshot the dirty-tracking baseline) because dialog=true
            // is mutated first, so leaving this to the async watcher snapshots params:[] while the
            // live state becomes the presenter's defaults — every subsequent create-open would
            // spuriously report unsaved changes. The edit path below already sets this synchronously.
            parameterValues.value = selectedPresenter.value?.parameters?.map((param) => String(param.default_value ?? '')) || []
            return
        }

        for (const node of nodes.value) {
            const presenter = node.presenters?.find((entry) => entry.id === presenterId)
            if (presenter) {
                selectedNode.value = node
                selectedPresenter.value = presenter
                parameterValues.value = mapParameterValues(presenter, localItem.value.parameter_values)
                return
            }
        }

        selectedNode.value = null
        selectedPresenter.value = null
        parameterValues.value = []
    }

    const openCreateDialog = (): void => {
        localItem.value = { ...defaultItem }
        showValidationError.value = false
        showError.value = false
        syncPresenterSelection(null)
    }

    const loadNodes = async (): Promise<void> => {
        loadingNodes.value = true
        try {
            const response = (await getAllPresentersNodes({ search: '' })) as {
                items?: PresenterNode[]
                data?: { items?: PresenterNode[] }
            }
            nodes.value = response.items || response.data?.items || []
            if (isEdit.value) {
                syncPresenterSelection(localItem.value.presenter_id)
            } else if (!selectedNode.value && nodes.value.length > 0) {
                selectedNode.value = nodes.value[0] ?? null
                selectedPresenter.value = selectedNode.value?.presenters?.[0] ?? null
            }
        } catch (error) {
            console.error('Error loading presenters nodes:', error)
        } finally {
            loadingNodes.value = false
        }
    }

    const resetFormState = (): void => {
        localItem.value = { ...defaultItem }
        selectedNode.value = null
        selectedPresenter.value = null
        parameterValues.value = []
        showValidationError.value = false
        showError.value = false
        saving.value = false
        formRef.value?.resetValidation?.()
    }

    // Persists the form. Returns true on success so the guard can decide whether to close.
    async function persist(): Promise<boolean> {
        showValidationError.value = false
        showError.value = false

        if (!formRef.value?.validate) {
            return false
        }

        const { valid } = (await formRef.value.validate()) as FormValidationResult
        if (!valid || !selectedPresenter.value) {
            showValidationError.value = true
            return false
        }

        saving.value = true
        try {
            const payload: ProductTypeItem = {
                ...localItem.value,
                presenter_id: selectedPresenter.value.id,
                parameter_values:
                    selectedPresenter.value.parameters?.map((param, index) => ({
                        value: String(parameterValues.value[index] ?? param.default_value ?? ''),
                        parameter: param
                    })) || []
            }

            if (isEdit.value) {
                await updateProductType(payload)
                window.dispatchEvent(
                    new CustomEvent('notification', {
                        detail: { type: 'success', loc: 'presenters.types.successful_edit' }
                    })
                )
            } else {
                // Backend requires an integer id even on create (ignored); null fails validation.
                await createNewProductType({ ...payload, id: -1 })
                window.dispatchEvent(
                    new CustomEvent('notification', {
                        detail: { type: 'success', loc: 'presenters.types.successful' }
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
        getState: () => ({ item: localItem.value, presenter: selectedPresenter.value?.id ?? null, params: parameterValues.value }),
        save: persist,
        close: closeDialog
    })

    watch(
        () => props.editItem,
        (newItem) => {
            if (newItem && Object.keys(newItem).length > 0) {
                localItem.value = { ...defaultItem, ...newItem }
                syncPresenterSelection(localItem.value.presenter_id)
                dialog.value = true
            }
        },
        { immediate: true, deep: true }
    )

    watch(selectedNode, (newNode) => {
        if (!newNode) {
            selectedPresenter.value = null
            parameterValues.value = []
            return
        }

        const presenters = newNode.presenters || []
        if (isEdit.value && localItem.value.presenter_id != null) {
            const presenter = presenters.find((entry) => entry.id === localItem.value.presenter_id)
            if (presenter) {
                selectedPresenter.value = presenter
                return
            }
        }

        selectedPresenter.value = presenters[0] ?? null
    })

    watch(selectedPresenter, (newPresenter) => {
        if (!newPresenter) {
            parameterValues.value = []
            return
        }

        if (isEdit.value) {
            parameterValues.value = mapParameterValues(newPresenter, localItem.value.parameter_values)
            return
        }

        parameterValues.value = newPresenter.parameters?.map((param) => String(param.default_value ?? '')) || []
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
        await Promise.all([loadNodes(), configStore.loadReportItemTypesConfig({ search: '' })])
    })
</script>

<style scoped>
    .tpl-line {
        font-family: monospace;
        color: rgba(var(--v-theme-on-surface), 0.6);
    }

    .tpl-row {
        margin: 2px 0;
    }

    .tpl-var {
        background-color: rgba(var(--v-theme-on-surface), 0.08);
        padding: 1px 6px;
        border-radius: 4px;
        font-style: italic;
    }
</style>
