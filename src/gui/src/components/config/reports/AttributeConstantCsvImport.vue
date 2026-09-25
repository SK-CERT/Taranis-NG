<template>
    <v-btn
        v-if="show"
        type="button"
        color="primary"
        variant="tonal"
        prepend-icon="mdi-upload"
        :disabled="busy"
        @click="openDialog"
    >
        {{ t('attribute.import_from_csv') }}
    </v-btn>

    <v-dialog
        v-model="dialog"
        max-width="820"
        persistent
        scrollable
    >
        <v-card>
            <v-toolbar
                color="primary"
                density="compact"
            >
                <v-toolbar-title>{{ t('attribute.import_from_csv') }}</v-toolbar-title>
                <v-spacer />
                <v-btn
                    type="button"
                    variant="text"
                    :disabled="busy"
                    @click="closeDialog"
                >
                    {{ t('common.cancel') }}
                </v-btn>
                <v-btn
                    type="button"
                    variant="text"
                    :loading="busy"
                    :disabled="busy || previewRows.length === 0"
                    @click="submitImport"
                >
                    <v-icon start>mdi-upload</v-icon>
                    {{ t('attribute.import') }}
                </v-btn>
            </v-toolbar>

            <v-progress-linear
                v-if="busy"
                indeterminate
                color="primary"
            />

            <v-card-text>
                <v-file-input
                    v-model="csvFile"
                    :label="t('attribute.load_csv_file')"
                    accept=".csv,text/csv,text/plain"
                    prepend-icon="mdi-file-delimited"
                    variant="outlined"
                    clearable
                    :disabled="busy"
                    @update:model-value="readCsvFile"
                />

                <div class="d-flex flex-wrap align-center ga-6 mb-3">
                    <v-checkbox
                        v-model="fileHasHeader"
                        :label="t('attribute.file_has_header')"
                        hide-details
                        :disabled="busy"
                        @update:model-value="parseCsv"
                    />
                    <v-checkbox
                        v-model="replaceExisting"
                        :label="t('attribute.delete_existing')"
                        hide-details
                        :disabled="busy"
                    />
                </div>

                <v-row v-if="columnOptions.length">
                    <v-col
                        cols="12"
                        md="6"
                    >
                        <v-select
                            v-model="valueColumn"
                            :items="columnOptions"
                            :label="t('attribute.value')"
                            variant="outlined"
                            density="comfortable"
                            :disabled="busy"
                        />
                    </v-col>
                    <v-col
                        cols="12"
                        md="6"
                    >
                        <v-select
                            v-model="descriptionColumn"
                            :items="descriptionColumnOptions"
                            :label="t('attribute.description')"
                            variant="outlined"
                            density="comfortable"
                            clearable
                            :disabled="busy"
                        />
                    </v-col>
                </v-row>

                <v-alert
                    v-if="errorMessage"
                    type="error"
                    variant="tonal"
                    class="mb-3"
                >
                    {{ errorMessage }}
                </v-alert>

                <v-data-table
                    v-if="previewRows.length"
                    :headers="previewHeaders"
                    :items="previewRows"
                    :items-per-page="5"
                    density="compact"
                />
            </v-card-text>
        </v-card>
    </v-dialog>
</template>

<script setup lang="ts">
    import { computed, ref, watch } from 'vue'
    import { useI18n } from 'vue-i18n'
    import { mapAttributeConstantRows, readAttributeConstantCsv, type AttributeConstantImport } from '@/utils/attribute-constant-csv'

    type ColumnOption = { title: string; value: number }

    const props = withDefaults(
        defineProps<{
            show?: boolean
            busy?: boolean
            error?: string
        }>(),
        {
            show: true,
            busy: false,
            error: ''
        }
    )

    const emit = defineEmits<{
        (e: 'import', payload: { items: AttributeConstantImport[]; replaceExisting: boolean }): void
    }>()

    const dialog = defineModel<boolean>({ default: false })
    const { t } = useI18n()
    const csvFile = ref<File | File[] | null>(null)
    const csvText = ref('')
    const rawRecords = ref<string[][]>([])
    const columnOptions = ref<ColumnOption[]>([])
    const valueColumn = ref<number | null>(null)
    const descriptionColumn = ref<number | null>(null)
    const fileHasHeader = ref(true)
    const replaceExisting = ref(false)
    const readingFile = ref(false)
    const parseError = ref('')

    const busy = computed(() => props.busy || readingFile.value)
    const errorMessage = computed(() => props.error || parseError.value)
    const descriptionColumnOptions = computed(() => columnOptions.value.filter((option) => option.value !== valueColumn.value))
    const previewRows = computed(() => mapAttributeConstantRows(rawRecords.value, valueColumn.value, descriptionColumn.value))
    const previewHeaders = computed(() => [
        { title: t('attribute.value'), key: 'value', sortable: false },
        { title: t('attribute.description'), key: 'description', sortable: false }
    ])

    const reset = (): void => {
        csvFile.value = null
        csvText.value = ''
        rawRecords.value = []
        columnOptions.value = []
        valueColumn.value = null
        descriptionColumn.value = null
        fileHasHeader.value = true
        replaceExisting.value = false
        readingFile.value = false
        parseError.value = ''
    }

    const openDialog = (): void => {
        reset()
        dialog.value = true
    }

    const closeDialog = (): void => {
        if (busy.value) return
        dialog.value = false
        reset()
    }

    const parseCsv = (): void => {
        parseError.value = ''
        rawRecords.value = []
        columnOptions.value = []
        if (!csvText.value) return
        try {
            const parsed = readAttributeConstantCsv(csvText.value, fileHasHeader.value)
            rawRecords.value = parsed.records
            columnOptions.value = parsed.headers.map((header, index) => ({ title: header, value: index }))
            const normalizedHeaders = parsed.headers.map((header) => header.trim().toLocaleLowerCase())
            valueColumn.value = normalizedHeaders.indexOf('value')
            if (valueColumn.value < 0) valueColumn.value = parsed.headers.length > 0 ? 0 : null
            descriptionColumn.value = normalizedHeaders.indexOf('description')
            if (descriptionColumn.value < 0) descriptionColumn.value = parsed.headers.length > 1 ? 1 : null
            if (descriptionColumn.value === valueColumn.value) descriptionColumn.value = null
            if (previewRows.value.length === 0) parseError.value = t('common.no_data')
        } catch {
            parseError.value = t('common.error')
        }
    }

    const readCsvFile = async (selection: File | File[] | null): Promise<void> => {
        const file = Array.isArray(selection) ? selection[0] : selection
        csvText.value = ''
        rawRecords.value = []
        parseError.value = ''
        if (!file) return
        readingFile.value = true
        try {
            csvText.value = await file.text()
            parseCsv()
        } catch {
            parseError.value = t('common.error')
        } finally {
            readingFile.value = false
        }
    }

    const submitImport = (): void => {
        if (previewRows.value.length === 0) return
        emit('import', { items: previewRows.value, replaceExisting: replaceExisting.value })
    }

    watch(valueColumn, (column) => {
        if (descriptionColumn.value === column) descriptionColumn.value = null
    })
</script>
