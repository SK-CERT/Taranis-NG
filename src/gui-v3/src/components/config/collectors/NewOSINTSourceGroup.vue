<template>
    <v-dialog
        v-model="dialog"
        max-width="800"
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
                :title="isEdit ? t('collectors.groups.edit') : t('collectors.groups.add_new')"
                :saving="saving"
                :show-save="!isReadOnly"
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
                        :label="t('collectors.groups.name')"
                        variant="outlined"
                        density="comfortable"
                        class="mb-3"
                        :rules="[(v) => !!v || t('error.required')]"
                        :disabled="saving || isReadOnly"
                    />

                    <v-textarea
                        v-model="localItem.description"
                        :label="t('collectors.groups.description')"
                        variant="outlined"
                        density="comfortable"
                        rows="3"
                        class="mb-3"
                        :disabled="saving || isReadOnly"
                    />

                    <!-- OSINT sources that belong to this group -->
                    <EntitySelectTable
                        v-model="selectedSources"
                        :title="t('collectors.groups.osint_sources')"
                        :items="sourceItems"
                        :headers="sourceHeaders"
                        :loading="loadingSources"
                        :disabled="saving || isReadOnly"
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
                    {{ t('collectors.groups.error') }}
                </v-alert>
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
    import { useConfigStore } from '@/stores/config'
    import EntitySelectTable from '@/components/common/EntitySelectTable.vue'
    import { createNewOSINTSourceGroup, updateOSINTSourceGroup } from '@/api/config'

    type OSINTSourceGroupItem = {
        id: string | number | null
        name: string
        description: string
        default: boolean
        osint_sources?: Array<{ id: string | number }>
        [key: string]: unknown
    }

    type FormValidationResult = {
        valid: boolean
    }

    const props = withDefaults(
        defineProps<{
            editItem?: Partial<OSINTSourceGroupItem> | null
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

    // Ids of the OSINT sources assigned to this group (v-model of the sources table).
    const selectedSources = ref<Array<string | number>>([])
    const loadingSources = ref(false)

    const sourceHeaders = [
        { title: t('card_item.name'), key: 'name' },
        { title: t('card_item.description'), key: 'description' }
    ]

    const sourceItems = computed(() => configStore.osintSources.items as Array<{ id: string | number; name?: string; description?: string }>)

    const defaultItem: OSINTSourceGroupItem = {
        id: '',
        name: '',
        description: '',
        default: false,
        osint_sources: []
    }

    const localItem = ref<OSINTSourceGroupItem>({ ...defaultItem })
    const isEdit = computed(() => !!localItem.value.id)
    // The default group cannot be modified (backend forbids it): open it as a read-only view.
    const isReadOnly = computed(() => localItem.value.default === true)

    const canCreate = computed(() => checkPermission('CONFIG_OSINT_SOURCE_GROUP_CREATE'))

    onMounted(async () => {
        // Load all sources so they can be assigned to the group.
        loadingSources.value = true
        try {
            await configStore.loadOSINTSources({ search: '' })
        } catch (error) {
            console.error('Error loading OSINT sources:', error)
        } finally {
            loadingSources.value = false
        }
    })

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
            // Backend requires all fields (id as a string, plus osint_sources). Build an
            // explicit payload: empty id for new groups, and preserve existing sources on edit.
            const payload = {
                id: localItem.value.id ?? '',
                name: localItem.value.name ?? '',
                // Backend fields are non-nullable strings; a group may have a null description.
                description: localItem.value.description ?? '',
                default: localItem.value.default ?? false,
                osint_sources: selectedSources.value.map((id) => ({ id }))
            }

            if (isEdit.value) {
                await updateOSINTSourceGroup(payload)
            } else {
                await createNewOSINTSourceGroup(payload)
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
        selectedSources.value = []
        dialog.value = false
    }

    watch(
        () => props.editItem,
        (newItem) => {
            if (newItem && Object.keys(newItem).length > 0) {
                localItem.value = { ...defaultItem, ...newItem }
                // Pre-select the sources already assigned to the group.
                selectedSources.value = (newItem.osint_sources ?? [])
                    .filter((source) => source && source.id != null)
                    .map((source) => source.id)
                dialog.value = true
            } else {
                localItem.value = { ...defaultItem }
                selectedSources.value = []
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
