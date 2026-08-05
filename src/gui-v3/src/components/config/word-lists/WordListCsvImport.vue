<template>
    <v-btn
        type="button"
        color="primary"
        variant="tonal"
        prepend-icon="mdi-upload"
        class="mb-3"
        @click="openDialog"
    >
        {{ t('word_lists.import_from_csv') }}
    </v-btn>

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
                <v-toolbar-title>{{ t('word_lists.import_from_csv') }}</v-toolbar-title>
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
                    v-model="csvFile"
                    :label="t('word_lists.load_csv_file')"
                    accept=".csv,text/csv,text/plain"
                    prepend-icon="mdi-file-delimited"
                    variant="outlined"
                    clearable
                    @update:model-value="readCsvFile"
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
                    {{ t('word_lists.error') }}
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
    const { t } = useI18n()

    const previewHeaders = computed(() => [
        { title: t('word_lists.value'), key: 'value', sortable: false },
        { title: t('word_lists.description'), key: 'description', sortable: false }
    ])

    const dialog = ref(false)
    const csvFile = ref<File | File[] | null>(null)
    const csvText = ref('')
    const csvRows = ref<WordListEntry[]>([])
    const csvError = ref(false)
    const fileHasHeader = ref(true)
    const replaceExisting = ref(false)
    const readingFile = ref(false)

    const reset = (): void => {
        csvFile.value = null
        csvText.value = ''
        csvRows.value = []
        csvError.value = false
        fileHasHeader.value = true
        replaceExisting.value = false
        readingFile.value = false
    }

    const openDialog = (): void => {
        reset()
        dialog.value = true
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

    const importCsv = (): void => {
        if (!csvRows.value.length) return
        model.value = mergeWordListEntries(model.value, csvRows.value, replaceExisting.value)
        closeDialog()
    }
</script>
