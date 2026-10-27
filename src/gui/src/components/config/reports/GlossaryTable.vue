<template>
    <!-- Padded like the other Reports tabs (the table adds its own top margin); the report type dialog pads it already. -->
    <div
        data-test="glossary"
        :class="{ 'px-4 pt-2 pb-4': !reportItemTypeId }"
    >
        <v-alert
            v-if="reportItemTypeId"
            type="info"
            variant="tonal"
            density="compact"
            class="mb-2"
        >
            {{ t('reports.glossary.type_intro') }}
        </v-alert>

        <EditableEntityTable
            v-model:dialog="editDialog"
            v-model:search="search"
            v-model:items-per-page="pageSize"
            server
            searchable
            :items="shownRows"
            :items-length="shownRows.length"
            :items-per-page-options="[-1]"
            :loading="loading"
            :title="reportItemTypeId ? t('reports.glossary.type_title') : t('reports.glossary.title')"
            :headers="headers"
            :default-item="emptyRow"
            :add-title="t('reports.glossary.add')"
            :edit-title="t('reports.glossary.edit')"
            :no-data-text="t('reports.glossary.empty')"
            :saving="saving"
            :disabled="!canUpdate"
            dialog-max-width="600"
            @save="save"
            @delete="askDelete"
        >
            <template #item.terms="{ item }">
                <div class="d-flex flex-wrap column-gap-4 py-1">
                    <span
                        v-for="code in filledLanguages(item)"
                        :key="code"
                        :data-test="`glossary-cell-${code}`"
                    >
                        <span
                            class="text-caption text-medium-emphasis me-1"
                            :title="languageName(code)"
                            >{{ code.toUpperCase() }}</span
                        >
                        <bdi dir="auto">{{ item[`term_${code}`] }}</bdi>
                    </span>
                </div>
            </template>
            <template #item.keep="{ item }">
                <v-icon
                    v-if="item.keep"
                    icon="mdi-lock-outline"
                    size="small"
                    :title="t('reports.glossary.keep')"
                />
            </template>
            <template #item.note="{ item }">
                <bdi dir="auto">{{ item.note }}</bdi>
            </template>

            <template #form="{ item }">
                <v-checkbox
                    v-model="item.keep"
                    :label="t('reports.glossary.keep')"
                    :hint="t('reports.glossary.keep_hint')"
                    persistent-hint
                    density="compact"
                    class="mb-3"
                    data-test="glossary-keep"
                />
                <v-text-field
                    v-for="code in formLanguages(item)"
                    :key="code"
                    v-model="item[`term_${code}`]"
                    :label="languageName(code)"
                    variant="outlined"
                    density="comfortable"
                    class="mb-1"
                    dir="auto"
                    :data-test="`glossary-term-${code}`"
                >
                    <template #append>
                        <v-btn
                            icon="mdi-close"
                            variant="text"
                            size="small"
                            :title="t('reports.glossary.remove_language', { language: languageName(code) })"
                            :aria-label="t('reports.glossary.remove_language', { language: languageName(code) })"
                            :disabled="!canUpdate"
                            :data-test="`glossary-remove-${code}`"
                            @click="removeLanguage(item, code)"
                        />
                    </template>
                </v-text-field>
                <v-autocomplete
                    v-model="addedLanguage"
                    :items="otherLanguages(item)"
                    item-title="txt"
                    item-value="id"
                    :label="t('reports.glossary.add_language')"
                    prepend-inner-icon="mdi-plus"
                    variant="outlined"
                    density="comfortable"
                    class="mb-1"
                    hide-details
                    data-test="glossary-add-language"
                    @update:model-value="(code: string | null) => addLanguage(item, code)"
                />
                <!-- Holds back Save, with the reason, until the entry has enough terms. -->
                <v-input
                    :model-value="isComplete(item)"
                    :rules="[(value: boolean) => value || t('reports.glossary.needs_terms')]"
                    class="mt-2"
                    data-test="glossary-complete"
                />
                <v-textarea
                    v-model="item.note"
                    :label="t('reports.glossary.note')"
                    :hint="t('reports.glossary.note_hint')"
                    persistent-hint
                    variant="outlined"
                    density="comfortable"
                    rows="2"
                    class="mt-4"
                    dir="auto"
                />
            </template>
        </EditableEntityTable>

        <ConfirmationDialog
            v-model="dialogDelete"
            :message="t('common.messagebox.delete_confirm_item')"
            max-width="500"
            @confirm="deleteRecord"
        />
    </div>
</template>

