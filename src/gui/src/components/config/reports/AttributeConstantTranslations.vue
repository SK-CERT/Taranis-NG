<template>
    <div
        class="mt-6"
        data-test="constant-translations"
    >
        <h3 class="text-subtitle-1 mb-2">{{ t('reports.attributes.constant_translations') }}</h3>
        <v-alert
            v-if="loaded && languages.length === 0"
            type="info"
            variant="tonal"
            density="compact"
        >
            {{ t('reports.attributes.no_languages') }}
        </v-alert>

        <template v-else-if="languages.length > 0">
            <div class="d-flex align-center flex-wrap ga-2 mb-2">
                <v-tabs
                    v-model="language"
                    density="compact"
                    data-test="constant-language-tabs"
                >
                    <v-tab
                        v-for="code in languages"
                        :key="code"
                        :value="code"
                    >
                        {{ languageName(code) }}
                    </v-tab>
                </v-tabs>
                <v-spacer />
                <v-select
                    v-model="providerId"
                    :items="providerOptions"
                    item-title="name"
                    item-value="id"
                    :label="t('reports.types.translation_ai_provider')"
                    density="compact"
                    variant="outlined"
                    hide-details
                    style="max-width: 240px"
                    :disabled="!canUpdate || translating"
                />
                <v-btn
                    color="primary"
                    variant="tonal"
                    prepend-icon="mdi-translate"
                    :loading="translating"
                    :disabled="!canUpdate || !providerId"
                    data-test="translate-constants"
                    @click="translateMissing"
                >
                    {{ t('reports.attributes.translate_missing') }}
                </v-btn>
            </div>

            <EditableEntityTable
                v-model:dialog="editDialog"
                v-model:page="page"
                v-model:items-per-page="pageSize"
                v-model:search="search"
                server
                searchable
                :items="rows"
                :items-length="total"
                :loading="loading"
                :title="t('reports.attributes.constants_in', { language: languageName(language) })"
                :headers="headers"
                :default-item="emptyRow"
                :add-title="''"
                :edit-title="t('reports.attributes.edit_translation')"
                :saving="saving"
                :disabled="!canUpdate"
                :allow-add="false"
                :allow-delete="false"
                dialog-max-width="500"
                @update:options="onOptions"
                @save="save"
            >
                <template #form="{ item }">
                    <p class="text-caption text-medium-emphasis mb-3">
                        {{ t('report_item.translation.source') }}: <bdi dir="auto">{{ item.value }}</bdi>
                    </p>
                    <v-text-field
                        v-model="item.translated_value"
                        :label="t('reports.attributes.value')"
                        variant="outlined"
                        density="comfortable"
                        class="mb-3"
                        dir="auto"
                    />
                    <v-text-field
                        v-model="item.translated_description"
                        :label="t('reports.attributes.description')"
                        variant="outlined"
                        density="comfortable"
                        dir="auto"
                    />
                </template>
            </EditableEntityTable>
        </template>
    </div>
</template>

