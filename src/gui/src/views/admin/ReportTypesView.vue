<template>
    <v-container
        fluid
        class="pa-0"
    >
        <!-- Toolbar -->
        <ToolbarFilter
            :total-count="configStore.reportItemTypesConfig.total_count"
            :selected-count="selectedIds.length"
            :show-selected-count="reportTypesMultiSelectActive"
            total-count-title="reports.types.total_count"
            @update-filter="handleFilterUpdate"
        >
            <template #prepend>
                <ToolbarGroup
                    view="reports.types"
                    @report-types-import="openImportDialog"
                    @report-types-export="exportReportTypesDefinitions"
                    @select-all="selectAll"
                    @clear-selection="clearSelection"
                />
            </template>
            <template #addbutton>
                <NewReportType
                    :edit-item="editItem"
                    @saved="handleSaved"
                />
            </template>
        </ToolbarFilter>

        <!-- Content -->
        <ContentData
            :items="configStore.reportItemTypesConfig.items"
            card-item="CardCompact"
            :multi-select-active="reportTypesMultiSelectActive"
            :selected-ids="selectedIds"
            delete-permission="CONFIG_REPORT_TYPE_DELETE"
            :loading="loading"
            @delete="handleDelete"
            @edit="handleEdit"
            @refresh="loadData"
            @selection-change="handleSelectionChange"
        />
    </v-container>

    <v-dialog
        v-model="importDialog"
        max-width="600"
        persistent
    >
        <v-card>
            <v-card-title>{{ t('reports.types.dialog_import') }}</v-card-title>
            <v-card-text>
                <v-form
                    ref="importFormRef"
                    @submit.prevent="importReportTypesDefinitions"
                >
                    <v-file-input
                        v-model="importFile"
                        accept="application/json,.json"
                        :label="t('reports.types.file')"
                        :disabled="importing"
                        :rules="[(value) => hasFile(value) || t('reports.types.file_required')]"
                        variant="outlined"
                        :truncate-length="40"
                    />
                    <div class="text-caption text-grey">
                        {{ t('reports.types.import_hint') }}
                    </div>
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
                    @click="importReportTypesDefinitions"
                >
                    {{ t('reports.types.import') }}
                </v-btn>
            </v-card-actions>
        </v-card>
    </v-dialog>
</template>

