<template>
    <v-card variant="outlined">
        <v-card-title class="d-flex align-center text-subtitle-1 bg-grey-lighten-4">
            <span>{{ t('asset.cpes') }}</span>
            <v-spacer />
            <v-btn
                v-if="!disabled"
                color="primary"
                variant="tonal"
                prepend-icon="mdi-upload"
                class="mr-2"
                @click="openImportDialog"
            >
                {{ t('asset.import_csv') }}
            </v-btn>
            <v-btn
                v-if="!disabled"
                color="primary"
                prepend-icon="mdi-plus"
                @click="openEditDialog()"
            >
                {{ t('asset.new_cpe') }}
            </v-btn>
        </v-card-title>

        <v-data-table
            :headers="headers"
            :items="model"
            :items-per-page="-1"
            hide-default-footer
            density="comfortable"
        >
            <template #item.actions="{ item, index }">
                <v-btn
                    :title="t('common.edit')"
                    :aria-label="t('common.edit')"
                    icon="mdi-pencil"
                    variant="text"
                    size="small"
                    @click="openEditDialog(item, index)"
                />
                <v-btn
                    :title="t('common.delete')"
                    :aria-label="t('common.delete')"
                    icon="mdi-delete"
                    variant="text"
                    size="small"
                    color="error"
                    @click="remove(index)"
                />
            </template>

            <template #no-data>
                <div class="text-center pa-4 text-grey">
                    {{ t('common.no_data') }}
                </div>
            </template>
        </v-data-table>
    </v-card>

    <v-dialog
        v-model="editDialog"
        max-width="700"
        persistent
    >
        <v-card>
            <DialogToolbar
                :title="editedIndex === -1 ? t('asset.new_cpe') : t('asset.edit_cpe')"
                :save-disabled="!editedCpe.value.trim()"
                @cancel="closeEditDialog"
                @save="save"
            />
            <v-card-text>
                <v-combobox
                    v-model="editedCpe.value"
                    v-model:search="cpeSearch"
                    :items="cpeSuggestions"
                    :label="t('asset.value')"
                    variant="outlined"
                    autofocus
                    clearable
                    :hint="t('asset.cpe_hint')"
                    persistent-hint
                    @update:search="scheduleCpeSearch"
                    @keydown.enter.prevent="save"
                />
                <v-text-field
                    v-model="editedCpe.description"
                    :label="t('asset.description')"
                    variant="outlined"
                    @keydown.enter.prevent="save"
                />
            </v-card-text>
        </v-card>
    </v-dialog>

    <v-dialog
        v-model="importDialog"
        max-width="800"
        persistent
        scrollable
    >
        <v-card>
            <v-toolbar
                color="primary"
                density="compact"
            >
                <v-toolbar-title>{{ t('asset.import_from_csv') }}</v-toolbar-title>
                <v-spacer />
                <v-btn
                    variant="text"
                    :disabled="readingFile"
                    @click="closeImportDialog"
                >
                    {{ t('common.cancel') }}
                </v-btn>
                <v-btn
                    variant="text"
                    :loading="readingFile"
                    :disabled="readingFile || csvRows.length === 0"
                    @click="importCsv"
                >
                    <v-icon start>mdi-upload</v-icon>
                    {{ t('asset.import') }}
                </v-btn>
            </v-toolbar>
            <v-card-text>
                <v-file-input
                    v-model="csvFile"
                    :label="t('asset.load_csv_file')"
                    accept=".csv,text/csv"
                    prepend-icon="mdi-file-delimited"
                    variant="outlined"
                    clearable
                    @update:model-value="readCsvFile"
                />

                <div class="d-flex flex-wrap align-center ga-6 mb-3">
                    <v-checkbox
                        v-model="fileHasHeader"
                        :label="t('asset.file_has_header')"
                        hide-details
                        @update:model-value="parseCsv"
                    />
                    <v-checkbox
                        v-model="replaceExisting"
                        :label="t('asset.replace_existing_cpes')"
                        hide-details
                    />
                </div>

                <v-alert
                    v-if="csvError"
                    type="error"
                    variant="tonal"
                    class="mb-3"
                >
                    {{ t('asset.csv_parse_error') }}
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
    import DialogToolbar from '@/components/common/dialogs/DialogToolbar.vue'
    import { getCPEAttributeEnums } from '@/api/assets'
    import type { ListResponse } from '@/types/assets'

    export type CpeEntry = {
        value: string
        description?: string
    }

    const props = withDefaults(defineProps<{ disabled?: boolean }>(), { disabled: false })
    const model = defineModel<CpeEntry[]>({ default: () => [] })
    const { t } = useI18n()

    const headers = computed(() => {
        const values = [
            { title: t('asset.value'), key: 'value', sortable: true },
            { title: t('asset.description'), key: 'description', sortable: true }
        ]
        if (!props.disabled) {
            values.push({ title: t('common.actions'), key: 'actions', sortable: false })
        }
        return values
    })
    const previewHeaders = computed(() => [
        { title: t('asset.value'), key: 'value', sortable: false },
        { title: t('asset.description'), key: 'description', sortable: false }
    ])

    const editDialog = ref(false)
    const editedIndex = ref(-1)
    const editedCpe = ref<CpeEntry>({ value: '', description: '' })
    const cpeSearch = ref('')
    const cpeSuggestions = ref<string[]>([])
    let searchTimer: ReturnType<typeof setTimeout> | undefined

    const openEditDialog = (item?: CpeEntry, index = -1): void => {
        editedIndex.value = index
        editedCpe.value = item ? { ...item } : { value: '', description: '' }
        editDialog.value = true
    }

    const scheduleCpeSearch = (): void => {
        clearTimeout(searchTimer)
        searchTimer = setTimeout(loadCpeSuggestions, 300)
    }

    const loadCpeSuggestions = async (): Promise<void> => {
        try {
            const response = (await getCPEAttributeEnums({ search: cpeSearch.value, limit: 30 })) as {
                data?: ListResponse<{ value?: string }>
            }
            cpeSuggestions.value = (response.data?.items || []).map((item) => item.value?.replaceAll('%', '*') || '').filter(Boolean)
        } catch {
            cpeSuggestions.value = []
        }
    }

    const closeEditDialog = (): void => {
        editDialog.value = false
        editedIndex.value = -1
        editedCpe.value = { value: '', description: '' }
        cpeSearch.value = ''
        cpeSuggestions.value = []
    }

    const save = (): void => {
        const value = String(editedCpe.value.value ?? '').trim()
        if (!value) return
        const next = [...model.value]
        const entry = { ...editedCpe.value, value }
        if (editedIndex.value === -1) next.push(entry)
        else next.splice(editedIndex.value, 1, entry)
        model.value = next
        closeEditDialog()
    }

    const remove = (index: number): void => {
        const next = [...model.value]
        next.splice(index, 1)
        model.value = next
    }

    const importDialog = ref(false)
    const csvFile = ref<File | File[] | null>(null)
    const csvText = ref('')
    const csvRows = ref<CpeEntry[]>([])
    const csvError = ref(false)
    const fileHasHeader = ref(true)
    const replaceExisting = ref(false)
    const readingFile = ref(false)

    const openImportDialog = (): void => {
        resetImport()
        importDialog.value = true
    }

    const closeImportDialog = (): void => {
        importDialog.value = false
        resetImport()
    }

    const resetImport = (): void => {
        csvFile.value = null
        csvText.value = ''
        csvRows.value = []
        csvError.value = false
        fileHasHeader.value = true
        replaceExisting.value = false
        readingFile.value = false
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

    const parseCsv = (): void => {
        csvError.value = false
        csvRows.value = []
        if (!csvText.value) return
        try {
            const records = parseCsvRecords(csvText.value)
            if (!records.length) return

            let valueIndex = 0
            let descriptionIndex = 1
            if (fileHasHeader.value) {
                const header = records.shift()?.map((value) => value.trim().toLowerCase()) || []
                const matchedValueIndex = header.indexOf('value')
                const matchedDescriptionIndex = header.indexOf('description')
                if (matchedValueIndex !== -1) valueIndex = matchedValueIndex
                descriptionIndex = matchedDescriptionIndex
            }

            csvRows.value = records
                .map((record) => ({
                    value: (record[valueIndex] || '').trim(),
                    description: descriptionIndex === -1 ? '' : (record[descriptionIndex] || '').trim()
                }))
                .filter((entry) => entry.value)
        } catch {
            csvError.value = true
        }
    }

    const importCsv = (): void => {
        if (!csvRows.value.length) return
        if (replaceExisting.value) {
            model.value = csvRows.value.map((entry) => ({ ...entry }))
        } else {
            const uniqueByValue = new Map<string, CpeEntry>()
            for (const entry of [...model.value, ...csvRows.value]) {
                uniqueByValue.set(entry.value, { ...entry })
            }
            model.value = [...uniqueByValue.values()]
        }
        closeImportDialog()
    }

    const parseCsvRecords = (input: string): string[][] => {
        const records: string[][] = []
        let record: string[] = []
        let field = ''
        let quoted = false

        const text = input.replace(/^\uFEFF/, '')
        for (let index = 0; index < text.length; index += 1) {
            const character = text[index]
            if (character === '"') {
                if (quoted && text[index + 1] === '"') {
                    field += '"'
                    index += 1
                } else {
                    quoted = !quoted
                }
            } else if (character === ',' && !quoted) {
                record.push(field)
                field = ''
            } else if ((character === '\n' || character === '\r') && !quoted) {
                record.push(field)
                if (record.some((value) => value.length)) records.push(record)
                record = []
                field = ''
                if (character === '\r' && text[index + 1] === '\n') index += 1
            } else {
                field += character
            }
        }

        if (quoted) throw new Error('Unterminated quoted CSV field')
        record.push(field)
        if (record.some((value) => value.length)) records.push(record)
        return records
    }
</script>