<script setup lang="ts">
    import { computed, onMounted, ref } from 'vue'
    import { useI18n } from 'vue-i18n'
    import EditableEntityTable from '@/components/common/EditableEntityTable.vue'
    import ConfirmationDialog from '@/components/common/dialogs/ConfirmationDialog.vue'
    import { useAuth } from '@/composables/useAuth'
    import { useContentLanguages } from '@/composables/useContentLanguages'
    import { createGlossaryEntry, deleteGlossaryEntry, getGlossary, updateGlossaryEntry } from '@/api/config'

    /**
     * The AI translation glossary: of the instance, or a report type's own entries
     * (`reportItemTypeId`). Each entry is saved at once, its terms in one column, each marked
     * with its language. Terms sit in the row as `term_<code>`, so the dialog's copy of a row is a
     * full copy; a `term_<code>` key, even empty, is a field the form shows. An entry offers a
     * field for each report language, and its languages are added and removed one by one.
     */

    type Entry = { id: number; terms: Record<string, string>; keep: boolean; note: string }
    type Row = { id: number; keep: boolean; note: string } & Record<string, unknown>

    const props = withDefaults(
        defineProps<{
            reportItemTypeId?: number | null
            /** Languages offered besides those the server reports, e.g. a type's unsaved ones. */
            languages?: Array<string | null>
        }>(),
        { reportItemTypeId: null, languages: () => [] }
    )

    const { t } = useI18n()
    const { checkPermission } = useAuth()
    const { languageName, languageOptions } = useContentLanguages()

    const entries = ref<Entry[]>([])
    const serverLanguages = ref<string[]>([])
    const addedLanguage = ref<string | null>(null)
    const search = ref('')
    const pageSize = ref(-1)
    const loading = ref(false)
    const saving = ref(false)
    const editDialog = ref(false)
    const dialogDelete = ref(false)
    const toDelete = ref<Row | null>(null)

    const canUpdate = computed(() => checkPermission('CONFIG_REPORT_TYPE_UPDATE'))

    // The report languages, each a field an entry starts with.
    const suggestedLanguages = computed(() => [
        ...new Set([...serverLanguages.value, ...props.languages.filter((code): code is string => !!code)])
    ])

    const headers = computed(() => [
        { title: t('reports.glossary.terms'), key: 'terms', sortable: false },
        { title: t('reports.glossary.keep'), key: 'keep', sortable: false, width: '80px' },
        { title: t('reports.glossary.note'), key: 'note', sortable: false },
        { title: t('settings.actions'), key: 'actions', align: 'end' as const, sortable: false }
    ])

    const termKey = (code: string): string => `term_${code}`
    const blankTerms = (): Record<string, string> => Object.fromEntries(suggestedLanguages.value.map((code) => [termKey(code), '']))

    // The suggested languages first, then the entry's others; a language added later goes last.
    const toRow = (entry: Entry): Row => ({
        id: entry.id,
        keep: entry.keep,
        note: entry.note,
        ...blankTerms(),
        ...Object.fromEntries(
            Object.entries(entry.terms)
                .sort(([left], [right]) => left.localeCompare(right))
                .map(([code, term]) => [termKey(code), term])
        )
    })

    const formLanguages = (row: Row): string[] =>
        Object.keys(row).flatMap((key) => (key.startsWith('term_') ? [key.slice('term_'.length)] : []))
    const filledLanguages = (row: Row): string[] => formLanguages(row).filter((code) => String(row[termKey(code)] ?? '').trim())
    const otherLanguages = (row: Row) => languageOptions.value.filter((option) => !(termKey(String(option.id)) in row))
    const rows = computed(() => entries.value.map(toRow))
    const shownRows = computed(() => {
        const needle = search.value.trim().toLocaleLowerCase()
        if (!needle) return rows.value
        return entries.value
            .filter((entry) => [...Object.values(entry.terms), entry.note].some((text) => text.toLocaleLowerCase().includes(needle)))
            .map(toRow)
    })

    const emptyRow = (): Row => ({ id: -1, keep: false, note: '', ...blankTerms() })

    const termsOf = (row: Row): Record<string, string> =>
        Object.fromEntries(
            Object.entries(row)
                .filter(([key, value]) => key.startsWith('term_') && typeof value === 'string' && value.trim())
                .map(([key, value]) => [key.slice('term_'.length), String(value).trim()])
        )

    // Mirrors the server's rule: a term to keep needs the term, any other entry two languages.
    const isComplete = (row: Row): boolean => Object.keys(termsOf(row)).length >= (row.keep ? 1 : 2)

    const notifyServerError = (error: unknown): void => {
        const message = (error as { response?: { data?: { error?: string } } })?.response?.data?.error
        window.dispatchEvent(
            new CustomEvent('notification', { detail: message ? { type: 'error', message } : { type: 'error', loc: 'common.error_saving' } })
        )
    }

    async function load(): Promise<void> {
        loading.value = true
        try {
            const response = (await getGlossary(props.reportItemTypeId)) as { data?: { items?: Entry[]; languages?: string[] } }
            entries.value = response.data?.items ?? []
            serverLanguages.value = response.data?.languages ?? []
        } catch (error) {
            console.error('Error loading the glossary:', error)
        } finally {
            loading.value = false
        }
    }

    function addLanguage(row: Row, code: string | null): void {
        if (code && !(termKey(code) in row)) row[termKey(code)] = ''
        // Cleared on the next tick, so the autocomplete takes the reset.
        setTimeout(() => (addedLanguage.value = null))
    }

    // Drops the language from this entry only; its term goes with it on save.
    function removeLanguage(row: Row, code: string): void {
        Reflect.deleteProperty(row, termKey(code))
    }

    async function save(row: Row, { isNew }: { isNew: boolean }): Promise<void> {
        saving.value = true
        try {
            const entry = { terms: termsOf(row), keep: Boolean(row.keep), note: String(row.note ?? '') }
            if (isNew) await createGlossaryEntry({ ...entry, report_item_type_id: props.reportItemTypeId })
            else await updateGlossaryEntry(row.id, entry)
            editDialog.value = false
            await load()
        } catch (error) {
            notifyServerError(error)
        } finally {
            saving.value = false
        }
    }

    function askDelete(row: Row): void {
        toDelete.value = row
        dialogDelete.value = true
    }

    async function deleteRecord(): Promise<void> {
        if (!toDelete.value) return
        try {
            await deleteGlossaryEntry(toDelete.value.id)
            await load()
        } catch (error) {
            notifyServerError(error)
        } finally {
            dialogDelete.value = false
            toDelete.value = null
        }
    }

    onMounted(load)

    defineExpose({ load, entries, suggestedLanguages, save, isComplete, addLanguage, removeLanguage })
</script>