<script setup lang="ts">
    import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
    import { useI18n } from 'vue-i18n'
    import { useConfigStore } from '@/stores/config'
    import { useReportTypesStore } from '@/stores/report_types'
    import { deleteReportItemType, exportReportTypes, importReportTypes } from '@/api/config'
    import ToolbarFilter from '@/components/common/ToolbarFilter.vue'
    import ContentData from '@/components/common/ContentData.vue'
    import ToolbarGroup from '@/components/common/ToolbarGroup.vue'
    import NewReportType from '@/components/config/reports/NewReportType.vue'
    import { useAuth } from '@/composables/useAuth'
    import { notifyDeleteError } from '@/utils/deleteError'

    const { t } = useI18n()
    const configStore = useConfigStore()
    const { checkPermission } = useAuth()
    const reportTypesStore = useReportTypesStore()
    const { getReportTypesSelection, multiSelectReportType, selectReportType, deselectReportType } = reportTypesStore

    type FilterState = {
        search: string
    }

    type ReportTypeItem = {
        id?: string | number | null
        title?: string
        description?: string
        [key: string]: unknown
    }

    type ImportResult = {
        report_types_created?: number
        report_types_skipped?: string[]
        attribute_types_created?: number
        fields_skipped?: string[]
    }

    type FormValidationResult = {
        valid: boolean
    }

    type ExportResponse = {
        data: Blob
        headers?: Record<string, string>
    }

    const loading = ref(false)
    const filter = ref<FilterState>({ search: '' })
    const editItem = ref<ReportTypeItem | null>(null)
    const selectedIds = ref<Array<string | number>>([])

    const canExport = computed(() => checkPermission('CONFIG_REPORT_TYPE_ACCESS'))
    const canImport = computed(() => checkPermission('CONFIG_REPORT_TYPE_CREATE'))
    const reportTypesMultiSelectActive = computed(() => reportTypesStore.getReportTypesMultiSelect)
    const typeItems = computed(() => configStore.reportItemTypesConfig.items as ReportTypeItem[])

    const loadData = async (): Promise<void> => {
        loading.value = true
        try {
            await configStore.loadReportItemTypesConfig(filter.value)
        } catch (error) {
            console.error('Error loading report types:', error)
        } finally {
            loading.value = false
        }
    }

    const handleFilterUpdate = (newFilter: FilterState): void => {
        filter.value = newFilter
        loadData()
    }

    const handleDelete = async (reportType: ReportTypeItem): Promise<void> => {
        try {
            await deleteReportItemType(reportType)
            console.log('Report type deleted successfully')
            await loadData()
        } catch (error) {
            console.error('Error deleting report type:', error)
            // The backend refuses to delete a report type that report items are based on.
            const count = (error as { response?: { data?: { report_item_count?: number } } })?.response?.data?.report_item_count
            if (count) {
                window.dispatchEvent(
                    new CustomEvent('notification', { detail: { type: 'error', loc: 'reports.types.in_use', params: { count } } })
                )
            } else {
                notifyDeleteError(error, { inUse: 'reports.types.removed_error' })
            }
        }
    }

    const handleEdit = async (reportType: ReportTypeItem): Promise<void> => {
        // Reset first so re-selecting the same row reopens the dialog.
        editItem.value = null
        await nextTick()
        editItem.value = reportType
    }

    const handleSaved = (): void => {
        editItem.value = null
        loadData()
    }

    const handleSelectionChange = (item: ReportTypeItem, selected: boolean): void => {
        const id = item.id
        if (id === undefined || id === null) return
        const selectedSet = new Set(selectedIds.value)
        if (selected) {
            selectedSet.add(id)
            selectReportType({ id, item })
        } else {
            selectedSet.delete(id)
            deselectReportType({ id, item })
        }
        selectedIds.value = [...selectedSet]
    }

    // "Select all" fills exactly the rows currently rendered
    const selectAll = (): void => {
        selectedIds.value = typeItems.value.map((item) => item.id).filter((id): id is string | number => id !== undefined && id !== null)
        reportTypesStore.selection = selectedIds.value.map((id) => ({ id }))
    }

    const clearSelection = (): void => {
        selectedIds.value = []
        reportTypesStore.selection = []
    }

    watch(
        getReportTypesSelection,
        (selection) => {
            selectedIds.value = selection.map((item) => item.id)
        },
        { deep: true }
    )

    // Import / export

    const importDialog = ref(false)
    const importing = ref(false)
    const exporting = ref(false)
    const importFile = ref<File | File[] | null>(null)
    const importFormRef = ref<{ validate: () => Promise<FormValidationResult>; resetValidation: () => void } | null>(null)

    const notify = (type: 'success' | 'error' | 'info', loc: string, params?: Record<string, unknown>, timeout?: number): void => {
        window.dispatchEvent(
            new CustomEvent('notification', {
                detail: { id: 'report-type-bulk-operation', type, loc, params, timeout }
            })
        )
    }

    const hasFile = (value: File | File[] | null): boolean => Boolean(Array.isArray(value) ? value[0] : value)

    const selectedFile = (): File | null => {
        if (Array.isArray(importFile.value)) return importFile.value[0] ?? null
        return importFile.value
    }

    const openImportDialog = (): void => {
        if (!canImport.value) return
        importDialog.value = true
    }

    const closeImportDialog = (): void => {
        if (importing.value) return
        importDialog.value = false
        importFile.value = null
        importFormRef.value?.resetValidation()
    }

    /**
     * Report what the import actually did.
     *
     * An import silently drops a field whose attribute type exists in neither installation, and
     * silently keeps the existing report type when a title is already taken. Both change what the
     * admin ends up with, so both are reported rather than folded into "success".
     */
    const reportImportResult = (result: ImportResult): void => {
        const created = result.report_types_created ?? 0
        const skipped = result.report_types_skipped ?? []
        const droppedFields = result.fields_skipped ?? []

        if (created > 0) {
            notify('success', 'reports.types.import_success', { count: created })
        }
        if (skipped.length > 0) {
            notify('info', 'reports.types.import_skipped', { count: skipped.length, names: skipped.join(', ') })
        }
        if (droppedFields.length > 0) {
            notify('info', 'reports.types.import_fields_skipped', { count: droppedFields.length, names: droppedFields.join(', ') })
        }
        if (created === 0 && skipped.length === 0) {
            // Nothing in the file could be imported at all - an empty or foreign document.
            notify('info', 'reports.types.import_nothing')
        }
    }

    const importReportTypesDefinitions = async (): Promise<void> => {
        if (!canImport.value || importing.value || !importFormRef.value) return

        const { valid } = await importFormRef.value.validate()
        const file = selectedFile()
        if (!valid || !file) return

        const formData = new FormData()
        formData.append('file', file)

        importing.value = true
        notify('info', 'reports.types.import_progress', undefined, 0)
        try {
            const response = (await importReportTypes(formData)) as { data?: ImportResult }
            reportImportResult(response?.data ?? {})
            closeImportDialog()
            await loadData()
        } catch (error: unknown) {
            // Core names the reason when the file itself is at fault (not JSON, an unknown format
            // version, malformed structure); anything else falls back to the generic message.
            const detail = (error as { response?: { data?: { error?: string } } })?.response?.data?.error
            if (detail) window.dispatchEvent(new CustomEvent('notification', { detail: { type: 'error', message: detail } }))
            else notify('error', 'reports.types.import_error')
        } finally {
            importing.value = false
        }
    }

    const filenameFromResponse = (response: ExportResponse): string => {
        const disposition = response.headers?.['content-disposition']
        const match = disposition?.match(/filename\*?=(?:UTF-8'')?["]?([^";\r\n]+)["]?/i)
        return match?.[1] ? decodeURIComponent(match[1]) : 'exported_report.json'
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

    const exportReportTypesDefinitions = async (): Promise<void> => {
        if (!canExport.value || selectedIds.value.length === 0 || exporting.value) return

        exporting.value = true
        notify('info', 'reports.types.export_progress', undefined, 0)
        try {
            const response = (await exportReportTypes({ selection: selectedIds.value })) as ExportResponse
            triggerDownload(response)
            notify('success', 'reports.types.export_success')
        } catch {
            notify('error', 'reports.types.export_error')
        } finally {
            exporting.value = false
        }
    }

    onMounted(() => {
        loadData()
    })

    onUnmounted(() => {
        multiSelectReportType(false)
    })
</script>
