<template>
    <v-dialog
        v-model="dialog"
        max-width="1200"
        persistent
        scrollable
        fullscreen
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
                @cancel="cancel"
                @save="handleSubmit"
            />

            <v-card-text>
                <v-form
                    ref="formRef"
                    @submit.prevent="handleSubmit"
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

                    <v-row>
                        <v-col cols="12">
                            <div class="d-flex align-center mb-3">
                                <h3 class="text-h6">
                                    {{ t('word_lists.categories') }}
                                </h3>
                                <v-spacer />
                                <v-btn
                                    color="primary"
                                    prepend-icon="mdi-plus"
                                    :disabled="saving"
                                    @click="addCategory"
                                >
                                    {{ t('word_lists.new_category') }}
                                </v-btn>
                            </div>

                            <!-- Categories -->
                            <v-expansion-panels
                                v-model="expandedPanels"
                                multiple
                            >
                                <v-expansion-panel
                                    v-for="(category, index) in localItem.categories"
                                    :key="index"
                                    :value="index"
                                >
                                    <v-expansion-panel-title>
                                        <div class="d-flex align-center w-100">
                                            <v-icon class="mr-2"> mdi-folder-outline </v-icon>
                                            <strong>
                                                {{ category.name || t('word_lists.category') + ' ' + (index + 1) }}
                                            </strong>
                                            <v-spacer />
                                            <v-btn
                                                icon
                                                size="small"
                                                variant="text"
                                                color="error"
                                                :disabled="saving"
                                                @click.stop="deleteCategory(index)"
                                            >
                                                <v-icon color="error">
                                                    {{ ICONS.DELETE }}
                                                </v-icon>
                                            </v-btn>
                                        </div>
                                    </v-expansion-panel-title>

                                    <v-expansion-panel-text>
                                        <v-row>
                                            <v-col cols="12">
                                                <v-text-field
                                                    v-model="category.name"
                                                    :label="t('word_lists.name')"
                                                    variant="outlined"
                                                    density="comfortable"
                                                    :disabled="saving"
                                                />
                                            </v-col>
                                            <v-col cols="12">
                                                <v-textarea
                                                    v-model="category.description"
                                                    :label="t('word_lists.description')"
                                                    variant="outlined"
                                                    density="comfortable"
                                                    rows="2"
                                                    :disabled="saving"
                                                />
                                            </v-col>
                                            <v-col cols="12">
                                                <v-text-field
                                                    v-model="category.link"
                                                    :label="t('word_lists.link')"
                                                    variant="outlined"
                                                    density="comfortable"
                                                    hint="Optional URL for downloading word entries"
                                                    :disabled="saving"
                                                />
                                            </v-col>
                                        </v-row>

                                        <v-divider class="my-3" />

                                        <!-- Words/Entries for this category -->
                                        <div class="mb-3">
                                            <div class="d-flex align-center mb-2">
                                                <h4 class="text-subtitle-1">
                                                    {{ t('word_lists.words') }}
                                                </h4>
                                                <v-spacer />
                                                <v-btn
                                                    size="small"
                                                    color="primary"
                                                    prepend-icon="mdi-plus"
                                                    :disabled="saving"
                                                    @click="addWord(index)"
                                                >
                                                    {{ t('word_lists.new_word') }}
                                                </v-btn>
                                            </div>

                                            <v-data-table
                                                :headers="wordHeaders"
                                                :items="category.entries || []"
                                                density="compact"
                                                :items-per-page="5"
                                            >
                                                <template #item.value="{ item }">
                                                    <v-text-field
                                                        v-model="item.value"
                                                        variant="outlined"
                                                        density="compact"
                                                        hide-details
                                                        :disabled="saving"
                                                    />
                                                </template>
                                                <template #item.description="{ item }">
                                                    <v-text-field
                                                        v-model="item.description"
                                                        variant="outlined"
                                                        density="compact"
                                                        hide-details
                                                        :disabled="saving"
                                                    />
                                                </template>
                                                <template #item.actions="{ item }">
                                                    <v-btn
                                                        icon
                                                        size="small"
                                                        variant="text"
                                                        color="error"
                                                        :disabled="saving"
                                                        @click="deleteWord(index, category.entries.indexOf(item))"
                                                    >
                                                        <v-icon color="error">
                                                            {{ ICONS.DELETE }}
                                                        </v-icon>
                                                    </v-btn>
                                                </template>
                                                <template #no-data>
                                                    <div class="text-center pa-4 text-grey">
                                                        {{ t('word_lists.no_words') }}
                                                    </div>
                                                </template>
                                            </v-data-table>
                                        </div>
                                    </v-expansion-panel-text>
                                </v-expansion-panel>
                            </v-expansion-panels>

                            <div
                                v-if="localItem.categories.length === 0"
                                class="text-center pa-8 text-grey"
                            >
                                <v-icon
                                    size="64"
                                    color="grey-lighten-1"
                                >
                                    mdi-folder-open-outline
                                </v-icon>
                                <div class="text-h6 mt-2">
                                    {{ t('word_lists.no_categories') }}
                                </div>
                                <div class="text-body-2">
                                    {{ t('word_lists.add_category_hint') }}
                                </div>
                            </div>
                        </v-col>
                    </v-row>

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
    </v-dialog>
