<template>
    <div class="d-flex flex-wrap ga-2 mb-3">
        <v-btn
            type="button"
            color="primary"
            variant="tonal"
            prepend-icon="mdi-upload"
            @click="openLocalDialog"
        >
            {{ t('word_lists.import_from_csv') }}
        </v-btn>
        <v-btn
            v-if="normalizedSourceUrl"
            type="button"
            color="primary"
            variant="tonal"
            prepend-icon="mdi-download"
            @click="openUrlDialog"
        >
            {{ t('word_lists.download_from_link') }}
        </v-btn>
    </div>

    <v-dialog
        v-model="dialog"
        max-width="800"
        persistent
        scrollable
    >
        <v-card>
            <v-toolbar
                color="primary"
                density="compact"
            >
                <v-toolbar-title>{{ dialogTitle }}</v-toolbar-title>
                <v-spacer />
                <v-btn
                    type="button"
                    variant="text"
                    :disabled="readingFile"
                    @click="closeDialog"
                >
                    {{ t('common.cancel') }}
                </v-btn>
                <v-btn
                    type="button"
                    variant="text"
                    :loading="readingFile"
                    :disabled="readingFile || csvRows.length === 0"
                    @click="importCsv"
                >
                    <v-icon start>mdi-upload</v-icon>
                    {{ t('word_lists.import') }}
                </v-btn>
            </v-toolbar>

            <v-card-text>
                <v-file-input
                    v-if="sourceMode === 'file'"
                    v-model="csvFile"
                    :label="t('word_lists.load_csv_file')"
                    accept=".csv,text/csv,text/plain"
                    prepend-icon="mdi-file-delimited"
                    variant="outlined"
                    clearable
                    @update:model-value="readCsvFile"
                />

                <v-text-field
                    v-else
                    :model-value="normalizedSourceUrl"
                    :spellcheck="false"
                    :label="t('word_lists.link')"
                    prepend-inner-icon="mdi-link"
                    variant="outlined"
                    readonly
                />

                <div class="d-flex flex-wrap align-center ga-6 mb-3">
                    <v-checkbox
                        v-model="fileHasHeader"
                        :label="t('word_lists.file_has_header')"
                        hide-details
                        @update:model-value="parseCsv"
                    />
                    <v-checkbox
                        v-model="replaceExisting"
                        :label="t('word_lists.delete_existing_words')"
                        hide-details
                    />
                </div>

                <v-alert
                    v-if="csvError"
                    type="error"
                    variant="tonal"
                    class="mb-3"
                >
                    {{ importErrorMessage }}
                </v-alert>

                <v-data-table
                    v-if="csvRows.length"
                    :headers="previewHeaders"
                    :items="csvRows"
                    :items-per-page="5"
                    density="compact"
                />
            </v-card-text>
        </v-card>
    </v-dialog>
</template>

<script setup lang="ts">
    import { computed, ref } from 'vue'
    import { useI18n } from 'vue-i18n'
    import { mergeWordListEntries, parseWordListCsv, type WordListEntry } from '@/utils/word-list-csv'

    const model = defineModel<WordListEntry[]>({ default: () => [] })
    const props = withDefaults(defineProps<{ sourceUrl?: string }>(), { sourceUrl: '' })
    const { t } = useI18n()

    type SourceMode = 'file' | 'url'

    const previewHeaders = computed(() => [
        { title: t('word_lists.value'), key: 'value', sortable: false },
        { title: t('word_lists.description'), key: 'description', sortable: false }
    ])

    const dialog = ref(false)
    const sourceMode = ref<SourceMode>('file')
    const csvFile = ref<File | File[] | null>(null)
    const csvText = ref('')
    const csvRows = ref<WordListEntry[]>([])
    const csvError = ref(false)
    const fileHasHeader = ref(true)
    const replaceExisting = ref(false)
    const readingFile = ref(false)
    const normalizedSourceUrl = computed(() => props.sourceUrl.trim())
    const dialogTitle = computed(() => (sourceMode.value === 'url' ? t('word_lists.download_from_link') : t('word_lists.import_from_csv')))
    const importErrorMessage = computed(() => (sourceMode.value === 'url' ? t('word_lists.download_error') : t('word_lists.import_error')))

    const reset = (): void => {
        csvFile.value = null
        csvText.value = ''
        csvRows.value = []
        csvError.value = false
        fileHasHeader.value = true
        replaceExisting.value = false
        readingFile.value = false
    }

    const openLocalDialog = (): void => {
        reset()
        sourceMode.value = 'file'
        dialog.value = true
    }

    const openUrlDialog = async (): Promise<void> => {
        reset()
        sourceMode.value = 'url'
        dialog.value = true
        await downloadCsv()
    }

    const closeDialog = (): void => {
        dialog.value = false
        reset()
    }

    const parseCsv = (): void => {
        csvError.value = false
        csvRows.value = []
        if (!csvText.value) return
        try {
            csvRows.value = parseWordListCsv(csvText.value, fileHasHeader.value)
        } catch {
            csvError.value = true
        }
    }

    const readCsvFile = async (selection: File | File[] | null): Promise<void> => {
        const file = Array.isArray(selection) ? selection[0] : selection
        csvText.value = ''
        csvRows.value = []
        csvError.value = false
        if (!file) return
        readingFile.value = true
        try {
            csvText.value = await file.text()
            parseCsv()
        } catch {
            csvError.value = true
        } finally {
            readingFile.value = false
        }
    }

    const downloadCsv = async (): Promise<void> => {
        csvText.value = ''
        csvRows.value = []
        csvError.value = false
        readingFile.value = true

        try {
            const url = new globalThis.URL(normalizedSourceUrl.value)
            if (url.protocol !== 'http:' && url.protocol !== 'https:') throw new Error('Unsupported URL protocol')

            // This intentionally remains a direct browser request, like Vue 2. Omitting
            // credentials prevents Taranis cookies or authorization from reaching a
            // category-controlled host; the remote server must explicitly allow CORS.
            const response = await globalThis.fetch(url, {
                credentials: 'omit',
                referrerPolicy: 'no-referrer',
                cache: 'no-store'
            })
            if (!response.ok) throw new Error(`Download failed with HTTP ${response.status}`)

            csvText.value = await response.text()
            parseCsv()
            if (!csvRows.value.length) csvError.value = true
        } catch {
            csvError.value = true
        } finally {
            readingFile.value = false
        }
    }

    const importCsv = (): void => {
        if (!csvRows.value.length) return
        model.value = mergeWordListEntries(model.value, csvRows.value, replaceExisting.value)
        closeDialog()
    }
</script>
