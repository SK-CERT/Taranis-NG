<template>
    <div class="d-flex align-center justify-end ga-2 flex-wrap">
        <template v-if="canExport && sourceCount > 0">
            <v-btn
                v-if="selectedIds.length < sourceCount"
                variant="text"
                size="small"
                @click="emit('select-all')"
            >
                {{ t('collectors.sources.tooltip.select_all') }}
            </v-btn>
            <v-btn
                v-if="selectedIds.length > 0"
                variant="text"
                size="small"
                @click="emit('clear-selection')"
            >
                {{ t('collectors.sources.tooltip.unselect_all') }}
            </v-btn>
            <span class="text-caption text-medium-emphasis">
                {{ t('collectors.sources.selected_count', { count: selectedIds.length }) }}
            </span>
        </template>

        <v-btn
            v-if="canImport"
            color="primary"
            variant="outlined"
            prepend-icon="mdi-import"
            :disabled="importing"
            @click="openImportDialog"
        >
            {{ t('collectors.sources.import') }}
        </v-btn>

        <v-btn
            v-if="canExport"
            color="primary"
            variant="outlined"
            prepend-icon="mdi-export"
            :loading="exporting"
            :disabled="exporting"
            :title="t(selectedIds.length > 0 ? 'collectors.sources.export_selected_hint' : 'collectors.sources.export_all_hint')"
            @click="exportSources"
        >
            {{ t('collectors.sources.export') }}
        </v-btn>
    </div>

    <v-dialog
        v-model="dialog"
        max-width="600"
        persistent
    >
        <v-card>
            <v-card-title>{{ t('collectors.sources.dialog_import') }}</v-card-title>
            <v-card-text>
                <v-form
                    ref="formRef"
                    @submit.prevent="importSources"
                >
                    <v-select
                        v-model="selectedNodeId"
                        :items="nodes"
                        item-title="name"
                        item-value="id"
                        :label="t('collectors.sources.node')"
                        :loading="loadingNodes"
                        :disabled="importing"
                        :rules="[(value) => value !== null || t('collectors.sources.node_required')]"
                        variant="outlined"
                    />
                    <v-file-input
                        v-model="importFile"
                        accept="application/json,.json"
                        :label="t('collectors.sources.file')"
                        :disabled="importing || selectedNodeId === null"
                        :rules="[(value) => hasFile(value) || t('collectors.sources.file_required')]"
                        variant="outlined"
                    />
                </v-form>
            </v-card-text>
            <v-card-actions>
                <v-spacer />
                <v-btn
                    :disabled="importing"
                    @click="closeImportDialog"
                >
                    {{ t('common.cancel') }}
                </v-btn>
                <v-btn
                    color="primary"
                    :loading="importing"
                    :disabled="importing"
                    @click="importSources"
                >
                    {{ t('collectors.sources.import') }}
                </v-btn>
            </v-card-actions>
        </v-card>
    </v-dialog>
</template>

<script setup lang="ts">
    import { ref } from 'vue'
    import { useI18n } from 'vue-i18n'
    import { exportOSINTSources, importOSINTSources } from '@/api/config'

    type CollectorNode = {
        id: string | number
        name?: string
    }

    type FormValidationResult = {
        valid: boolean
    }

    type ExportResponse = {
        data: Blob
        headers?: Record<string, string>
    }

    const props = withDefaults(
        defineProps<{
            canImport: boolean
            canExport: boolean
            nodes: CollectorNode[]
            loadingNodes?: boolean
            selectedIds: Array<string | number>
            sourceCount: number
        }>(),
        { loadingNodes: false }
    )

    const emit = defineEmits<{
        (event: 'load-nodes'): void
        (event: 'import-complete'): void
        (event: 'select-all'): void
        (event: 'clear-selection'): void
    }>()

    const { t } = useI18n()
    const dialog = ref(false)
    const importing = ref(false)
    const exporting = ref(false)
    const selectedNodeId = ref<string | number | null>(null)
    const importFile = ref<File | File[] | null>(null)
    const formRef = ref<{ validate: () => Promise<FormValidationResult>; resetValidation: () => void } | null>(null)

    const notify = (type: 'success' | 'error' | 'info', loc: string, timeout?: number): void => {
        window.dispatchEvent(
            new CustomEvent('notification', {
                detail: { id: 'osint-source-bulk-operation', type, loc, timeout }
            })
        )
    }

    const hasFile = (value: File | File[] | null): boolean => Boolean(Array.isArray(value) ? value[0] : value)

    const selectedFile = (): File | null => {
        if (Array.isArray(importFile.value)) return importFile.value[0] ?? null
        return importFile.value
    }

    const openImportDialog = (): void => {
        if (!props.canImport) return
        dialog.value = true
        emit('load-nodes')
    }

    const closeImportDialog = (): void => {
        if (importing.value) return
        dialog.value = false
        selectedNodeId.value = null
        importFile.value = null
        formRef.value?.resetValidation()
    }

    const importSources = async (): Promise<void> => {
        if (!props.canImport || importing.value || !formRef.value) return

        const { valid } = await formRef.value.validate()
        const file = selectedFile()
        if (!valid || selectedNodeId.value === null || !file) return

        const formData = new FormData()
        formData.append('file', file)
        formData.append('collectors_node_id', String(selectedNodeId.value))

        importing.value = true
        notify('info', 'collectors.sources.import_progress', 0)
        try {
            await importOSINTSources(formData)
            notify('success', 'collectors.sources.import_success')
            importing.value = false
            closeImportDialog()
            emit('import-complete')
        } catch {
            notify('error', 'collectors.sources.import_error')
        } finally {
            importing.value = false
        }
    }

    const filenameFromResponse = (response: ExportResponse): string => {
        const disposition = response.headers?.['content-disposition']
        const match = disposition?.match(/filename\*?=(?:UTF-8'')?["]?([^";\r\n]+)["]?/i)
        return match?.[1] ? decodeURIComponent(match[1]) : 'osint_sources_export.json'
    }

    const triggerDownload = (response: ExportResponse): void => {
        const url = window.URL.createObjectURL(new Blob([response.data], { type: 'application/json' }))
        const link = document.createElement('a')
        link.href = url
        link.download = filenameFromResponse(response)
        document.body.appendChild(link)
        link.click()
        link.remove()
        window.URL.revokeObjectURL(url)
    }

    const exportSources = async (): Promise<void> => {
        if (!props.canExport || exporting.value) return

        exporting.value = true
        notify('info', 'collectors.sources.export_progress', 0)
        try {
            const payload = props.selectedIds.length > 0 ? { selection: props.selectedIds } : {}
            const response = (await exportOSINTSources(payload)) as ExportResponse
            triggerDownload(response)
            notify('success', 'collectors.sources.export_success')
        } catch {
            notify('error', 'collectors.sources.export_error')
        } finally {
            exporting.value = false
        }
    }
</script>
