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
                :title="isEdit ? t('public_web.webs.edit') : t('public_web.webs.add_new')"
                :saving="saving"
                @cancel="requestClose"
                @save="saveAndClose"
            />

            <v-card-text>
                <v-form
                    ref="formRef"
                    @submit.prevent="saveAndClose"
                >
                    <v-tabs
                        v-model="activeSection"
                        color="primary"
                        density="comfortable"
                        class="mb-3"
                    >
                        <v-tab value="feed">{{ t('public_web.webs.feed_settings') }}</v-tab>
                        <v-tab value="branding">{{ t('public_web.webs.branding') }}</v-tab>
                        <v-tab value="images">{{ t('public_web.webs.images') }}</v-tab>
                        <v-tab value="email">{{ t('public_web.webs.email_settings') }}</v-tab>
                    </v-tabs>

                    <v-window
                        v-model="activeSection"
                        class="pt-2"
                    >
                        <v-window-item value="feed">
                            <!-- Basics -->
                            <v-row>
                                <v-col
                                    cols="12"
                                    sm="6"
                                >
                                    <v-text-field
                                        v-model="localItem.name"
                                        :label="t('public_web.webs.name')"
                                        variant="outlined"
                                        density="comfortable"
                                        :rules="[(v) => !!v || t('error.required')]"
                                        :disabled="saving"
                                    />
                                </v-col>
                                <v-col
                                    cols="12"
                                    sm="6"
                                >
                                    <v-text-field
                                        v-model="localItem.hostname"
                                        :label="t('public_web.webs.hostname')"
                                        :hint="t('public_web.webs.hostname_hint')"
                                        persistent-hint
                                        variant="outlined"
                                        density="comfortable"
                                        :disabled="saving"
                                    />
                                </v-col>
                            </v-row>

                            <v-row>
                                <v-col
                                    cols="6"
                                    sm="3"
                                >
                                    <v-text-field
                                        v-model.number="localItem.config.max_reports_homepage"
                                        type="number"
                                        :label="t('public_web.webs.max_reports_homepage')"
                                        variant="outlined"
                                        density="comfortable"
                                        :disabled="saving"
                                    />
                                </v-col>
                                <v-col
                                    cols="6"
                                    sm="3"
                                >
                                    <v-text-field
                                        v-model.number="localItem.config.max_reports_rss"
                                        type="number"
                                        :label="t('public_web.webs.max_reports_rss')"
                                        variant="outlined"
                                        density="comfortable"
                                        :disabled="saving"
                                    />
                                </v-col>
                                <v-col
                                    cols="6"
                                    sm="3"
                                >
                                    <v-text-field
                                        v-model.number="localItem.config.logo_width"
                                        type="number"
                                        :label="t('public_web.webs.logo_width')"
                                        variant="outlined"
                                        density="comfortable"
                                        :disabled="saving"
                                    />
                                </v-col>
                                <v-col
                                    cols="6"
                                    sm="3"
                                >
                                    <v-text-field
                                        v-model.number="localItem.config.logo_height"
                                        type="number"
                                        :label="t('public_web.webs.logo_height')"
                                        variant="outlined"
                                        density="comfortable"
                                        :disabled="saving"
                                    />
                                </v-col>
                                <v-col
                                    cols="12"
                                    sm="6"
                                >
                                    <v-combobox
                                        v-model="localItem.config.organization"
                                        :items="organizationNames"
                                        :label="t('public_web.webs.organization')"
                                        :hint="t('public_web.webs.organization_hint')"
                                        persistent-hint
                                        :loading="loadingOrganizations"
                                        variant="outlined"
                                        density="comfortable"
                                        :disabled="saving"
                                    />
                                </v-col>
                            </v-row>

                            <v-row>
                                <v-col
                                    cols="12"
                                    sm="8"
                                >
                                    <v-combobox
                                        v-model="localItem.config.languages"
                                        :items="languageSuggestions"
                                        :label="t('public_web.webs.languages')"
                                        :hint="t('public_web.webs.languages_hint')"
                                        persistent-hint
                                        multiple
                                        chips
                                        closable-chips
                                        variant="outlined"
                                        density="comfortable"
                                        :disabled="saving"
                                    />
                                </v-col>
                                <v-col
                                    cols="12"
                                    sm="4"
                                >
                                    <v-select
                                        v-model="localItem.config.default_language"
                                        :items="languagesForForm"
                                        :label="t('public_web.webs.default_language')"
                                        variant="outlined"
                                        density="comfortable"
                                        :disabled="saving"
                                    />
                                </v-col>
                            </v-row>
                        </v-window-item>

                        <v-window-item value="branding">
                            <v-tabs
                                v-model="activeLang"
                                color="primary"
                                density="compact"
                                class="mt-n3"
                            >
                                <v-tab
                                    v-for="lang in languagesForForm"
                                    :key="lang"
                                    :value="lang"
                                >
                                    {{ lang }}
                                </v-tab>
                            </v-tabs>
                            <v-window
                                v-model="activeLang"
                                class="mt-2 pt-2"
                            >
                                <v-window-item
                                    v-for="lang in languagesForForm"
                                    :key="lang"
                                    :value="lang"
                                >
                                    <template
                                        v-for="field in textFields"
                                        :key="field.key"
                                    >
                                        <v-textarea
                                            v-if="field.multiline"
                                            v-model="langText(field.key)[lang]"
                                            :label="t(field.label)"
                                            variant="outlined"
                                            density="comfortable"
                                            rows="3"
                                            class="mb-2"
                                            :disabled="saving"
                                        />
                                        <v-text-field
                                            v-else
                                            v-model="langText(field.key)[lang]"
                                            :label="t(field.label)"
                                            variant="outlined"
                                            density="comfortable"
                                            class="mb-2"
                                            :disabled="saving"
                                        />
                                    </template>
                                </v-window-item>
                            </v-window>
                        </v-window-item>

                        <v-window-item value="images">
                            <v-row>
                                <v-col
                                    v-for="kind in imageKinds"
                                    :key="kind"
                                    cols="12"
                                    sm="4"
                                >
                                    <div class="text-caption mb-1">{{ t('public_web.webs.image_' + kind) }}</div>
                                    <v-img
                                        v-if="imageState[kind].url"
                                        :src="imageState[kind].url"
                                        max-height="80"
                                        class="mb-2 border"
                                        contain
                                    />
                                    <v-file-input
                                        :label="t('public_web.webs.upload')"
                                        accept="image/*"
                                        prepend-icon="mdi-image"
                                        variant="outlined"
                                        density="compact"
                                        hide-details
                                        :disabled="saving"
                                        @update:model-value="(f) => onFileSelected(kind, f)"
                                    />
                                    <v-btn
                                        v-if="imageState[kind].url"
                                        size="x-small"
                                        variant="text"
                                        color="error"
                                        class="mt-1"
                                        :disabled="saving"
                                        @click="clearImage(kind)"
                                    >
                                        {{ t('public_web.webs.remove_image') }}
                                    </v-btn>
                                </v-col>
                            </v-row>

                            <v-alert
                                v-if="!isEdit"
                                type="info"
                                variant="tonal"
                                density="compact"
                                class="mt-3"
                            >
                                {{ t('public_web.webs.images_after_save') }}
                            </v-alert>
                        </v-window-item>

                        <v-window-item value="email">
                            <v-row>
                                <v-col cols="12">
                                    <v-text-field
                                        v-model="localItem.config.feedback_recipients"
                                        :label="t('public_web.webs.feedback_recipients')"
                                        :hint="t('public_web.webs.feedback_recipients_hint')"
                                        persistent-hint
                                        variant="outlined"
                                        density="comfortable"
                                        :disabled="saving"
                                    />
                                </v-col>
                                <v-col
                                    cols="12"
                                    sm="6"
                                >
                                    <v-text-field
                                        v-model="localItem.config.smtp_username"
                                        :label="t('public_web.webs.smtp_username')"
                                        variant="outlined"
                                        density="comfortable"
                                        :disabled="saving"
                                    />
                                </v-col>
                                <v-col
                                    cols="12"
                                    sm="6"
                                >
                                    <v-text-field
                                        v-model="localItem.config.smtp_password"
                                        :label="t('public_web.webs.smtp_password')"
                                        type="password"
                                        autocomplete="new-password"
                                        variant="outlined"
                                        density="comfortable"
                                        :disabled="saving"
                                    />
                                </v-col>
                                <v-col
                                    cols="12"
                                    sm="8"
                                >
                                    <v-text-field
                                        v-model="localItem.config.smtp_url"
                                        :label="t('public_web.webs.smtp_url')"
                                        variant="outlined"
                                        density="comfortable"
                                        :disabled="saving"
                                    />
                                </v-col>
                                <v-col
                                    cols="12"
                                    sm="4"
                                >
                                    <v-text-field
                                        v-model.number="localItem.config.smtp_port"
                                        :label="t('public_web.webs.smtp_port')"
                                        type="number"
                                        variant="outlined"
                                        density="comfortable"
                                        :disabled="saving"
                                    />
                                </v-col>
                                <v-col
                                    cols="12"
                                    sm="6"
                                >
                                    <v-text-field
                                        v-model="localItem.config.email_sender"
                                        :label="t('public_web.webs.email_sender')"
                                        variant="outlined"
                                        density="comfortable"
                                        :disabled="saving"
                                    />
                                </v-col>
                                <v-col
                                    cols="12"
                                    sm="6"
                                >
                                    <v-text-field
                                        v-model="localItem.config.email_subject"
                                        :label="t('public_web.webs.email_subject')"
                                        variant="outlined"
                                        density="comfortable"
                                        :disabled="saving"
                                    />
                                </v-col>
                                <v-col cols="12">
                                    <v-btn
                                        color="primary"
                                        variant="tonal"
                                        :loading="testingEmail"
                                        :disabled="saving || testingEmail"
                                        @click="sendTestEmail"
                                    >
                                        {{ t('public_web.webs.send_test_email') }}
                                    </v-btn>
                                </v-col>
                            </v-row>
                        </v-window-item>
                    </v-window>
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
    import { useAuth } from '@/composables/useAuth'
    import { useUnsavedChanges } from '@/composables/useUnsavedChanges'
    import {
        createNewPublicWeb,
        updatePublicWeb,
        getPublicWebImage,
        uploadPublicWebImage,
        deletePublicWebImage,
        getAllOrganizations,
        testPublicWebEmail
    } from '@/api/config'

    type WebConfig = {
        languages: string[]
        default_language: string
        max_reports_homepage: number | null
        max_reports_rss: number | null
        logo_width: number | null
        logo_height: number | null
        organization: string
        feedback_recipients: string
        smtp_username: string
        smtp_password: string
        smtp_url: string
        smtp_port: number | null
        email_sender: string
        email_subject: string
        // Legacy neutral URLs; migrated into `text` (per-language) by normalize().
        organization_url?: string
        service_description_url?: string
        text: Record<string, Record<string, string>>
    }

    type WebItem = {
        id: string | number | null
        name: string
        hostname: string
        config: WebConfig
        images?: Array<{ kind: string }>
        [key: string]: unknown
    }

    type FormValidationResult = { valid: boolean }

    const props = withDefaults(
        defineProps<{
            nodeId: number | string
            editItem?: Partial<WebItem> | null
        }>(),
        { editItem: null }
    )

    const emit = defineEmits<{ (e: 'saved'): void }>()

    const { t } = useI18n()
    const { checkPermission } = useAuth()

    const imageKinds = ['logo', 'favicon', 'preview'] as const
    type ImageKind = (typeof imageKinds)[number]

    const languageSuggestions = ['en', 'cs', 'sk', 'de', 'fr', 'es', 'pl']

    // Translatable branding fields (stored under config.text[key][lang]).
    const textFields = [
        { key: 'site_name', label: 'public_web.text.site_name', multiline: false },
        { key: 'rss_title', label: 'public_web.text.rss_title', multiline: false },
        { key: 'rss_description', label: 'public_web.text.rss_description', multiline: false },
        { key: 'meta_description', label: 'public_web.text.meta_description', multiline: false },
        { key: 'meta_keywords', label: 'public_web.text.meta_keywords', multiline: false },
        { key: 'homepage_title', label: 'public_web.text.homepage_title', multiline: false },
        { key: 'service_description_title', label: 'public_web.text.service_description_title', multiline: false },
        { key: 'service_description_url', label: 'public_web.webs.service_description_url', multiline: false },
        { key: 'organization_url', label: 'public_web.webs.organization_url', multiline: false },
        { key: 'service_warning', label: 'public_web.text.service_warning', multiline: true },
        { key: 'feedback_question1', label: 'public_web.text.feedback_question1', multiline: false },
        { key: 'feedback_question2', label: 'public_web.text.feedback_question2', multiline: false },
        { key: 'feedback_question3', label: 'public_web.text.feedback_question3', multiline: false },
        { key: 'feedback_comment', label: 'public_web.text.feedback_comment', multiline: false }
    ]

    const formRef = ref<any>(null)
    const saving = ref(false)
    const testingEmail = ref(false)
    const dialog = ref(false)
    const activeSection = ref('feed')
    const activeLang = ref('en')

    // Existing Taranis organizations, offered as the org link label (a v-combobox
    // so an admin can pick one or type a custom name). Loaded once on first open.
    const organizationNames = ref<string[]>([])
    const loadingOrganizations = ref(false)

    async function loadOrganizations(): Promise<void> {
        if (organizationNames.value.length) {
            return
        }
        loadingOrganizations.value = true
        try {
            const response = (await getAllOrganizations({ search: '' })) as { data?: { items?: Array<{ name: string }> } }
            organizationNames.value = (response.data?.items || []).map((org) => org.name).filter(Boolean)
        } catch (error) {
            console.error('Error loading organizations:', error)
        } finally {
            loadingOrganizations.value = false
        }
    }

    function emptyConfig(): WebConfig {
        return {
            languages: ['en'],
            default_language: 'en',
            max_reports_homepage: 10,
            max_reports_rss: 15,
            logo_width: 90,
            logo_height: 45,
            organization: '',
            feedback_recipients: '',
            smtp_username: '',
            smtp_password: '',
            smtp_url: '',
            smtp_port: null,
            email_sender: '',
            email_subject: '',
            text: {}
        }
    }

    function emptyItem(): WebItem {
        return { id: null, name: '', hostname: '', config: emptyConfig() }
    }

    // Ensure config + every text field is a well-formed object so v-model binds cleanly.
    function normalize(item: WebItem): WebItem {
        item.config = { ...emptyConfig(), ...(item.config || {}) }
        if (!Array.isArray(item.config.languages) || item.config.languages.length === 0) {
            item.config.languages = [item.config.default_language || 'en']
        }
        const text = item.config.text || {}
        for (const field of textFields) {
            text[field.key] = { ...(text[field.key] || {}) }
        }
        // Migrate legacy neutral URLs (stored top-level) into the per-language map,
        // seeding the default language so an existing value stays visible/editable.
        const defaultLang = item.config.default_language || item.config.languages[0] || 'en'
        for (const key of ['organization_url', 'service_description_url'] as const) {
            const legacy = item.config[key]
            const map = text[key] ?? (text[key] = {})
            if (legacy && !map[defaultLang]) {
                map[defaultLang] = legacy
            }
            delete item.config[key]
        }
        item.config.text = text
        return item
    }

    const localItem = ref<WebItem>(normalize(emptyItem()))
    const isEdit = computed(() => !!localItem.value.id)

    // The per-language map for a branding field. normalize() guarantees it
    // exists, so the `?? {}` fallback is only there to satisfy the type checker.
    function langText(key: string): Record<string, string> {
        return localItem.value.config.text[key] ?? {}
    }
    const canCreate = computed(() => checkPermission('CONFIG_PUBLIC_WEB_NODE_CREATE'))

    // Languages currently offered as branding tabs / default-language choices.
    const languagesForForm = computed<string[]>(() => {
        const langs = localItem.value.config.languages
        return Array.isArray(langs) && langs.length > 0 ? langs : ['en']
    })

    // Keep the active tab valid when the language list changes.
    watch(languagesForForm, (langs) => {
        if (!langs.includes(activeLang.value)) {
            activeLang.value = langs[0] || 'en'
        }
    })

    // Image working state: url = current preview, file = a pending upload, cleared = delete on save.
    const imageState = ref<Record<ImageKind, { url: string | null; file: File | null; cleared: boolean }>>({
        logo: { url: null, file: null, cleared: false },
        favicon: { url: null, file: null, cleared: false },
        preview: { url: null, file: null, cleared: false }
    })

    function resetImageState(): void {
        for (const kind of imageKinds) {
            const state = imageState.value[kind]
            if (state.url && state.file) {
                URL.revokeObjectURL(state.url)
            }
            imageState.value[kind] = { url: null, file: null, cleared: false }
        }
    }

    async function loadExistingImages(): Promise<void> {
        if (!isEdit.value) {
            return
        }
        const present = (localItem.value.images || []).map((i) => i.kind)
        for (const kind of imageKinds) {
            if (!present.includes(kind)) {
                continue
            }
            try {
                const response = (await getPublicWebImage(props.nodeId, localItem.value.id, kind)) as { data: Blob }
                imageState.value[kind].url = URL.createObjectURL(response.data)
            } catch (error) {
                console.error('Error loading image', kind, error)
            }
        }
    }

    function onFileSelected(kind: ImageKind, file: File | File[] | null): void {
        const selected = Array.isArray(file) ? file[0] : file
        const state = imageState.value[kind]
        if (state.url && state.file) {
            URL.revokeObjectURL(state.url)
        }
        if (selected) {
            state.file = selected
            state.url = URL.createObjectURL(selected)
            state.cleared = false
        }
    }

    function clearImage(kind: ImageKind): void {
        const state = imageState.value[kind]
        if (state.url && state.file) {
            URL.revokeObjectURL(state.url)
        }
        state.url = null
        state.file = null
        state.cleared = true
    }

    async function syncImages(webId: number | string): Promise<void> {
        for (const kind of imageKinds) {
            const state = imageState.value[kind]
            if (state.file) {
                const formData = new FormData()
                formData.append('file', state.file)
                await uploadPublicWebImage(props.nodeId, webId, kind, formData)
            } else if (state.cleared) {
                await deletePublicWebImage(props.nodeId, webId, kind)
            }
        }
    }

    async function sendTestEmail(): Promise<void> {
        testingEmail.value = true
        try {
            await testPublicWebEmail(props.nodeId, {
                name: localItem.value.name,
                hostname: localItem.value.hostname,
                feedback_recipients: localItem.value.config.feedback_recipients,
                smtp_username: localItem.value.config.smtp_username,
                smtp_password: localItem.value.config.smtp_password,
                smtp_url: localItem.value.config.smtp_url,
                smtp_port: localItem.value.config.smtp_port,
                email_sender: localItem.value.config.email_sender,
                email_subject: localItem.value.config.email_subject
            })
            window.dispatchEvent(
                new CustomEvent('notification', {
                    detail: { type: 'success', loc: 'public_web.webs.send_test_email_success' }
                })
            )
        } catch {
            window.dispatchEvent(
                new CustomEvent('notification', {
                    detail: { type: 'error', loc: 'public_web.webs.send_test_email_error' }
                })
            )
        } finally {
            testingEmail.value = false
        }
    }

    async function persist(): Promise<boolean> {
        const { valid } = (await formRef.value.validate()) as FormValidationResult
        if (!valid) {
            return false
        }
        saving.value = true
        try {
            let webId = localItem.value.id
            if (isEdit.value) {
                await updatePublicWeb(props.nodeId, localItem.value)
            } else {
                const response = (await createNewPublicWeb(props.nodeId, { ...localItem.value, id: -1 })) as {
                    data?: { id?: number }
                }
                webId = response.data?.id ?? null
            }
            if (webId != null) {
                await syncImages(webId)
            }
            emit('saved')
            return true
        } catch (error) {
            window.dispatchEvent(new CustomEvent('notification', { detail: { type: 'error', loc: 'common.error_saving' } }))
            return false
        } finally {
            saving.value = false
        }
    }

    function closeDialog(): void {
        formRef.value?.reset()
        resetImageState()
        localItem.value = normalize(emptyItem())
        dialog.value = false
    }

    const { confirmVisible, capture, requestClose, continueEditing, saveAndClose, discardAndClose } = useUnsavedChanges({
        getState: () => ({ item: localItem.value, images: imageState.value }),
        save: persist,
        close: closeDialog
    })

    watch(
        () => props.editItem,
        (newItem) => {
            if (newItem && Object.keys(newItem).length > 0) {
                // Deep-clone first: normalize() mutates config.text in place, and
                // newItem still shares that nested object with the store's web. A
                // deep watch here would see those mutations and re-fire endlessly
                // (100% CPU freeze), so clone to break the shared refs and watch by
                // identity only (the parent assigns a fresh object per edit click).
                const clone = JSON.parse(JSON.stringify(newItem)) as WebItem
                localItem.value = normalize({ ...emptyItem(), ...clone })
                dialog.value = true
            } else {
                localItem.value = normalize(emptyItem())
            }
        },
        { immediate: true }
    )

    watch(
        () => dialog.value,
        async (newVal: boolean) => {
            if (!newVal) {
                saving.value = false
                resetImageState()
            } else {
                activeSection.value = 'feed'
                activeLang.value = languagesForForm.value[0] || 'en'
                resetImageState()
                await loadOrganizations()
                await loadExistingImages()
                capture()
            }
        }
    )
</script>
