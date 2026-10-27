<template>
    <div
        class="pa-4"
        data-test="report-item-translation"
    >
        <div class="d-flex align-center flex-wrap ga-2 mb-4">
            <span class="text-body-2 text-medium-emphasis">
                {{ t('report_item.translation.intro', { language: languageName(language) }) }}
            </span>
            <v-spacer />
            <v-btn
                v-if="canModify && unreviewedKeys.length > 0"
                color="success"
                variant="tonal"
                prepend-icon="mdi-check-all"
                :loading="reviewing"
                :disabled="busy || reviewing"
                data-test="review-language"
                @click="review()"
            >
                {{ t('report_item.translation.review_all') }}
            </v-btn>
            <v-btn
                v-if="canTranslate"
                color="primary"
                variant="tonal"
                prepend-icon="mdi-translate"
                :loading="busy"
                :disabled="busy"
                data-test="translate-language"
                @click="emit('translate-language', language)"
            >
                {{ t('report_item.translation.translate_language', { language: languageName(language) }) }}
            </v-btn>
        </div>

        <!-- Name prefix and name -->
        <v-row>
            <v-col
                v-for="field in titleFields"
                :key="field"
                cols="12"
                md="6"
            >
                <v-text-field
                    v-model="titles[field]"
                    dir="auto"
                    :label="t(field === 'title' ? 'report_item.title' : 'report_item.title_prefix')"
                    :hint="sourceTitle(field)"
                    persistent-hint
                    :disabled="titleLocks[field] || !canModify"
                    :class="titleLocks[field] ? 'locked-style' : ''"
                    :spellcheck="spellcheck"
                    :data-test="`translation-${field}`"
                    @focus="onTitleFocus(field)"
                    @blur="onTitleBlur(field)"
                    @keyup="onTitleKeyUp(field)"
                >
                    <template #append-inner>
                        <TranslationState
                            :state="titleTranslations[field]"
                            :reviewable="canModify && !titleLocks[field] && !reviewing"
                            @review="review([field])"
                        />
                        <v-btn
                            v-if="canTranslate && sourceTitle(field)"
                            icon="mdi-translate"
                            variant="text"
                            density="compact"
                            size="small"
                            tabindex="-1"
                            :disabled="busy || titleLocks[field]"
                            :loading="translatingKey === field"
                            :title="t('report_item.translation.translate_field')"
                            @mousedown.stop
                            @click.stop="translateField(field, titleTranslations[field])"
                        />
                    </template>
                </v-text-field>
            </v-col>
        </v-row>

        <!-- Attribute groups, labelled in this language -->
        <v-expansion-panels
            v-model="openGroups"
            multiple
            class="mt-4"
        >
            <v-expansion-panel
                v-for="group in variantGroups"
                :key="group.id"
                :value="group.id"
            >
                <v-expansion-panel-title class="text-primary text-body-1 text-uppercase pa-3">
                    <bdi dir="auto">{{ group.label }}</bdi>
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                    <div
                        v-for="item in group.items"
                        :key="item.attributeItem.attribute_group_item.id"
                        class="mb-4"
                    >
                        <div class="d-flex align-center font-weight-bold text-primary mb-1">
                            <bdi dir="auto">{{ item.label }}</bdi>
                            <v-chip
                                v-if="!item.translated"
                                size="x-small"
                                variant="outlined"
                                class="ms-2"
                            >
                                {{ t('report_item.translation.same_in_all_languages') }}
                            </v-chip>
                        </div>

                        <template v-if="item.translated">
                            <div
                                v-for="value in item.variantValues"
                                :key="String(value.id)"
                                class="d-flex align-center ga-2 mb-1"
                            >
                                <div
                                    class="source-text text-caption text-medium-emphasis flex-grow-1"
                                    dir="auto"
                                >
                                    <span class="me-1">{{ t('report_item.translation.source') }}:</span>
                                    <span
                                        v-if="item.html"
                                        v-html="sanitizeRichTextHtml(String(value.source?.value ?? ''))"
                                    />
                                    <span v-else>{{ value.source?.value }}</span>
                                </div>
                                <TranslationState
                                    :state="value.state"
                                    :reviewable="canModify && value.locked !== true && !reviewing"
                                    @review="review([String(value.id)])"
                                />
                                <v-btn
                                    v-if="canTranslate && value.source?.value"
                                    icon="mdi-translate"
                                    variant="text"
                                    density="compact"
                                    size="small"
                                    :disabled="busy || value.locked === true"
                                    :loading="translatingKey === String(value.id)"
                                    :title="t('report_item.translation.translate_field')"
                                    @click="translateField(String(value.id), value.state)"
                                />
                            </div>
                            <AttributeContainer
                                :attribute-item="item.attributeItem"
                                :edit="true"
                                :modify="modify"
                                :report-item-id="reportItemId"
                                :read-only="!canModify"
                                :language="language"
                            />
                        </template>
                        <AttributeContainer
                            v-else
                            :attribute-item="item.attributeItem"
                            :edit="true"
                            :modify="modify"
                            :report-item-id="reportItemId"
                            :read-only="true"
                            :language="item.constants ? language : null"
                        />
                    </div>
                </v-expansion-panel-text>
            </v-expansion-panel>
        </v-expansion-panels>

        <ConfirmationDialog
            v-model="confirmOverwrite"
            title-key="report_item.translation.overwrite_title"
            confirm-label-key="report_item.translation.overwrite_confirm"
            :message="t('report_item.translation.overwrite_message')"
            @confirm="runPendingTranslation"
        />
    </div>
