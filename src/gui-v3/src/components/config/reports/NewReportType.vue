<template>
    <v-dialog
        v-model="dialog"
        max-width="1200"
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
                :title="isEdit ? t('reports.types.edit') : t('reports.types.add_new')"
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
                        v-model="localItem.title"
                        :label="t('reports.types.name')"
                        variant="outlined"
                        density="comfortable"
                        class="mb-3"
                        :rules="[(v) => !!v || t('error.required')]"
                        :disabled="saving"
                    />

                    <v-textarea
                        v-model="localItem.description"
                        :label="t('reports.types.description')"
                        variant="outlined"
                        density="comfortable"
                        rows="3"
                        class="mb-3"
                        :disabled="saving"
                    />

                    <!-- Attribute groups -->
                    <div class="d-flex align-center mb-3">
                        <h3 class="text-h6">
                            {{ t('reports.types.attribute_groups') }}
                        </h3>
                        <v-spacer />
                        <AddNewButton
                            :disabled="saving"
                            @click="addGroup"
                        />
                    </div>

                    <v-card
                        v-for="(group, index) in localItem.attribute_groups"
                        :key="group.id + '-' + index"
                        variant="outlined"
                        class="mb-4"
                    >
                        <v-toolbar
                            color="grey-lighten-3"
                            density="compact"
                        >
                            <v-spacer />
                            <ActionButton
                                icon="mdi-arrow-up-bold"
                                :title="t('common.up')"
                                :disabled="saving"
                                @click="moveGroup(index, -1)"
                            />
                            <ActionButton
                                icon="mdi-arrow-down-bold"
                                :title="t('common.down')"
                                :disabled="saving"
                                @click="moveGroup(index, 1)"
                            />
                            <ActionButton
                                action="delete"
                                :title="t('common.delete')"
                                :disabled="saving"
                                @click="deleteGroup(index)"
                            />
                        </v-toolbar>

                        <v-card-text>
                            <v-text-field
                                v-model="group.title"
                                :label="t('reports.types.name')"
                                variant="outlined"
                                density="comfortable"
                                class="mb-3"
                                :disabled="saving"
                            />
                            <v-textarea
                                v-model="group.description"
                                :label="t('reports.types.description')"
                                variant="outlined"
                                density="comfortable"
                                rows="2"
                                class="mb-3"
                                :disabled="saving"
                            />
                            <v-text-field
                                v-model="group.section_title"
                                :label="t('reports.types.section_title')"
                                variant="outlined"
                                density="comfortable"
                                class="mb-3"
                                :disabled="saving"
                            />

                            <AttributeTable
                                v-model="group.attribute_group_items"
                                :attribute-templates="attributeTemplates"
                                :ai-providers="aiProviders"
                                :disabled="saving"
                            />
                        </v-card-text>
                    </v-card>
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
                    {{ t('reports.types.error') }}
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
    import AddNewButton from '@/components/common/buttons/AddNewButton.vue'
    import DialogToolbar from '@/components/common/dialogs/DialogToolbar.vue'
    import UnsavedChangesDialog from '@/components/common/dialogs/UnsavedChangesDialog.vue'
    import { useUnsavedChanges } from '@/composables/useUnsavedChanges'
    import ActionButton from '@/components/common/buttons/ActionButton.vue'
    import AttributeTable, { type AttributeGroupItem } from '@/components/config/reports/AttributeTable.vue'
    import { useAuth } from '@/composables/useAuth'
    import { createNewReportItemType, updateReportItemType, getAllAttributes, getAllAiProviders } from '@/api/config'

    type AttributeGroup = {
        id: number
        title: string
        description: string
        section: number | null
        section_title: string
        index: number
        attribute_group_items: AttributeGroupItem[]
    }

    type ReportTypeItem = {
        id: number | null
        title: string
        description: string
        attribute_groups: AttributeGroup[]
        [key: string]: unknown
    }

    type FormValidationResult = {
        valid: boolean
    }

    // Shape of an attribute group item as returned by the backend (nested `attribute`).
    type IncomingGroupItem = {
        id?: number
        index?: number
        title?: string
        description?: string
        min_occurrence?: number
        max_occurrence?: number
        attribute?: { id?: number; name?: string }
        ai_provider_id?: number | null
        ai_prompt?: string | null
    }

    type IncomingGroup = {
        id?: number
        title?: string
        description?: string
        section?: number | null
        section_title?: string | null
        index?: number
        attribute_group_items?: IncomingGroupItem[]
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

    const attributeTemplates = ref<{ id: number; name: string }[]>([])
    const aiProviders = ref<{ id: number; name: string }[]>([])

    const defaultItem = (): ReportTypeItem => ({
        id: null,
        title: '',
        description: '',
        attribute_groups: []
    })

    const localItem = ref<ReportTypeItem>(defaultItem())
    const isEdit = computed(() => !!localItem.value.id)

    const canCreate = computed(() => checkPermission('CONFIG_REPORT_TYPE_CREATE'))

    const notify = (type: 'success' | 'error', loc: string): void => {
        window.dispatchEvent(new CustomEvent('notification', { detail: { type, loc } }))
    }

    const addGroup = (): void => {
        localItem.value.attribute_groups.push({
            id: -1,
            title: '',
            description: '',
            section: -1,
            section_title: '',
            index: localItem.value.attribute_groups.length,
            attribute_group_items: []
        })
    }

    const deleteGroup = (index: number): void => {
        localItem.value.attribute_groups.splice(index, 1)
    }

    const moveGroup = (index: number, offset: number): void => {
        const target = index + offset
        const groups = localItem.value.attribute_groups
        if (target < 0 || target >= groups.length) {
            return
        }
        const [moved] = groups.splice(index, 1)
        if (!moved) {
            return
        }
        groups.splice(target, 0, moved)
    }

    const mapIncoming = (incoming: Record<string, unknown>): ReportTypeItem => {
        const src = incoming as { id?: number; title?: string; description?: string; attribute_groups?: IncomingGroup[] }
        return {
            id: src.id ?? null,
            title: src.title ?? '',
            description: src.description ?? '',
            attribute_groups: (src.attribute_groups ?? []).map((group, gi) => ({
                id: group.id ?? -1,
                title: group.title ?? '',
                description: group.description ?? '',
                section: group.section ?? -1,
                section_title: group.section_title ?? '',
                index: group.index ?? gi,
                attribute_group_items: (group.attribute_group_items ?? []).map((item, ii) => ({
                    id: item.id ?? -1,
                    index: item.index ?? ii,
                    attribute_id: item.attribute?.id ?? -1,
                    attribute_name: item.attribute?.name ?? '',
                    title: item.title ?? '',
                    description: item.description ?? '',
                    min_occurrence: item.min_occurrence ?? 0,
                    max_occurrence: item.max_occurrence ?? 1,
                    ai_provider_id: item.ai_provider_id ?? null,
                    ai_prompt: item.ai_prompt ?? ''
                }))
            }))
        }
    }

    const loadTemplates = async (): Promise<void> => {
        try {
            const [attrRes, aiRes] = await Promise.all([getAllAttributes({ search: '' }), getAllAiProviders({ search: '' })])
            attributeTemplates.value = (attrRes as { data?: { items?: { id: number; name: string }[] } }).data?.items ?? []
            aiProviders.value = (aiRes as { data?: { items?: { id: number; name: string }[] } }).data?.items ?? []
        } catch (error) {
            console.error('Error loading attribute templates / AI providers:', error)
        }
    }

    // Renumber groups and items by their current order before sending to the backend.
    const buildPayload = (): Record<string, unknown> => ({
        id: localItem.value.id ?? -1,
        title: localItem.value.title,
        description: localItem.value.description,
        attribute_groups: localItem.value.attribute_groups.map((group, gi) => ({
            id: group.id,
            title: group.title,
            description: group.description,
            section: group.section,
            section_title: group.section_title,
            index: gi,
            attribute_group_items: group.attribute_group_items.map((item, ii) => ({
                id: item.id,
                index: ii,
                attribute_id: item.attribute_id,
                title: item.title,
                description: item.description,
                min_occurrence: Number(item.min_occurrence) || 0,
                max_occurrence: Number(item.max_occurrence) || 0,
                ai_provider_id: item.ai_provider_id,
                ai_prompt: item.ai_prompt
            }))
        }))
    })

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
            const payload = buildPayload()
            if (isEdit.value) {
                await updateReportItemType(payload)
                notify('success', 'common.updated_successfully')
            } else {
                await createNewReportItemType(payload)
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

    function closeDialog(): void {
        showValidationError.value = false
        showError.value = false
        formRef.value?.reset()
        localItem.value = defaultItem()
        dialog.value = false
    }

    const { confirmVisible, capture, requestClose, continueEditing, saveAndClose, discardAndClose } = useUnsavedChanges({
        getState: () => localItem.value,
        save: persist,
        close: closeDialog
    })

    onMounted(loadTemplates)

    watch(
        () => props.editItem,
        (newItem) => {
            if (newItem && Object.keys(newItem).length > 0) {
                localItem.value = mapIncoming(newItem)
                dialog.value = true
            } else {
                localItem.value = defaultItem()
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
