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
                :title="isEdit ? t('word_lists.edit') : t('word_lists.add_new')"
                :saving="saving"
                @cancel="requestClose"
                @save="saveAndClose"
            />

            <v-card-text>
                <v-form
                    ref="formRef"
                    @submit.prevent="saveAndClose"
                >
                    <v-row>
                        <v-col cols="12">
                            <v-text-field
                                v-model="localItem.name"
                                :label="t('word_lists.name')"
                                variant="outlined"
                                density="comfortable"
                                :rules="[(v) => !!v || t('error.required')]"
                                :disabled="saving"
                            />
                        </v-col>
                        <v-col cols="12">
                            <v-textarea
                                v-model="localItem.description"
                                :label="t('word_lists.description')"
                                variant="outlined"
                                density="comfortable"
                                rows="3"
                                :disabled="saving"
                            />
                        </v-col>
                        <v-col cols="12">
                            <v-checkbox
                                v-model="localItem.use_for_stop_words"
                                :label="t('word_lists.use_for_stop_words')"
                                color="primary"
                                :disabled="saving"
                            />
                        </v-col>
                    </v-row>

                    <v-divider class="my-4" />

                    <!-- Categories -->
                    <EditableEntityTable
                        v-model="localItem.categories"
                        :title="t('word_lists.categories')"
                        :headers="categoryHeaders"
                        :default-item="newCategory"
                        :add-title="t('word_lists.add_category')"
                        :edit-title="t('word_lists.edit_category')"
                        :no-data-text="t('word_lists.no_categories')"
                        :disabled="saving"
                        dialog-max-width="900"
                    >
                        <template #item.name="{ item }">
                            <v-icon
                                class="mr-2 text-medium-emphasis"
                                size="small"
                                >mdi-folder-outline</v-icon
                            >
                            <strong>{{ item.name || t('word_lists.category') }}</strong>
                        </template>
                        <template #item.word_count="{ item }">
                            {{ (item.entries || []).length }}
                        </template>

                        <template #form="{ item }">
                            <v-text-field
                                v-model="item.name"
                                :label="t('word_lists.name')"
                                variant="outlined"
                                density="comfortable"
                                class="mb-3"
                                :rules="[(v) => !!v || t('error.required')]"
                            />
                            <v-textarea
                                v-model="item.description"
                                :label="t('word_lists.description')"
                                variant="outlined"
                                density="comfortable"
                                rows="2"
                                class="mb-3"
                            />
                            <v-text-field
                                v-model="item.link"
                                :label="t('word_lists.link')"
                                variant="outlined"
                                density="comfortable"
                                class="mb-3"
                                :hint="t('word_lists.link_hint')"
                            />

                            <EditableEntityTable
                                v-model="item.entries"
                                :title="t('word_lists.words')"
                                :headers="wordHeaders"
                                :default-item="newWord"
                                :add-title="t('word_lists.add_word')"
                                :edit-title="t('word_lists.edit_word')"
                                :no-data-text="t('word_lists.no_words')"
                                dialog-max-width="500"
                            >
                                <template #form="{ item: word }">
                                    <v-text-field
                                        v-model="word.value"
                                        :label="t('word_lists.value')"
                                        variant="outlined"
                                        density="comfortable"
                                        class="mb-3"
                                        :rules="[(v) => !!v || t('error.required')]"
                                    />
                                    <v-text-field
                                        v-model="word.description"
                                        :label="t('word_lists.description')"
                                        variant="outlined"
                                        density="comfortable"
                                    />
                                </template>
                            </EditableEntityTable>
                        </template>
                    </EditableEntityTable>

                    <v-alert
                        v-if="showValidationError"
                        type="error"
                        density="compact"
                        class="mb-3 mt-4"
                    >
                        {{ t('error.validation') }}
                    </v-alert>

                    <v-alert
                        v-if="showError"
                        type="error"
                        density="compact"
                        class="mb-3 mt-4"
                    >
                        {{ t('word_lists.error') }}
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
    import { ref, computed, watch } from 'vue'
    import { useI18n } from 'vue-i18n'
    import AddNewButton from '@/components/common/buttons/AddNewButton.vue'
    import DialogToolbar from '@/components/common/dialogs/DialogToolbar.vue'
    import UnsavedChangesDialog from '@/components/common/dialogs/UnsavedChangesDialog.vue'
    import { useUnsavedChanges } from '@/composables/useUnsavedChanges'
    import EditableEntityTable from '@/components/common/EditableEntityTable.vue'
    import { useAuth } from '@/composables/useAuth'
    import { createNewWordList, updateWordList } from '@/api/config'

    type WordEntry = {
        value: string
        description: string
        [key: string]: unknown
    }

    type WordCategory = {
        name: string
        description: string
        link: string
        entries: WordEntry[]
        [key: string]: unknown
    }

    type WordListItem = {
        id: string | number | null
        name: string
        description: string
        use_for_stop_words: boolean
        categories: WordCategory[]
        [key: string]: unknown
    }

    type HeaderEntry = {
        title: string
        key: string
        sortable?: boolean
        width?: string
        align?: 'start' | 'center' | 'end'
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
    const showValidationError = ref(false)
    const showError = ref(false)

    const defaultItem: WordListItem = {
        id: null,
        name: '',
        description: '',
        use_for_stop_words: false,
        categories: []
    }

    const localItem = ref<WordListItem>({ ...defaultItem })

    const isEdit = computed(() => !!localItem.value.id)
    const canCreate = computed(() => checkPermission('CONFIG_WORD_LIST_CREATE'))

    const categoryHeaders: HeaderEntry[] = [
        { title: t('word_lists.name'), key: 'name', sortable: false },
        { title: t('word_lists.description'), key: 'description', sortable: false },
        { title: t('word_lists.words'), key: 'word_count', sortable: false, width: '10%', align: 'center' },
        { title: t('settings.actions'), key: 'actions', sortable: false, width: '15%', align: 'end' }
    ]

    const wordHeaders: HeaderEntry[] = [
        { title: t('word_lists.value'), key: 'value', sortable: false, width: '40%' },
        { title: t('word_lists.description'), key: 'description', sortable: false, width: '45%' },
        { title: t('settings.actions'), key: 'actions', sortable: false, width: '15%', align: 'end' }
    ]

    const newCategory = (): WordCategory => ({ name: '', description: '', link: '', entries: [] })
    const newWord = (): WordEntry => ({ value: '', description: '' })

    // Watch for edit item changes
    watch(
        () => props.editItem,
        (newVal) => {
            if (newVal) {
                const incoming = JSON.parse(JSON.stringify(newVal)) as Partial<WordListItem>
                localItem.value = { ...defaultItem, ...incoming, categories: incoming.categories || [] }

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

    const resetForm = (): void => {
        localItem.value = { ...defaultItem, categories: [] }
        showValidationError.value = false
        showError.value = false
        if (formRef.value) {
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

        if (!valid) {
            showValidationError.value = true
            return false
        }

        saving.value = true

        try {
            if (isEdit.value) {
                await updateWordList(localItem.value)
                window.dispatchEvent(
                    new CustomEvent('notification', {
                        detail: { type: 'success', loc: 'common.updated_successfully' }
                    })
                )
            } else {
                // Backend requires an integer id even on create (ignored); null/missing fails the constructor.
                await createNewWordList({ ...localItem.value, id: -1 })
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
        getState: () => localItem.value,
        save: persist,
        close: closeDialog
    })
</script>

<style scoped>
    .w-100 {
        width: 100%;
    }
</style>
