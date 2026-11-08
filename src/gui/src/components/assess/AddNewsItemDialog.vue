<template>
    <v-dialog
        v-if="canCreateNewsItem"
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
                    validate-on="submit"
                    @submit.prevent="handleSubmit"
                >
                    <!-- The group the item goes into; nothing to choose when there is only one. -->
                    <v-select
                        v-if="groups.length > 1"
                        v-model="selectedGroupId"
                        :items="groupOptions"
                        :label="t('enter.group')"
                        variant="outlined"
                        density="comfortable"
                        class="mb-4"
                        :rules="[rules.required]"
                    />

                    <!-- Title Field -->
                    <v-text-field
                        v-model="newsItem.title"
                        dir="auto"
                        :spellcheck="spellcheck"
                        :label="t('enter.title')"
                        :rules="[rules.required]"
                        variant="outlined"
                        density="comfortable"
                        class="mb-4"
                    />

                    <!-- Review Field -->
                    <v-textarea
                        v-model="newsItem.review"
                        dir="auto"
                        :spellcheck="spellcheck"
                        :label="t('enter.review')"
                        variant="outlined"
                        density="comfortable"
                        rows="3"
                        class="mb-4"
                    />

                    <!-- Source Field -->
                    <v-text-field
                        v-model="newsItem.source"
                        dir="auto"
                        :spellcheck="spellcheck"
                        :label="t('enter.source')"
                        variant="outlined"
                        density="comfortable"
                        class="mb-4"
                    />

                    <!-- Link Field -->
                    <v-text-field
                        v-model="newsItem.link"
                        dir="ltr"
                        :spellcheck="false"
                        :label="t('enter.link')"
                        variant="outlined"
                        density="comfortable"
                        type="url"
                        :rules="[rules.link]"
                        class="mb-4"
                    />

                    <!-- Content Editor -->
                    <div class="mb-4">
                        <label class="text-subtitle-2 text-medium-emphasis mb-2 d-block">
                            {{ t('enter.content') }}
                        </label>
                        <RichTextEditor
                            v-model="editorContent"
                            height="200px"
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
    import RichTextEditor from '@/components/common/RichTextEditor.vue'
    import DialogToolbar from '@/components/common/dialogs/DialogToolbar.vue'
    import { addNewsItem } from '@/api/assess'
    import { useUserStore } from '@/stores/user'
    import { useAuth } from '@/composables/useAuth'
    import { useSpellcheck } from '@/composables/useSpellcheck'
    import Permissions from '@/services/permissions'
    import type { EntryGroup } from '@/stores/assess'
    import { isHttpUrl } from '@/utils/linkReferences'

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
            /** The groups the user may enter items into. */
            groups?: EntryGroup[]
            /** The group to propose: the one open in Assess; otherwise the default group. */
            initialGroupId?: string | null
        }>(),
        {
            modelValue: false,
            groups: () => [],
            initialGroupId: null
        }
    )

    const emit = defineEmits<{
        (e: 'update:modelValue', value: boolean): void
        (e: 'news-item-added'): void
    }>()

    const { t, locale } = useI18n()
    const userStore = useUserStore()
    const { checkPermission } = useAuth()
    const canCreateNewsItem = computed(() => checkPermission(Permissions.ASSESS_CREATE))
    const spellcheck = useSpellcheck()

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

    const selectedGroupId = ref<string>('')

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
        published: '',
        collected: '',
        attributes: []
    })

    const rules: {
        required: (value: string | number | null | undefined) => true | string
        link: (value: string | null | undefined) => true | string
    } = {
        required: (value: string | number | null | undefined) => !!value || t('error.required'),
        // Optional, but a web address when given: core refuses anything else.
        link: (value: string | null | undefined) => !value?.trim() || isHttpUrl(value) || t('enter.link_invalid')
    }

    // The default group is seeded as "Default" and shown as "Uncategorized", as in the Assess sidebar.
    const groupOptions = computed(() =>
        props.groups.map((group) => ({
            title: group.default ? t('collectors.groups.default_group') : group.name || group.id,
            value: group.id
        }))
    )

    // Propose the group open in Assess, else the default group, else the first.
    watch(
        [() => props.modelValue, () => props.groups, () => props.initialGroupId],
        ([isDialogOpen]) => {
            if (isDialogOpen && props.groups.length > 0) {
                const proposed =
                    props.groups.find((group) => props.initialGroupId !== null && group.id === props.initialGroupId) ??
                    props.groups.find((group) => group.default) ??
                    props.groups[0]
                selectedGroupId.value = proposed?.id ?? ''
            }
        },
        { immediate: true }
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

        // The parent hides this dialog for unauthorized users, but permission may
        // change while it is open or this component may be mounted elsewhere.
        if (!checkPermission(Permissions.ASSESS_CREATE)) {
            closeDialog()
            return
        }

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

            // v-text-field change '' -> null, normalize it otherwise the backend will fail
            newsItem.value.source ??= ''
            newsItem.value.link = (newsItem.value.link ?? '').trim()
            newsItem.value.review ??= ''

            // Set author
            newsItem.value.author = userStore.userName

            // Set language from locale
            newsItem.value.language = locale.value || 'en'

            // Set timestamps
            const d = new Date()
            const timestamp = `${appendLeadingZeroes(d.getDate())}.${appendLeadingZeroes(d.getMonth() + 1)}.${d.getFullYear()} - ${appendLeadingZeroes(d.getHours())}:${appendLeadingZeroes(d.getMinutes())}`
            newsItem.value.collected = timestamp
            newsItem.value.published = timestamp

            await addNewsItem({ ...newsItem.value, osint_source_group_id: selectedGroupId.value })
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
