<template>
    <v-dialog
        v-model="isOpen"
        max-width="800px"
        scrollable
    >
        <!-- Optional activator: when a parent supplies one (e.g. the Assess "Add New"
             button), the open transition originates from it, matching the config dialogs. -->
        <template
            v-if="$slots['activator']"
            #activator="activatorProps"
        >
            <slot
                name="activator"
                v-bind="activatorProps"
            />
        </template>

        <v-card>
            <DialogToolbar
                :title="t('nav_menu.enter')"
                :saving="isSubmitting"
                @cancel="closeDialog"
                @save="handleSubmit"
            />

            <v-card-text>
                <v-form
                    ref="formRef"
                    @submit.prevent="handleSubmit"
                >
                    <!-- Manual OSINT Source Select -->
                    <v-select
                        v-if="manualSources && manualSources.length > 1"
                        v-model="selectedSourceId"
                        :items="sourceOptions"
                        :label="t('enter.manual_source')"
                        variant="outlined"
                        density="comfortable"
                        class="mb-4"
                        :rules="[rules.required]"
                    />

                    <!-- Title Field -->
                    <v-text-field
                        v-model="newsItem.title"
                        :label="t('enter.title')"
                        :rules="[rules.required]"
                        variant="outlined"
                        density="comfortable"
                        class="mb-4"
                    />

                    <!-- Review Field -->
                    <v-textarea
                        v-model="newsItem.review"
                        :label="t('enter.review')"
                        variant="outlined"
                        density="comfortable"
                        rows="3"
                        class="mb-4"
                    />

                    <!-- Source Field -->
                    <v-text-field
                        v-model="newsItem.source"
                        :label="t('enter.source')"
                        variant="outlined"
                        density="comfortable"
                        class="mb-4"
                    />

                    <!-- Link Field -->
                    <v-text-field
                        v-model="newsItem.link"
                        :label="t('enter.link')"
                        variant="outlined"
                        density="comfortable"
                        type="url"
                        class="mb-4"
                    />

                    <!-- Content Editor -->
                    <div class="mb-4">
                        <label class="text-subtitle-2 text-medium-emphasis mb-2 d-block">
                            {{ t('enter.content') }}
                        </label>
                        <Editor
                            v-model="editorContent"
                            editor-style="min-height: 250px"
                        />
                    </div>

                    <!-- Validation Error Alert -->
                    <v-alert
                        v-if="showValidationError"
                        type="error"
                        variant="tonal"
                        class="mb-4"
                        closable
                        @click:close="showValidationError = false"
                    >
                        {{ t('error.validation') }}
                    </v-alert>

                    <!-- Error Alert -->
                    <v-alert
                        v-if="showError"
                        type="error"
                        variant="tonal"
                        class="mb-4"
                        closable
                        @click:close="showError = false"
                    >
                        {{ t('enter.error') }}
                    </v-alert>

                    <!-- Success Alert -->
                    <v-alert
                        v-if="showSuccess"
                        type="success"
                        variant="tonal"
                        class="mb-4"
                        closable
                        @click:close="showSuccess = false"
                    >
                        {{ t('enter.successful') }}
                    </v-alert>
                </v-form>
            </v-card-text>
        </v-card>
    </v-dialog>
</template>