</template>

<script setup lang="ts">
    import { ref, computed, watch } from 'vue'
    import { ICONS } from '@/config/ui-constants'
    import { useI18n } from 'vue-i18n'
    import AddNewButton from '@/components/common/buttons/AddNewButton.vue'
    import DialogToolbar from '@/components/common/dialogs/DialogToolbar.vue'
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
    const expandedPanels = ref<number[]>([])

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

    const wordHeaders: HeaderEntry[] = [
        { title: t('word_lists.value'), key: 'value', sortable: true, width: '40%' },
        { title: t('word_lists.description'), key: 'description', sortable: false, width: '50%' },
        { title: t('settings.actions'), key: 'actions', sortable: false, width: '10%', align: 'center' }
    ]

    // Watch for edit item changes
    watch(
        () => props.editItem,
        (newVal) => {
            if (newVal) {
                const incoming = JSON.parse(JSON.stringify(newVal)) as Partial<WordListItem>
                localItem.value = { ...defaultItem, ...incoming, categories: incoming.categories || [] }

                // Expand all panels when editing
                expandedPanels.value = localItem.value.categories.map((_, index) => index)

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

    const resetForm = (): void => {
        localItem.value = { ...defaultItem, categories: [] }
        expandedPanels.value = []
        showValidationError.value = false
        showError.value = false
        if (formRef.value) {
            formRef.value.resetValidation()
        }
    }

    const cancel = (): void => {
        dialog.value = false
    }

    const addCategory = (): void => {
        localItem.value.categories.push({
            name: '',
            description: '',
            link: '',
            entries: []
        })
        // Expand the newly added category
        expandedPanels.value.push(localItem.value.categories.length - 1)
    }

    const deleteCategory = (index: number): void => {
        localItem.value.categories.splice(index, 1)
        // Update expanded panels
        expandedPanels.value = expandedPanels.value.filter((p) => p !== index).map((p) => (p > index ? p - 1 : p))
    }

    const addWord = (categoryIndex: number): void => {
        const category = localItem.value.categories[categoryIndex]
        if (!category) {
            return
        }
        if (!category.entries) {
            category.entries = []
        }
        category.entries.push({
            value: '',
            description: ''
        })
    }

    const deleteWord = (categoryIndex: number, wordIndex: number): void => {
        const category = localItem.value.categories[categoryIndex]
        if (!category?.entries) {
            return
        }
        category.entries.splice(wordIndex, 1)
    }

    const handleSubmit = async (): Promise<void> => {
        showValidationError.value = false
        showError.value = false

        if (!formRef.value?.validate) {
            return
        }
        const { valid } = (await formRef.value.validate()) as FormValidationResult

        if (!valid) {
            showValidationError.value = true
            return
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
                // Backend create schema has no id field for the constructor; omit it (null fails validation).
                const createPayload: Record<string, unknown> = { ...localItem.value }
                delete createPayload['id']
                await createNewWordList(createPayload)
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

<style scoped>
    .w-100 {
        width: 100%;
    }
</style>