<script setup lang="ts">
    import { computed, onMounted, ref, watch } from 'vue'
    import { useI18n } from 'vue-i18n'
    import EditableEntityTable from '@/components/common/EditableEntityTable.vue'
    import { useContentLanguages } from '@/composables/useContentLanguages'
    import { getAttributeEnums, getAttributeLanguages, translateAttributeEnums, updateAttributeEnum } from '@/api/config'

    /**
     * Language variants of an attribute's constants, one tab per language of the report types
     * that use the attribute. Reports keep storing the original constant; these are what
     * rendering shows in another language. Saved per constant, right away.
     */

    type Translations = Record<string, { value?: string; description?: string }>
    type Constant = { id: number; index: number; value: string; description: string; translations?: Translations }
    type Row = Constant & { translated_value: string; translated_description: string }

    const props = withDefaults(
        defineProps<{
            attributeId: number
            canUpdate?: boolean
        }>(),
        { canUpdate: false }
    )

    const { t } = useI18n()
    const { languageName } = useContentLanguages()

    const languages = ref<string[]>([])
    const sourceLanguage = ref<string | null>(null)
    const providers = ref<{ id: number; name: string }[]>([])
    const providerId = ref<number | null>(null)
    const language = ref<string>('')
    const loaded = ref(false)

    const rows = ref<Row[]>([])
    const total = ref(0)
    const page = ref(1)
    const pageSize = ref(25)
    const search = ref('')
    const loading = ref(false)
    const saving = ref(false)
    const translating = ref(false)
    const editDialog = ref(false)
    let searchTimeout: ReturnType<typeof setTimeout> | undefined

    const providerOptions = computed(() => providers.value)

    const headers = computed(() => [
        { title: t('reports.attributes.value'), key: 'value', sortable: false },
        {
            title: t('reports.attributes.translated_value', { language: languageName(language.value) }),
            key: 'translated_value',
            sortable: false
        },
        { title: t('reports.attributes.description'), key: 'translated_description', sortable: false },
        { title: t('settings.actions'), key: 'actions', align: 'end' as const, sortable: false }
    ])

    const emptyRow = (): Row => ({ id: -1, index: -1, value: '', description: '', translated_value: '', translated_description: '' })

    const toRow = (constant: Constant): Row => ({
        ...constant,
        translated_value: constant.translations?.[language.value]?.value ?? '',
        translated_description: constant.translations?.[language.value]?.description ?? ''
    })

    const load = async (): Promise<void> => {
        if (!language.value) return
        loading.value = true
        try {
            const response = (await getAttributeEnums({
                attribute_id: props.attributeId,
                search: search.value,
                offset: (page.value - 1) * pageSize.value,
                limit: pageSize.value
            })) as { data?: { items?: Constant[]; total_count?: number } }
            rows.value = (response.data?.items ?? []).map(toRow)
            total.value = response.data?.total_count ?? 0
        } catch (error) {
            console.error('Error loading constant translations:', error)
        } finally {
            loading.value = false
        }
    }

    const onOptions = (options: { page: number; itemsPerPage: number }): void => {
        const changed = options.page !== page.value || options.itemsPerPage !== pageSize.value
        page.value = options.page
        pageSize.value = options.itemsPerPage
        if (changed) load()
    }

    const notify = (detail: Record<string, unknown>): void => {
        window.dispatchEvent(new CustomEvent('notification', { detail }))
    }

    const notifyServerError = (error: unknown): void => {
        const message = (error as { response?: { data?: { error?: string } } })?.response?.data?.error
        notify(message ? { type: 'error', message } : { type: 'error', loc: 'common.error_saving' })
    }

    async function save(row: Row): Promise<void> {
        saving.value = true
        try {
            const translations: Translations = { ...(row.translations ?? {}) }
            if (row.translated_value.trim()) {
                translations[language.value] = { value: row.translated_value.trim(), description: row.translated_description.trim() }
            } else {
                delete translations[language.value]
            }
            await updateAttributeEnum(props.attributeId, row.id, [{ value: row.value, description: row.description, translations }])
            editDialog.value = false
            await load()
        } catch (error) {
            notifyServerError(error)
        } finally {
            saving.value = false
        }
    }

    // Translates in batches until nothing is left or a batch translates nothing (the rest failed).
    async function translateMissing(): Promise<void> {
        if (!providerId.value || !language.value) return
        translating.value = true
        let translated = 0
        let failed: number
        try {
            for (;;) {
                const response = (await translateAttributeEnums(props.attributeId, {
                    language: language.value,
                    ai_provider_id: providerId.value,
                    source_language: sourceLanguage.value
                })) as { data?: { translated?: number; failed?: number; remaining?: number } }
                translated += response.data?.translated ?? 0
                failed = response.data?.failed ?? 0
                if (!response.data?.remaining || !response.data?.translated) break
            }
            notify(
                failed > 0
                    ? { type: 'warning', loc: 'reports.attributes.translated_with_failures', params: { translated, failed } }
                    : { type: 'success', loc: 'reports.attributes.translated_constants', params: { count: translated } }
            )
            await load()
        } catch (error) {
            notifyServerError(error)
        } finally {
            translating.value = false
        }
    }

    watch(language, () => {
        page.value = 1
        load()
    })

    watch(search, () => {
        clearTimeout(searchTimeout)
        searchTimeout = setTimeout(() => {
            page.value = 1
            load()
        }, 300)
    })

    onMounted(async () => {
        try {
            const response = (await getAttributeLanguages(props.attributeId)) as {
                data?: { languages?: string[]; source_language?: string | null; ai_providers?: { id: number; name: string }[] }
            }
            languages.value = response.data?.languages ?? []
            sourceLanguage.value = response.data?.source_language ?? null
            providers.value = response.data?.ai_providers ?? []
            providerId.value = providers.value[0]?.id ?? null
            language.value = languages.value[0] ?? ''
        } catch (error) {
            console.error('Error loading constant languages:', error)
        } finally {
            loaded.value = true
        }
    })

    defineExpose({ languages, language, rows })
</script>
