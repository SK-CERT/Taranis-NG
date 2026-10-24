<template>
    <div data-test="label-translations">
        <div class="d-flex align-center flex-wrap ga-2 mb-4">
            <span class="text-body-2 text-medium-emphasis">{{ t('reports.types.labels_in', { language: languageName(language) }) }}</span>
            <v-spacer />
            <v-btn
                color="primary"
                variant="tonal"
                prepend-icon="mdi-translate"
                :loading="translating"
                :disabled="disabled || !aiProviderId"
                :title="aiProviderId ? undefined : t('reports.types.no_ai_provider')"
                data-test="translate-labels"
                @click="translateMissing"
            >
                {{ t('reports.types.translate_labels') }}
            </v-btn>
        </div>

        <v-text-field
            :model-value="label(reportType, 'title')"
            :label="t('reports.types.name')"
            :hint="reportType.title"
            persistent-hint
            :spellcheck="spellcheck"
            :disabled="disabled"
            variant="outlined"
            density="comfortable"
            class="mb-3"
            dir="auto"
            @update:model-value="(value: string) => setLabel(reportType, 'title', value)"
        >
            <template #append-inner>
                <v-btn
                    v-if="reportType.title"
                    v-bind="copyButton"
                    @click="copyOriginal(reportType, 'title')"
                />
            </template>
        </v-text-field>
        <v-textarea
            :model-value="label(reportType, 'description')"
            :label="t('reports.types.description')"
            :hint="reportType.description"
            persistent-hint
            :spellcheck="spellcheck"
            :disabled="disabled"
            variant="outlined"
            density="comfortable"
            rows="2"
            class="mb-3"
            dir="auto"
            @update:model-value="(value: string) => setLabel(reportType, 'description', value)"
        >
            <template #append-inner>
                <v-btn
                    v-if="reportType.description"
                    v-bind="copyButton"
                    @click="copyOriginal(reportType, 'description')"
                />
            </template>
        </v-textarea>

        <v-card
            v-for="(group, groupIndex) in reportType.attribute_groups"
            :key="`${group.id}-${groupIndex}`"
            variant="outlined"
            class="mb-4"
        >
            <v-card-text>
                <v-row dense>
                    <v-col
                        v-for="field in groupFields"
                        :key="field"
                        cols="12"
                        md="4"
                    >
                        <v-text-field
                            :model-value="label(group, field)"
                            :label="t(groupFieldLabels[field])"
                            :hint="String(group[field] ?? '')"
                            persistent-hint
                            :spellcheck="spellcheck"
                            :disabled="disabled || !group[field]"
                            variant="outlined"
                            density="compact"
                            dir="auto"
                            @update:model-value="(value: string) => setLabel(group, field, value)"
                        >
                            <template #append-inner>
                                <v-btn
                                    v-if="group[field]"
                                    v-bind="copyButton"
                                    @click="copyOriginal(group, field)"
                                />
                            </template>
                        </v-text-field>
                    </v-col>
                </v-row>
                <v-row
                    v-for="(item, itemIndex) in group.attribute_group_items"
                    :key="`${item.id}-${itemIndex}`"
                    dense
                    class="ms-4"
                >
                    <v-col
                        v-for="field in itemFields"
                        :key="field"
                        cols="12"
                        md="6"
                    >
                        <v-text-field
                            :model-value="label(item, field)"
                            :label="t(itemFieldLabels[field])"
                            :hint="String(item[field] ?? '')"
                            persistent-hint
                            :spellcheck="spellcheck"
                            :disabled="disabled || !item[field]"
                            variant="outlined"
                            density="compact"
                            dir="auto"
                            @update:model-value="(value: string) => setLabel(item, field, value)"
                        >
                            <template #append-inner>
                                <v-btn
                                    v-if="item[field]"
                                    v-bind="copyButton"
                                    @click="copyOriginal(item, field)"
                                />
                            </template>
                        </v-text-field>
                    </v-col>
                </v-row>
            </v-card-text>
        </v-card>
    </div>
</template>

