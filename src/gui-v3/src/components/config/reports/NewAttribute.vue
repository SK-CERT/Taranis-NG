<template>
    <v-dialog
        v-model="dialog"
        max-width="900"
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
                :title="isEdit ? t('reports.attributes.edit') : t('reports.attributes.add_new')"
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

                    <v-row>
                        <v-col
                            cols="12"
                            md="6"
                        >
                            <v-select
                                v-model="localItem.type"
                                :label="t('reports.attributes.type')"
                                :items="attributeTypes"
                                variant="outlined"
                                density="comfortable"
                                :rules="[(v) => !!v || t('error.required')]"
                                :disabled="saving"
                            />
                        </v-col>
                        <v-col
                            cols="12"
                            md="6"
                        >
                            <v-text-field
                                v-model="localItem.default_value"
                                :label="t('reports.attributes.default_value')"
                                variant="outlined"
                                density="comfortable"
                                :disabled="saving"
                            />
                        </v-col>
                        <v-col
                            cols="12"
                            md="6"
                        >
                            <v-select
                                v-model="localItem.validator"
                                :label="t('reports.attributes.validator')"
                                :items="validators"
                                variant="outlined"
                                density="comfortable"
                                :disabled="saving"
                            />
                        </v-col>
                        <v-col
                            cols="12"
                            md="6"
                        >
                            <v-text-field
                                v-model="localItem.validator_parameter"
                                :label="t('reports.attributes.validator_parameter')"
                                variant="outlined"
                                density="comfortable"
                                :disabled="saving"
                            />
                        </v-col>
                    </v-row>

                    <!-- Attribute constants (enums) -->
                    <EditableEntityTable
                        :key="tableKey"
                        v-model:dialog="constantDialog"
                        v-model:page="constantPage"
                        v-model:items-per-page="constantPageSize"
                        v-model:search="constantSearch"
                        server
                        searchable
                        :items="constants"
                        :items-length="constantsTotal"
                        :loading="constantsLoading"
                        :title="t('reports.attributes.constants')"
                        :headers="constantHeaders"
                        :default-item="newConstant"
                        :add-title="t('reports.attributes.add_constant')"
                        :edit-title="t('reports.attributes.edit_constant')"
                        :saving="constantSaving"
                        :disabled="saving"
                        dialog-max-width="500"
                        @update:options="onConstantsOptions"
                        @save="onConstantSave"
                        @delete="onConstantDelete"
                    >
                        <template #form="{ item }">
                            <v-text-field
                                v-model="item.value"
                                :label="t('reports.attributes.value')"
                                variant="outlined"
                                density="comfortable"
                                class="mb-3"
                                :disabled="constantSaving"
                            />
                            <v-text-field
                                v-model="item.description"
                                :label="t('reports.attributes.description')"
                                variant="outlined"
                                density="comfortable"
                                :disabled="constantSaving"
                            />
                        </template>
                    </EditableEntityTable>
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
    import {
        createNewAttribute,
        updateAttribute,
        getAttributeEnums,
        addAttributeEnum,
        updateAttributeEnum,
        deleteAttributeEnum
    } from '@/api/config'
    import AddNewButton from '@/components/common/buttons/AddNewButton.vue'
    import DialogToolbar from '@/components/common/dialogs/DialogToolbar.vue'
    import UnsavedChangesDialog from '@/components/common/dialogs/UnsavedChangesDialog.vue'
    import { useUnsavedChanges } from '@/composables/useUnsavedChanges'
    import EditableEntityTable from '@/components/common/EditableEntityTable.vue'

    type AttributeType =
        | 'STRING'
        | 'NUMBER'
        | 'BOOLEAN'
        | 'RADIO'
        | 'ENUM'
        | 'TEXT'
        | 'RICH_TEXT'
        | 'DATE'
        | 'TIME'
        | 'DATE_TIME'
        | 'LINK'
        | 'ATTACHMENT'
        | 'TLP'
        | 'CPE'
        | 'CVE'
        | 'CVSS'
        | 'CWE'

    type AttributeValidator = 'NONE' | 'EMAIL' | 'NUMBER' | 'RANGE' | 'REGEXP'

    type AttributeConstant = {
        id: number
        index: number
        value: string
        description: string
    }

    type AttributeItem = {
        id: number | null
        name: string
        description: string
        type: AttributeType
        default_value: string
        validator: AttributeValidator
        validator_parameter: string
        [key: string]: unknown
    }

    type SelectItem<T> = {
        title: string
        value: T
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

    const attributeTypes: SelectItem<AttributeType>[] = [
        { title: 'String', value: 'STRING' },
        { title: 'Number', value: 'NUMBER' },
        { title: 'Boolean', value: 'BOOLEAN' },
        { title: 'Radio', value: 'RADIO' },
        { title: 'Enumeration', value: 'ENUM' },
        { title: 'Text', value: 'TEXT' },
        { title: 'Rich Text', value: 'RICH_TEXT' },
        { title: 'Date', value: 'DATE' },
        { title: 'Time', value: 'TIME' },
        { title: 'Date Time', value: 'DATE_TIME' },
        { title: 'Link', value: 'LINK' },
        { title: 'Attachment', value: 'ATTACHMENT' },
        { title: 'TLP', value: 'TLP' },
        { title: 'CPE', value: 'CPE' },
        { title: 'CVE', value: 'CVE' },
        { title: 'CVSS', value: 'CVSS' },
        { title: 'CWE', value: 'CWE' }
    ]

    const validators: SelectItem<AttributeValidator>[] = [
        { title: 'None', value: 'NONE' },
        { title: 'Email', value: 'EMAIL' },
        { title: 'Number', value: 'NUMBER' },
        { title: 'Range', value: 'RANGE' },
        { title: 'Regular Expression', value: 'REGEXP' }
    ]

    const defaultItem: AttributeItem = {
        id: null,
        name: '',
        description: '',
        type: 'STRING',
        default_value: '',
        validator: 'NONE',
        validator_parameter: ''
    }

    const localItem = ref<AttributeItem>({ ...defaultItem })
    const isEdit = computed(() => !!localItem.value.id)

    const canCreate = computed(() => checkPermission('CONFIG_ATTRIBUTE_CREATE'))

    // --- Attribute constants (enums) ---
    const constants = ref<AttributeConstant[]>([])
    const constantsTotal = ref(0)
    const constantsLoading = ref(false)
    const constantSearch = ref('')
    const constantPage = ref(1)
    const constantPageSize = ref(25)
    // Bumped on every dialog open to force the server table to remount and re-fire
    // @update:options. The dialog keeps its content mounted between opens, so without
    // this the table would only load constants the first time it is shown.
    const tableKey = ref(0)
    let searchTimeout: ReturnType<typeof setTimeout> | undefined

    const constantDialog = ref(false)
    const constantSaving = ref(false)

    const constantHeaders = [
        { title: t('reports.attributes.value'), key: 'value', sortable: false },
        { title: t('reports.attributes.description'), key: 'description', sortable: false },
        { title: t('settings.actions'), key: 'actions', align: 'end' as const, sortable: false }
    ]

    const newConstant = (): AttributeConstant => ({ id: -1, index: -1, value: '', description: '' })

    const notify = (type: 'success' | 'error', loc: string): void => {
        window.dispatchEvent(new CustomEvent('notification', { detail: { type, loc } }))
    }

    const loadConstants = async (): Promise<void> => {
        if (!isEdit.value || localItem.value.id === null) {
            return
        }
        constantsLoading.value = true
        try {
            const response = (await getAttributeEnums({
                attribute_id: localItem.value.id,
                search: constantSearch.value,
                offset: (constantPage.value - 1) * constantPageSize.value,
                limit: constantPageSize.value
            })) as { data?: { items?: AttributeConstant[]; total_count?: number } }
            constants.value = response.data?.items ?? []
            constantsTotal.value = response.data?.total_count ?? 0
        } catch (error) {
            console.error('Error loading attribute constants:', error)
        } finally {
            constantsLoading.value = false
        }
    }

    // Fired by the data table on mount and whenever page/size change.
    const onConstantsOptions = (options: { page: number; itemsPerPage: number }): void => {
        constantPage.value = options.page
        constantPageSize.value = options.itemsPerPage
        if (isEdit.value) {
            loadConstants()
        } else {
            // Create mode: constants are kept in memory until the attribute is saved.
            constantsTotal.value = constants.value.length
        }
    }

    // Debounced server search (only meaningful in edit mode; create mode keeps a small in-memory list).
    watch(constantSearch, () => {
        clearTimeout(searchTimeout)
        searchTimeout = setTimeout(() => {
            constantPage.value = 1
            loadConstants()
        }, 300)
    })

    // Persist a constant from the table's add/edit dialog. `isNew` is true when adding.
    const onConstantSave = async (constant: AttributeConstant, { isNew }: { isNew: boolean }): Promise<void> => {
        constantSaving.value = true
        try {
            if (isEdit.value && localItem.value.id !== null) {
                // Edit mode: persist immediately via the API.
                if (!isNew && constant.id > 0) {
                    await updateAttributeEnum(localItem.value.id, constant.id, [{ value: constant.value, description: constant.description }])
                } else {
                    await addAttributeEnum(localItem.value.id, {
                        items: [{ value: constant.value, description: constant.description }],
                        delete_existing: false
                    })
                }
                await loadConstants()
            } else {
                // Create mode: keep the constant in memory until the attribute is saved.
                if (!isNew && constant.index >= 0) {
                    const idx = constants.value.findIndex((c) => c.index === constant.index)
                    if (idx > -1) {
                        constants.value[idx] = { ...constant }
                    }
                } else {
                    constants.value.push({ ...constant, index: constants.value.length })
                }
                constantsTotal.value = constants.value.length
            }
            constantDialog.value = false
        } catch (error) {
            console.error('Error saving attribute constant:', error)
            notify('error', 'common.error_saving')
        } finally {
            constantSaving.value = false
        }
    }

    const onConstantDelete = async (constant: AttributeConstant): Promise<void> => {
        try {
            if (isEdit.value && localItem.value.id !== null) {
                await deleteAttributeEnum(localItem.value.id, constant.id)
                await loadConstants()
            } else {
                constants.value = constants.value.filter((c) => c.index !== constant.index)
                constantsTotal.value = constants.value.length
            }
        } catch (error) {
            console.error('Error deleting attribute constant:', error)
            notify('error', 'common.error_saving')
        }
    }

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
                await updateAttribute(localItem.value)
                notify('success', 'common.updated_successfully')
            } else {
                // Backend requires an integer id even on create (ignored); null fails validation.
                await createNewAttribute({
                    ...localItem.value,
                    id: -1,
                    attribute_enums: constants.value.map((c, index) => ({
                        value: c.value,
                        description: c.description,
                        index
                    }))
                })
                notify('success', 'common.created_successfully')
            }
            emit('saved')
            return true
        } catch (error) {
            notify('error', 'common.error_saving')
            showError.value = true
            return false
        } finally {
            saving.value = false
        }
    }

    function resetConstants(): void {
        constants.value = []
        constantsTotal.value = 0
        constantSearch.value = ''
        constantPage.value = 1
    }

    function closeDialog(): void {
        showValidationError.value = false
        showError.value = false
        formRef.value?.reset()
        localItem.value = { ...defaultItem }
        resetConstants()
        dialog.value = false
    }

    const { confirmVisible, capture, requestClose, continueEditing, saveAndClose, discardAndClose } = useUnsavedChanges({
        // In edit mode, constants are persisted immediately via their own dialog, so they
        // are not "unsaved"; only track them in create mode where they live in memory.
        getState: () => (isEdit.value ? { item: localItem.value } : { item: localItem.value, constants: constants.value }),
        save: persist,
        close: closeDialog
    })

    watch(
        () => props.editItem,
        (newItem) => {
            if (newItem && Object.keys(newItem).length > 0) {
                const incoming = newItem as Partial<AttributeItem>
                localItem.value = { ...defaultItem, ...incoming }
                resetConstants()
                dialog.value = true
                // Remount the table so it re-fires @update:options -> loadConstants for this attribute.
                tableKey.value++
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
            } else {
                // Snapshot the freshly-loaded form as the clean baseline for dirty-tracking.
                capture()
            }
        }
    )
</script>
