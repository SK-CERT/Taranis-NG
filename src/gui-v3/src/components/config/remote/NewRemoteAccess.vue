<template>
    <v-dialog
        v-model="dialog"
        max-width="600"
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
                :title="isEdit ? t('remote.access.edit') : t('remote.access.add_new')"
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
                        :label="t('remote.access.name')"
                        variant="outlined"
                        density="comfortable"
                        class="mb-3"
                        :rules="[(v) => !!v || t('error.required')]"
                        :disabled="saving"
                    />

                    <v-textarea
                        v-model="localItem.description"
                        :label="t('remote.access.description')"
                        variant="outlined"
                        density="comfortable"
                        rows="3"
                        class="mb-3"
                        :disabled="saving"
                    />

                    <v-text-field
                        v-model="localItem.api_key"
                        :label="t('settings.api_key')"
                        :type="showApiKey ? 'text' : 'password'"
                        :append-inner-icon="showApiKey ? 'mdi-eye-off' : 'mdi-eye'"
                        variant="outlined"
                        density="comfortable"
                        class="mb-3"
                        :disabled="saving"
                        @click:append-inner="showApiKey = !showApiKey"
                    />

                    <v-switch
                        v-model="localItem.enabled"
                        :label="t('remote.access.enabled')"
                        color="primary"
                        :disabled="saving"
                    />

                    <v-autocomplete
                        v-model="selectedOsintSources"
                        :items="osintSources"
                        item-title="name"
                        item-value="id"
                        :label="t('remote.access.osint_sources')"
                        variant="outlined"
                        density="comfortable"
                        class="mb-3"
                        multiple
                        chips
                        closable-chips
                        clearable
                        :loading="loadingSources"
                        :disabled="saving"
                    />

                    <v-autocomplete
                        v-model="selectedReportItemTypes"
                        :items="reportItemTypes"
                        item-title="title"
                        item-value="id"
                        :label="t('remote.access.report_item_types')"
                        variant="outlined"
                        density="comfortable"
                        class="mb-3"
                        multiple
                        chips
                        closable-chips
                        clearable
                        :loading="loadingTypes"
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
                    {{ t('remote.access.error') }}
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
    import { useAuth } from '@/composables/useAuth'
    import { useUnsavedChanges } from '@/composables/useUnsavedChanges'
    import { createNewRemoteAccess, updateRemoteAccess, getAllOSINTSources, getAllReportItemTypes } from '@/api/config'

    type IdRef = { id: string | number; [key: string]: unknown }

    type OSINTSource = { id: string | number; name?: string; [key: string]: unknown }
    type ReportItemType = { id: string | number; title?: string; [key: string]: unknown }

    type RemoteAccessItem = {
        id: string | number | null
        name: string
        description: string
        api_key: string
        enabled: boolean
        osint_sources: IdRef[]
        report_item_types: IdRef[]
        [key: string]: unknown
    }

    type FormValidationResult = {
        valid: boolean
    }

    const props = withDefaults(
        defineProps<{
            editItem?: Partial<RemoteAccessItem> | null
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
    const showApiKey = ref(false)
    const loadingSources = ref(false)
    const loadingTypes = ref(false)

    const osintSources = ref<OSINTSource[]>([])
    const reportItemTypes = ref<ReportItemType[]>([])
    const selectedOsintSources = ref<(string | number)[]>([])
    const selectedReportItemTypes = ref<(string | number)[]>([])

    const defaultItem: RemoteAccessItem = {
        id: null,
        name: '',
        description: '',
        api_key: '',
        enabled: true,
        osint_sources: [],
        report_item_types: []
    }

    const localItem = ref<RemoteAccessItem>({ ...defaultItem })
    const isEdit = computed(() => !!localItem.value.id)

    const canCreate = computed(() => checkPermission('CONFIG_REMOTE_ACCESS_CREATE'))

    onMounted(async () => {
        await Promise.all([loadOsintSources(), loadReportItemTypes()])
    })

    async function loadOsintSources(): Promise<void> {
        loadingSources.value = true
        try {
            const response = (await getAllOSINTSources({ search: '' })) as {
                items?: OSINTSource[]
                data?: { items?: OSINTSource[] }
            }
            osintSources.value = response.items || response.data?.items || []
        } catch (error) {
            console.error('Error loading OSINT sources:', error)
        } finally {
            loadingSources.value = false
        }
    }

    async function loadReportItemTypes(): Promise<void> {
        loadingTypes.value = true
        try {
            const response = (await getAllReportItemTypes({ search: '' })) as {
                items?: ReportItemType[]
                data?: { items?: ReportItemType[] }
            }
            reportItemTypes.value = response.items || response.data?.items || []
        } catch (error) {
            console.error('Error loading report item types:', error)
        } finally {
            loadingTypes.value = false
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
            const payload: RemoteAccessItem = {
                ...localItem.value,
                osint_sources: selectedOsintSources.value.map((id) => ({ id })),
                report_item_types: selectedReportItemTypes.value.map((id) => ({ id }))
            }

            if (isEdit.value) {
                await updateRemoteAccess(payload)
            } else {
                // Backend requires an integer id even on create (ignored); null fails validation.
                await createNewRemoteAccess({ ...payload, id: -1 })
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
        showValidationError.value = false
        showError.value = false
        showApiKey.value = false
        formRef.value?.reset()
        localItem.value = { ...defaultItem }
        selectedOsintSources.value = []
        selectedReportItemTypes.value = []
        dialog.value = false
    }

    const { confirmVisible, capture, requestClose, continueEditing, saveAndClose, discardAndClose } = useUnsavedChanges({
        getState: () => ({ item: localItem.value, sources: selectedOsintSources.value, types: selectedReportItemTypes.value }),
        save: persist,
        close: closeDialog
    })

    watch(
        () => props.editItem,
        (newItem) => {
            if (newItem && Object.keys(newItem).length > 0) {
                localItem.value = { ...defaultItem, ...newItem }
                selectedOsintSources.value = (newItem.osint_sources ?? []).map((s) => s.id)
                selectedReportItemTypes.value = (newItem.report_item_types ?? []).map((tp) => tp.id)
                // Opening for edit: the parent sets editItem, so reveal the dialog.
                dialog.value = true
            } else {
                localItem.value = { ...defaultItem }
                selectedOsintSources.value = []
                selectedReportItemTypes.value = []
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