</template>

<script setup lang="ts">
    import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
    import { useI18n } from 'vue-i18n'
    import {
        holdLockReportItem,
        lockReportItem,
        reviewReportItemTranslations,
        translateReportItem,
        unlockReportItem,
        updateReportItem,
        getReportItemData
    } from '@/api/analyze'
    import AttributeContainer from '@/components/common/attribute/AttributeContainer.vue'
    import ConfirmationDialog from '@/components/common/dialogs/ConfirmationDialog.vue'
    import TranslationState, { type TranslationStateValue } from '@/components/analyze/TranslationState.vue'
    import { TRANSLATABLE_TYPES, useContentLanguages } from '@/composables/useContentLanguages'
    import { useAuth } from '@/composables/useAuth'
    import { sanitizeRichTextHtml } from '@/utils/sanitizeRichTextHtml'

    /**
     * One language variant of a report item. Name, prefix and the text attributes ticked for
     * translation are edited here; everything else is shown as in the source, read only.
     * Values are saved one by one like the source's, with `language` set, and locked per
     * language. The parent owns the report and refreshes `revision` when translations were
     * replaced from the server (AI, a reload).
     */

    type TitleField = 'title' | 'title_prefix'
    type Translations = Record<string, TranslationStateValue>
    type SourceValue = { id?: number | string; value?: unknown; remote?: boolean; translations?: Translations }
    type GroupItem = {
        id: number
        title?: string
        translate?: boolean
        translations?: Record<string, Record<string, string>>
        attribute?: { type?: string }
        [key: string]: unknown
    }
    type SourceGroup = { id: number; title?: string; attribute_group_items: { attribute_group_item: GroupItem; values: SourceValue[] }[] }
    type ReportType = { attribute_groups?: { id: number; title?: string; translations?: Record<string, Record<string, string>> }[] }
    type VariantValue = {
        id: number | string | undefined
        index: number
        value: string
        version: number
        locked: boolean
        user: { name: string } | null
        last_updated: unknown
        source: SourceValue
        state: TranslationStateValue | null
    }

    const props = withDefaults(
        defineProps<{
            reportItemId: number
            language: string
            title: string
            titlePrefix: string
            titleTranslations: Partial<Record<TitleField, TranslationStateValue>>
            attributeGroups: SourceGroup[]
            reportType?: ReportType | null
            locks?: Record<string, { user_id?: number }>
            canModify?: boolean
            modify?: boolean
            canTranslate?: boolean
            busy?: boolean
            revision?: number
            spellcheck?: boolean
        }>(),
        {
            reportType: null,
            locks: () => ({}),
            canModify: false,
            modify: false,
            canTranslate: false,
            busy: false,
            revision: 0,
            spellcheck: true
        }
    )

    const emit = defineEmits<{
        (e: 'translate-language', language: string): void
        (
            e: 'translations-updated',
            data: { translations: Record<string, Record<string, TranslationStateValue>>; attributes: Record<string, Translations> }
        ): void
    }>()

    const { t } = useI18n()
    const { languageName } = useContentLanguages()
    const { getUserId } = useAuth()

    const titleFields: TitleField[] = ['title_prefix', 'title']
    const titles = reactive<Record<TitleField, string>>({ title: '', title_prefix: '' })
    const titleBaseline = reactive<Record<TitleField, string>>({ title: '', title_prefix: '' })
    const titleLocks = reactive<Record<TitleField, boolean>>({ title: false, title_prefix: false })
    const focusedTitle = ref<TitleField | null>(null)
    const translatingKey = ref<string | null>(null)
    const confirmOverwrite = ref(false)
    const pendingKey = ref<string | null>(null)
    const keyTimeout = ref<ReturnType<typeof setTimeout> | null>(null)

    const lockId = (field: string): string => `${field}:${props.language}`
    const lockedByOthers = (field: string): boolean => {
        const lock = props.locks?.[lockId(field)]
        return !!lock && lock.user_id !== getUserId()
    }

    const sourceTitle = (field: TitleField): string => String(field === 'title' ? props.title : props.titlePrefix) || ''

    // ---- variant groups -------------------------------------------------------------
    const isTranslated = (item: GroupItem): boolean =>
        !!item.translate && (TRANSLATABLE_TYPES as readonly string[]).includes(String(item.attribute?.type ?? ''))

    const labelOf = (translations: Record<string, Record<string, string>> | undefined, fallback: string | undefined): string =>
        translations?.[props.language]?.['title'] || fallback || ''

    const buildValue = (source: SourceValue, index: number): VariantValue => {
        const state = source.translations?.[props.language] ?? null
        return {
            id: source.id,
            index,
            value: state?.value ?? '',
            version: state?.version ?? 0,
            locked: lockedByOthers(String(source.id)),
            user: state?.user ? { name: state.user } : null,
            last_updated: state?.last_updated,
            source,
            state
        }
    }

    const buildGroups = () =>
        props.attributeGroups.map((group) => {
            const typeGroup = props.reportType?.attribute_groups?.find((candidate) => candidate.id === group.id)
            return {
                id: group.id,
                label: labelOf(typeGroup?.translations, group.title),
                items: group.attribute_group_items.map((entry) => {
                    const item = entry.attribute_group_item
                    const translated = isTranslated(item)
                    // The translated values are edited through the same attribute components as
                    // the source, so they share one array with what the container receives.
                    const variantValues = translated
                        ? entry.values.filter((value) => !value.remote && value.id !== undefined).map(buildValue)
                        : []
                    return {
                        label: labelOf(item.translations, item.title),
                        translated,
                        // Choice constants read in this language (their translations are configured on the attribute).
                        constants: ['ENUM', 'RADIO', 'MULTI_CHOICE'].includes(String(item.attribute?.type ?? '')),
                        html: item.attribute?.type === 'RICH_TEXT',
                        variantValues,
                        attributeItem: translated ? { attribute_group_item: item, values: variantValues } : entry
                    }
                })
            }
        })

    const variantGroups = ref(buildGroups())
    const openGroups = ref<number[]>(props.attributeGroups.map((group) => group.id))

    // Which translated values exist, to tell whether the form must be rebuilt or only refilled.
    const structureOf = (groups: { items: { translated: boolean; variantValues: VariantValue[] }[] }[]): string =>
        groups
            .map((group) =>
                group.items.map((item) => (item.translated ? item.variantValues.map((value) => value.id).join(',') : '-')).join('|')
            )
            .join('/')

    // Refill translated values from the source copies; rebuild only when values came or went.
    const syncFromSource = () => {
        const fresh = buildGroups()
        if (structureOf(fresh) !== structureOf(variantGroups.value)) {
            variantGroups.value = fresh
            return
        }
        for (const group of variantGroups.value) {
            for (const item of group.items) {
                if (!item.translated) continue
                for (const value of item.variantValues) {
                    const fresh = buildValue(value.source, value.index)
                    Object.assign(value, {
                        value: fresh.value,
                        version: fresh.version,
                        user: fresh.user,
                        last_updated: fresh.last_updated,
                        state: fresh.state
                    })
                }
            }
        }
    }

    // ---- name and prefix ------------------------------------------------------------
    const syncTitles = () => {
        for (const field of titleFields) {
            const stored = props.titleTranslations[field]?.value ?? ''
            if (focusedTitle.value === field && titles[field] !== titleBaseline[field]) continue
            titles[field] = stored
            titleBaseline[field] = stored
            titleLocks[field] = lockedByOthers(field)
        }
    }

    const onTitleFocus = (field: TitleField) => {
        focusedTitle.value = field
        titleBaseline[field] = titles[field]
        lockReportItem(props.reportItemId, { field_id: lockId(field) }).catch(() => {})
    }

    const onTitleKeyUp = (field: TitleField) => {
        if (keyTimeout.value) clearTimeout(keyTimeout.value)
        keyTimeout.value = setTimeout(() => {
            holdLockReportItem(props.reportItemId, { field_id: lockId(field) }).catch(() => {})
        }, 1000)
    }

    const onTitleBlur = async (field: TitleField) => {
        if (focusedTitle.value === field) focusedTitle.value = null
        if (titles[field] !== titleBaseline[field]) {
            titleBaseline[field] = titles[field]
            try {
                await updateReportItem(props.reportItemId, { update: true, language: props.language, [field]: titles[field] })
            } catch (error) {
                notifyError(error)
            }
        }
        unlockReportItem(props.reportItemId, { field_id: lockId(field) }).catch(() => {})
    }

    // ---- AI ------------------------------------------------------------------------
    const notifyError = (error: unknown) => {
        // Core names the reason (no provider, the provider's TLP limit ...).
        const message = (error as { response?: { data?: { error?: string } } })?.response?.data?.error
        window.dispatchEvent(
            new CustomEvent('notification', {
                detail: message ? { type: 'error', message } : { type: 'error', loc: 'common.error_saving' }
            })
        )
    }

    const translateField = (key: string, state: TranslationStateValue | null | undefined) => {
        pendingKey.value = key
        // A translation a person wrote is only replaced after asking.
        if (state?.origin === 'manual' && state.value) {
            confirmOverwrite.value = true
            return
        }
        runPendingTranslation(false)
    }

    const runPendingTranslation = async (overwrite = true) => {
        const key = pendingKey.value
        confirmOverwrite.value = false
        pendingKey.value = null
        if (!key) return
        translatingKey.value = key
        try {
            const response = (await translateReportItem(props.reportItemId, {
                languages: [props.language],
                fields: [key],
                overwrite_manual: overwrite
            })) as {
                data?: {
                    results?: Array<{ failed?: Record<string, string>; skipped_locked?: string[] }>
                    translations?: {
                        translations: Record<string, Record<string, TranslationStateValue>>
                        attributes: Record<string, Translations>
                    }
                }
            }
            const result = response.data?.results?.[0]
            if (result?.skipped_locked?.length) {
                window.dispatchEvent(
                    new CustomEvent('notification', { detail: { type: 'warning', loc: 'report_item.translation.field_locked' } })
                )
            } else if (result?.failed && Object.keys(result.failed).length > 0) {
                const reason = Object.values(result.failed)[0]
                window.dispatchEvent(
                    new CustomEvent('notification', {
                        detail: { type: 'error', loc: 'report_item.translation.field_failed', params: { reason } }
                    })
                )
            }
            if (response.data?.translations) emit('translations-updated', response.data.translations)
        } catch (error) {
            notifyError(error)
        } finally {
            translatingKey.value = null
        }
    }

    // ---- review ---------------------------------------------------------------------
    const reviewing = ref(false)

    // The AI translations of this language nobody has edited or reviewed yet.
    const unreviewedKeys = computed<string[]>(() => {
        const isAi = (state: TranslationStateValue | null | undefined) => state?.origin === 'ai' && !!state.value
        const titles = titleFields.filter((field) => sourceTitle(field) && isAi(props.titleTranslations[field]))
        const values = variantGroups.value
            .flatMap((group) => group.items.flatMap((item) => item.variantValues))
            .filter((value) => value.source?.value && isAi(value.state))
            .map((value) => String(value.id))
        return [...titles, ...values]
    })

    // Keeps the text: the AI translation counts as a person's, checked against the current source.
    const review = async (fields?: string[]) => {
        reviewing.value = true
        try {
            const response = (await reviewReportItemTranslations(props.reportItemId, {
                language: props.language,
                ...(fields ? { fields } : {})
            })) as {
                data?: {
                    reviewed?: string[]
                    skipped_locked?: string[]
                    translations?: {
                        translations: Record<string, Record<string, TranslationStateValue>>
                        attributes: Record<string, Translations>
                    }
                }
            }
            const result = response.data
            if (result?.skipped_locked?.length) {
                window.dispatchEvent(
                    new CustomEvent('notification', { detail: { type: 'warning', loc: 'report_item.translation.review_locked' } })
                )
            } else if (!fields && result?.reviewed?.length) {
                window.dispatchEvent(
                    new CustomEvent('notification', {
                        detail: { type: 'success', loc: 'report_item.translation.reviewed', params: { count: result.reviewed.length } }
                    })
                )
            }
            if (result?.translations) emit('translations-updated', result.translations)
        } catch (error) {
            notifyError(error)
        } finally {
            reviewing.value = false
        }
    }

    // ---- live updates of this language ----------------------------------------------
    type ReportEvent = {
        report_item_id?: number
        user_id?: number
        language?: string | null
        field_id?: string
        title?: unknown
        title_prefix?: unknown
    }

    const onLocked = (event: Event) => {
        const data = (event as CustomEvent<ReportEvent>).detail
        if (data?.report_item_id !== props.reportItemId || data.user_id === getUserId()) return
        for (const field of titleFields) if (data.field_id === lockId(field)) titleLocks[field] = true
    }

    const onUnlocked = (event: Event) => {
        const data = (event as CustomEvent<ReportEvent>).detail
        if (data?.report_item_id !== props.reportItemId || data.user_id === getUserId()) return
        for (const field of titleFields) if (data.field_id === lockId(field)) titleLocks[field] = false
    }

    const onUpdated = async (event: Event) => {
        const data = (event as CustomEvent<ReportEvent>).detail
        if (data?.report_item_id !== props.reportItemId || data.language !== props.language || data.user_id === getUserId()) return
        if (data.title === undefined && data.title_prefix === undefined) return
        try {
            const response = (await getReportItemData(props.reportItemId, data)) as { data: Record<string, unknown> }
            for (const field of titleFields) {
                if (response.data[field] === undefined) continue
                if (focusedTitle.value === field && titles[field] !== titleBaseline[field]) continue
                titles[field] = String(response.data[field] ?? '')
                titleBaseline[field] = titles[field]
            }
        } catch (error) {
            console.error('Failed to refresh a translated name:', error)
        }
    }

    watch(
        () => [props.revision, props.language],
        () => {
            syncTitles()
            syncFromSource()
        }
    )

    onMounted(() => {
        syncTitles()
        window.addEventListener('report-item-locked', onLocked)
        window.addEventListener('report-item-unlocked', onUnlocked)
        window.addEventListener('report-item-updated', onUpdated)
    })

    onUnmounted(() => {
        if (keyTimeout.value) clearTimeout(keyTimeout.value)
        window.removeEventListener('report-item-locked', onLocked)
        window.removeEventListener('report-item-unlocked', onUnlocked)
        window.removeEventListener('report-item-updated', onUpdated)
    })

    const titleTranslations = computed(() => props.titleTranslations)

    defineExpose({ variantGroups, titles, unreviewedKeys, review })
</script>

<style scoped>
    .source-text {
        white-space: pre-wrap;
        word-break: break-word;
    }

    .locked-style :deep(input) {
        color: grey !important;
        font-style: italic;
    }
</style>