<script setup lang="ts">
    import { ref, computed, watch } from 'vue'
    import { useI18n } from 'vue-i18n'
    import Editor from 'primevue/editor'
    import DialogToolbar from '@/components/common/dialogs/DialogToolbar.vue'
    import { addNewsItem } from '@/api/assess'
    import { useUserStore } from '@/stores/user'

    type ManualSource = {
        id: string | number
        name?: string
        [key: string]: unknown
    }

    type NewsItemForm = {
        id: string
        title: string
        review: string
        content: string
        link: string
        source: string
        author: string
        language: string
        hash: string
        osint_source_id: string | number
        published: string
        collected: string
        attributes: unknown[]
    }

    type FormRef = {
        reset?: () => void
        validate?: () => Promise<{ valid: boolean }>
    }

    const props = withDefaults(
        defineProps<{
            modelValue?: boolean
            manualSources?: unknown[]
        }>(),
        {
            modelValue: false,
            manualSources: () => []
        }
    )

    const emit = defineEmits<{
        (e: 'update:modelValue', value: boolean): void
        (e: 'news-item-added'): void
    }>()

    const { t, locale } = useI18n()
    const userStore = useUserStore()

    const isOpen = computed<boolean>({
        get: () => props.modelValue,
        set: (value: boolean) => emit('update:modelValue', value)
    })

    const formRef = ref<FormRef | null>(null)
    const editorContent = ref<string>('')
    const isSubmitting = ref<boolean>(false)

    const showError = ref<boolean>(false)
    const showValidationError = ref<boolean>(false)
    const showSuccess = ref<boolean>(false)

    const selectedSourceId = ref<string | number>('')

    const newsItem = ref<NewsItemForm>({
        id: '',
        title: '',
        review: '',
        content: '',
        link: '',
        source: '',
        author: '',
        language: '',
        hash: '',
        osint_source_id: '',
        published: '',
        collected: '',
        attributes: []
    })

    const rules: {
        required: (value: string | number | null | undefined) => true | string
    } = {
        required: (value: string | number | null | undefined) => !!value || t('error.required')
    }

    const sourceOptions = computed(() => {
        return (props.manualSources as ManualSource[]).map((source: ManualSource) => ({
            title: source.name || source.id,
            value: source.id
        }))
    })

    // Initialize selected source
    watch(
        () => props.modelValue,
        (newVal: boolean) => {
            if (newVal && props.manualSources.length > 0) {
                // Set to first source if only one, otherwise let user select
                if (props.manualSources.length === 1) {
                    selectedSourceId.value = (props.manualSources[0] as ManualSource).id
                } else if (!selectedSourceId.value) {
                    selectedSourceId.value = (props.manualSources[0] as ManualSource).id
                }
            }
        }
    )

    const appendLeadingZeroes = (n: number): string | number => {
        if (n <= 9) {
            return '0' + n
        }
        return n
    }

    const resetForm = (): void => {
        newsItem.value = {
            id: '',
            title: '',
            review: '',
            content: '',
            link: '',
            source: '',
            author: '',
            language: '',
            hash: '',
            osint_source_id: '',
            published: '',
            collected: '',
            attributes: []
        }
        editorContent.value = ''
        showError.value = false
        showValidationError.value = false
        showSuccess.value = false
        if (formRef.value?.reset) {
            formRef.value.reset()
        }
    }

    const closeDialog = (): void => {
        resetForm()
        isOpen.value = false
    }

    const handleSubmit = async (): Promise<void> => {
        showError.value = false
        showValidationError.value = false
        showSuccess.value = false

        if (!formRef.value?.validate) {
            return
        }
        const { valid } = (await formRef.value?.validate?.()) || { valid: false }

        if (!valid) {
            showValidationError.value = true
            return
        }

        isSubmitting.value = true

        try {
            // Set content from editor
            newsItem.value.content = editorContent.value

            // Set osint_source_id from selected source
            newsItem.value.osint_source_id = selectedSourceId.value

            // Set author
            newsItem.value.author = userStore.userName

            // Set language from locale
            newsItem.value.language = locale.value || 'en'

            // Set timestamps
            const d = new Date()
            const timestamp = `${appendLeadingZeroes(d.getDate())}.${appendLeadingZeroes(d.getMonth() + 1)}.${d.getFullYear()} - ${appendLeadingZeroes(d.getHours())}:${appendLeadingZeroes(d.getMinutes())}`
            newsItem.value.collected = timestamp
            newsItem.value.published = timestamp

            await addNewsItem(newsItem.value)
            showSuccess.value = true

            emit('news-item-added')

            // Close after a short delay to show success message
            setTimeout(() => {
                closeDialog()
            }, 1000)
        } catch (error: unknown) {
            console.error('Error adding news item:', error)
            showError.value = true
        } finally {
            isSubmitting.value = false
        }
    }
</script>

<style scoped>
    :deep(.ql-editor) {
        min-height: 250px;
    }
</style>