<script setup lang="ts">
    import { computed, ref } from 'vue'
    import { useI18n } from 'vue-i18n'
    import { useSpellcheck } from '@/composables/useSpellcheck'
    import { useContentLanguages } from '@/composables/useContentLanguages'
    import { translateReportItemTypeLabels } from '@/api/config'

    /**
     * Label variants of a report type in one language: the type's name and description, and
     * each group's and field's labels. The texts live in each level's `translations`; nothing is
     * sent to the server until the report type is saved, the AI button included.
     */

    type Translations = Record<string, Record<string, string>>
    type Labelled = { translations?: Translations; [key: string]: unknown }
    type LabelledGroup = Labelled & { id: number; attribute_group_items: (Labelled & { id: number })[] }
    type LabelledType = Labelled & { id?: number | null; title: string; description: string; attribute_groups: LabelledGroup[] }

    const props = withDefaults(
        defineProps<{
            language: string
            sourceLanguage?: string | null
            aiProviderId?: number | null
            disabled?: boolean
        }>(),
        {
            sourceLanguage: null,
            aiProviderId: null,
            disabled: false
        }
    )

    const reportType = defineModel<LabelledType>({ required: true })

    const { t } = useI18n()
    const spellcheck = useSpellcheck()
    const { languageName } = useContentLanguages()
    const translating = ref(false)

    const groupFields = ['title', 'description', 'section_title'] as const
    const itemFields = ['title', 'description'] as const
    const groupFieldLabels: Record<(typeof groupFields)[number], string> = {
        title: 'reports.types.name',
        description: 'reports.types.description',
        section_title: 'reports.types.section_title'
    }
    const itemFieldLabels: Record<(typeof itemFields)[number], string> = {
        title: 'reports.types.name',
        description: 'reports.types.description'
    }

    const label = (target: Labelled, field: string): string => target.translations?.[props.language]?.[field] ?? ''

    const setLabel = (target: Labelled, field: string, value: string | null): void => {
        const translations = target.translations ?? (target.translations = {})
        const texts = translations[props.language] ?? (translations[props.language] = {})
        texts[field] = value ?? ''
    }

    // The original, shown under each field, as the start of its translation (names that read
    // the same in both languages, or a text to correct rather than retype).
    const copyOriginal = (target: Labelled, field: string): void => setLabel(target, field, String(target[field] ?? ''))

    const copyButton = computed(() => ({
        'icon': 'mdi-content-copy',
        'variant': 'text' as const,
        'size': 'small',
        'density': 'comfortable' as const,
        'title': t('reports.types.copy_original'),
        'aria-label': t('reports.types.copy_original'),
        'disabled': props.disabled,
        'data-test': 'copy-original'
    }))

    // Every label with a source text and no translation yet, keyed by where it goes.
    const missingLabels = (): Map<string, { target: Labelled; field: string; text: string }> => {
        const missing = new Map<string, { target: Labelled; field: string; text: string }>()
        const collect = (key: string, target: Labelled, fields: readonly string[]): void => {
            for (const field of fields) {
                const text = String(target[field] ?? '').trim()
                if (text && !label(target, field).trim()) missing.set(`${key}.${field}`, { target, field, text })
            }
        }
        collect('type', reportType.value, itemFields)
        reportType.value.attribute_groups.forEach((group, groupIndex) => {
            collect(`g${groupIndex}`, group, groupFields)
            group.attribute_group_items.forEach((item, itemIndex) => collect(`g${groupIndex}.i${itemIndex}`, item, itemFields))
        })
        return missing
    }

    const notify = (type: 'success' | 'error' | 'warning', loc: string, params?: Record<string, unknown>): void => {
        window.dispatchEvent(new CustomEvent('notification', { detail: { type, loc, params } }))
    }

    async function translateMissing(): Promise<void> {
        const missing = missingLabels()
        if (missing.size === 0 || !props.aiProviderId) return
        translating.value = true
        try {
            const response = (await translateReportItemTypeLabels({
                texts: Object.fromEntries([...missing].map(([key, entry]) => [key, entry.text])),
                source_language: props.sourceLanguage,
                target_language: props.language,
                ai_provider_id: props.aiProviderId,
                report_item_type_id: reportType.value.id ?? null
            })) as { data?: { translations?: Record<string, string>; failed?: Record<string, string> } }
            for (const [key, text] of Object.entries(response.data?.translations ?? {})) {
                const entry = missing.get(key)
                if (entry) setLabel(entry.target, entry.field, text)
            }
            const failed = Object.keys(response.data?.failed ?? {}).length
            if (failed > 0) notify('warning', 'reports.types.translate_labels_failed', { count: failed })
            else notify('success', 'reports.types.labels_translated')
        } catch (error) {
            // Core says why (no provider, an unsupported one ...); otherwise a generic failure.
            const message = (error as { response?: { data?: { error?: string } } })?.response?.data?.error
            if (message) window.dispatchEvent(new CustomEvent('notification', { detail: { type: 'error', message } }))
            else notify('error', 'common.error_saving')
        } finally {
            translating.value = false
        }
    }
</script>
