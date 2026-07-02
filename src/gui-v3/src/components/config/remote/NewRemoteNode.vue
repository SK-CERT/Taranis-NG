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
                :title="isEdit ? t('remote.nodes.edit') : t('remote.nodes.add_new')"
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
                        :label="t('remote.nodes.name')"
                        variant="outlined"
                        density="comfortable"
                        class="mb-3"
                        :rules="[(v) => !!v || t('error.required')]"
                        :disabled="saving"
                    />

                    <v-textarea
                        v-model="localItem.description"
                        :label="t('remote.nodes.description')"
                        variant="outlined"
                        density="comfortable"
                        rows="3"
                        class="mb-3"
                        :disabled="saving"
                    />

                    <v-text-field
                        v-model="localItem.remote_url"
                        :label="t('remote.nodes.remote_url')"
                        variant="outlined"
                        density="comfortable"
                        class="mb-3"
                        :rules="[(v) => !!v || t('error.required')]"
                        :disabled="saving"
                    />

                    <v-text-field
                        v-model="localItem.events_url"
                        :label="t('remote.nodes.event_url')"
                        variant="outlined"
                        density="comfortable"
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

                    <v-row class="mb-1">
                        <v-col
                            cols="12"
                            sm="6"
                            class="py-0"
                        >
                            <v-checkbox
                                v-model="localItem.sync_news_items"
                                :label="t('remote.nodes.sync_news_items')"
                                color="primary"
                                density="comfortable"
                                hide-details
                                :disabled="saving"
                            />
                        </v-col>
                        <v-col
                            cols="12"
                            sm="6"
                            class="py-0"
                        >
                            <v-checkbox
                                v-model="localItem.sync_report_items"
                                :label="t('remote.nodes.sync_report_items')"
                                color="primary"
                                density="comfortable"
                                hide-details
                                :disabled="saving"
                            />
                        </v-col>
                    </v-row>

                    <v-select
                        v-model="localItem.osint_source_group_id"
                        :items="osintSourceGroups"
                        item-title="name"
                        item-value="id"
                        :label="t('remote.nodes.osint_source_group')"
                        variant="outlined"
                        density="comfortable"
                        class="mb-3"
                        clearable
                        :disabled="saving || !localItem.sync_news_items"
                    />

                    <v-btn
                        v-if="canConnect"
                        variant="tonal"
                        color="primary"
                        prepend-icon="mdi-lan-connect"
                        class="mt-2"
                        :loading="connecting"
                        :disabled="saving"
                        @click="handleConnect"
                    >
                        {{ t('remote.nodes.connect') }}
                    </v-btn>

                    <v-switch
                        v-model="localItem.enabled"
                        :label="t('remote.nodes.enabled')"
                        color="primary"
                        :disabled="saving"
                    />
                </v-form>

                <v-alert
                    v-if="showConnectInfo"
                    type="success"
                    variant="tonal"
                    class="mt-4"
                    closable
                    @click:close="showConnectInfo = false"
                >
                    {{ t('remote.nodes.connect_info') }}
                </v-alert>

                <v-alert
                    v-if="showConnectError"
                    type="error"
                    variant="tonal"
                    class="mt-4"
                    closable
                    @click:close="showConnectError = false"
                >
                    {{ t('remote.nodes.connect_error') }}
                </v-alert>

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
                    {{ t('remote.nodes.error') }}
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
    import { createNewRemoteNode, updateRemoteNode, connectRemoteNode, getAllOSINTSourceGroups } from '@/api/config'

    type RemoteNodeItem = {
        id: string | number | null
        name: string
        description: string
        remote_url: string
        events_url: string
        api_key: string
        enabled: boolean
        sync_news_items: boolean
        sync_report_items: boolean
        osint_source_group_id: string | number | null
        [key: string]: unknown
    }

    type OSINTSourceGroup = {
        id: string | number
        name?: string
        [key: string]: unknown
    }

    type FormValidationResult = {
        valid: boolean
    }

    const props = withDefaults(
        defineProps<{
            editItem?: Partial<RemoteNodeItem> | null
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
    const connecting = ref(false)
    const dialog = ref(false)
    const showApiKey = ref(false)
    const showConnectInfo = ref(false)
    const showConnectError = ref(false)
    const osintSourceGroups = ref<OSINTSourceGroup[]>([])

    const defaultItem: RemoteNodeItem = {
        id: null,
        name: '',
        description: '',
        remote_url: '',
        events_url: '',
        api_key: '',
        enabled: true,
        sync_news_items: false,
        sync_report_items: false,
        osint_source_group_id: null
    }

    const localItem = ref<RemoteNodeItem>({ ...defaultItem })
    const isEdit = computed(() => !!localItem.value.id)

    const canCreate = computed(() => checkPermission('CONFIG_REMOTE_NODE_CREATE'))

    // Connecting needs a persisted node id (GET /remote-nodes/{id}/connect), so the
    // button is only offered once the node exists (edit mode) and is enabled.
    const canConnect = computed(() => isEdit.value && localItem.value.enabled === true && checkPermission('CONFIG_REMOTE_NODE_UPDATE'))

    onMounted(async () => {
        await loadOSINTSourceGroups()
    })

    async function loadOSINTSourceGroups(): Promise<void> {
        try {
            const response = (await getAllOSINTSourceGroups({ search: '' })) as {
                items?: OSINTSourceGroup[]
                data?: { items?: OSINTSourceGroup[] }
            }
            osintSourceGroups.value = response.items || response.data?.items || []
        } catch (error) {
            console.error('Error loading OSINT source groups:', error)
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
                await updateRemoteNode(localItem.value)
            } else {
                // Backend requires an integer id even on create (ignored); null fails validation.
                await createNewRemoteNode({ ...localItem.value, id: -1 })
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

    async function handleConnect(): Promise<void> {
        showValidationError.value = false
        showError.value = false
        showConnectInfo.value = false
        showConnectError.value = false

        const { valid } = (await formRef.value.validate()) as FormValidationResult
        if (!valid) {
            showValidationError.value = true
            return
        }

        connecting.value = true
        try {
            // Persist any pending edits, then ask the core to connect to the node.
            await updateRemoteNode(localItem.value)
            await connectRemoteNode(localItem.value)
            showConnectInfo.value = true
        } catch (error) {
            showConnectError.value = true
        } finally {
            connecting.value = false
        }
    }

    function closeDialog(): void {
        showValidationError.value = false
        showError.value = false
        showConnectInfo.value = false
        showConnectError.value = false
        showApiKey.value = false
        formRef.value?.reset()
        localItem.value = { ...defaultItem }
        dialog.value = false
    }

    const { confirmVisible, capture, requestClose, continueEditing, saveAndClose, discardAndClose } = useUnsavedChanges({
        getState: () => localItem.value,
        save: persist,
        close: closeDialog
    })

    watch(
        () => props.editItem,
        (newItem) => {
            if (newItem && Object.keys(newItem).length > 0) {
                localItem.value = { ...defaultItem, ...newItem }
                // Opening for edit: the parent sets editItem, so reveal the dialog.
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
                showConnectInfo.value = false
                showConnectError.value = false
                saving.value = false
            } else {
                // Snapshot the freshly-loaded form as the clean baseline for dirty-tracking.
                capture()
            }
        }
    )
</script>
