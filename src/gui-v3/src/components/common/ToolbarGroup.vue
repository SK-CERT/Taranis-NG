<template>
    <div class="toolbar-group">
        <!-- Multi-select toggle button -->
        <ActionButton
            :icon="ICONS.MULTISELECT"
            :color="multiSelectActive ? 'primary' : 'medium-emphasis'"
            :title="t(`${view}.tooltip.toggle_selection`)"
            @click="toggleMultiSelect"
        />

        <!-- Divider -->
        <v-divider
            vertical
            class="mx-2"
        />

        <!-- Select All / Unselect All (display always first!). Always present so the toolbar keeps
             its shape, but inactive until selection mode is on - the same way export and delete
             stay inactive until there is a selection to act on. -->
        <ActionButton
            :icon="allSelected ? ICONS.CHECKBOX_BLANK_OUTLINE : ICONS.SELECT_ALL"
            color="primary"
            :disabled="!multiSelectActive"
            :title="allSelected ? t(`${view}.tooltip.unselect_all`) : t(`${view}.tooltip.select_all`)"
            @click="allSelected ? unselectAll() : selectAll()"
        />

        <!-- Action Buttons (visible always) -->
        <template v-if="view === 'collectors.sources'">
            <!-- Import -->
            <ActionButton
                v-if="canImport"
                icon="mdi-import"
                color="primary"
                :title="t('collectors.sources.import')"
                @click="handleActionEvent(Action.OSINT_IMPORT)"
            />
            <!-- Export -->
            <ActionButton
                v-if="canExport"
                icon="mdi-export"
                color="primary"
                :disabled="selectedCount === 0"
                :title="t('collectors.sources.export_selected_hint')"
                @click="handleActionEvent(Action.OSINT_EXPORT)"
            />
            <!-- Delete selected. Destructive and unbounded in size, so the view confirms first. -->
            <ActionButton
                v-if="canDeleteSources"
                action="delete"
                :disabled="selectedCount === 0"
                :title="t('collectors.sources.delete_selected_hint')"
                @click="handleActionEvent(Action.OSINT_DELETE)"
            />
        </template>

        <!-- Action Buttons (visible only when multi-select is active) -->
        <template v-if="multiSelectActive">
            <template v-if="view === 'assess'">
                <!-- Group -->
                <v-btn
                    v-if="canModify && canGroupActions"
                    icon
                    size="small"
                    :disabled="selectedCount < 2"
                    :title="t('assess.tooltip.group_items')"
                    :data-multi-action="Action.GROUP"
                    @click="handleAction(Action.GROUP)"
                >
                    <v-icon>{{ ICONS.GROUP }}</v-icon>
                </v-btn>

                <!-- Ungroup -->
                <v-btn
                    v-if="canModify && canGroupActions"
                    icon
                    size="small"
                    :disabled="selectedCount === 0 || !canUngroupSelection"
                    :title="t('assess.tooltip.ungroup_items')"
                    :data-multi-action="Action.UNGROUP"
                    @click="handleAction(Action.UNGROUP)"
                >
                    <v-icon>{{ ICONS.UNGROUP }}</v-icon>
                </v-btn>

                <!-- Mark as Read -->
                <v-btn
                    icon
                    size="small"
                    :disabled="selectedCount === 0"
                    :title="t('assess.tooltip.read_items')"
                    :data-multi-action="Action.READ"
                    @click="handleAction(Action.READ)"
                >
                    <v-icon>{{ ICONS.READ }}</v-icon>
                </v-btn>

                <!-- Mark as Important -->
                <v-btn
                    icon
                    size="small"
                    :disabled="selectedCount === 0"
                    :title="t('assess.tooltip.important_items')"
                    :data-multi-action="Action.IMPORTANT"
                    @click="handleAction(Action.IMPORTANT)"
                >
                    <v-icon>{{ ICONS.IMPORTANT }}</v-icon>
                </v-btn>

                <!-- Give a Like -->
                <v-btn
                    icon
                    size="small"
                    :disabled="selectedCount === 0"
                    :title="t('assess.tooltip.like_items')"
                    :data-multi-action="Action.LIKE"
                    @click="handleAction(Action.LIKE)"
                >
                    <v-icon>{{ ICONS.LIKE }}</v-icon>
                </v-btn>

                <!-- Give a Dislike -->
                <v-btn
                    icon
                    size="small"
                    :disabled="selectedCount === 0"
                    :title="t('assess.tooltip.dislike_items')"
                    :data-multi-action="Action.DISLIKE"
                    @click="handleAction(Action.DISLIKE)"
                >
                    <v-icon>{{ ICONS.UNLIKE }}</v-icon>
                </v-btn>

                <!-- Analyze (Create Report) -->
                <v-btn
                    v-if="canCreateReport"
                    icon
                    size="small"
                    :disabled="selectedCount === 0"
                    :title="t('assess.tooltip.analyze_items')"
                    :data-multi-action="Action.CREATE_REPORT"
                    @click="handleAnalyze"
                >
                    <v-icon>{{ ICONS.FILE_CHART_OUTLINE }}</v-icon>
                </v-btn>

                <!-- Delete -->
                <v-btn
                    v-if="canDelete"
                    icon
                    size="small"
                    color="error"
                    :disabled="selectedCount === 0"
                    :title="t('assess.tooltip.delete_items')"
                    :data-multi-action="Action.DELETE"
                    @click="handleAction(Action.DELETE)"
                >
                    <v-icon>{{ ICONS.DELETE }}</v-icon>
                </v-btn>
            </template>

            <template v-else-if="view === 'analyze'">
                <!-- Publish (Create Product) -->
                <v-btn
                    v-if="canCreateProduct"
                    icon
                    size="small"
                    :disabled="selectedCount === 0"
                    :title="t('analyze.tooltip.publish_items')"
                    @click="handlePublish"
                >
                    <v-icon>{{ ICONS.PUBLISH }}</v-icon>
                </v-btn>

                <!-- Delete -->
                <v-btn
                    v-if="canDelete"
                    icon
                    size="small"
                    color="error"
                    :disabled="selectedCount === 0"
                    :title="t('analyze.tooltip.delete_items')"
                    @click="handleDelete"
                >
                    <v-icon>{{ ICONS.DELETE }}</v-icon>
                </v-btn>
            </template>

            <template v-else-if="view === 'publish'">
                <!-- Delete -->
                <v-btn
                    v-if="canDelete"
                    icon
                    size="small"
                    color="error"
                    :disabled="selectedCount === 0"
                    :title="t('publish.tooltip.delete_items')"
                    @click="handleDelete"
                >
                    <v-icon>{{ ICONS.DELETE }}</v-icon>
                </v-btn>
            </template>
        </template>
    </div>
</template>

<script setup lang="ts">
    import { ref, computed, watch } from 'vue'
    import { ICONS } from '@/config/ui-constants'
    import { useRoute, useRouter } from 'vue-router'
    import { useI18n } from 'vue-i18n'
    import ActionButton from '@/components/common/buttons/ActionButton.vue'
    import { useAssessStore } from '@/stores/assess'
    import { useAnalyzeStore } from '@/stores/analyze'
    import { usePublishStore } from '@/stores/publish'
    import { useOSINTSourceStore } from '@/stores/osint_source'
    import { useAuth } from '@/composables/useAuth'
    import { PERMISSIONS } from '@/services/auth/permissions'
    import { groupAction, selectAllNewsItems } from '@/api/assess'
    import { getAllReportItemsUnpaginated, deleteReportItem } from '@/api/analyze'
    import { getAllProductsUnpaginated, deleteProduct } from '@/api/publish'
    import { Action, type ActionKey } from '@/types/actions'
    import { useLocaleFormatters } from '@/composables/useLocaleFormatters'

    type ViewMode = 'assess' | 'analyze' | 'publish' | 'collectors.sources'
    type GenericFilter = Record<string, unknown>
    type SelectionItem = {
        type?: string
        id: string | number
        item: unknown
    }
    type ItemWithId = {
        id: string | number
        [key: string]: unknown
    }
    type NotificationDetail = {
        id?: string
        type?: 'success' | 'error' | 'warning' | 'info'
        message?: string
        persistent?: boolean
        timeout?: number
        loc?: string
        params?: Record<string, unknown>
        pluralCount?: number
    }

    type ApiErrorShape = {
        response?: {
            data?: unknown
        }
    }

    const props = withDefaults(
        defineProps<{
            view: ViewMode
            currentFilter?: GenericFilter | null
        }>(),
        {
            currentFilter: null
        }
    )

    const emit = defineEmits<{
        (e: 'update-data'): void
        (e: 'select-all'): void
        (e: 'clear-selection'): void
        (e: 'osint-import'): void
        (e: 'osint-export'): void
        (e: 'osint-delete'): void
    }>()

    const route = useRoute()
    const router = useRouter()
    const { t } = useI18n()
    const { formatNumber } = useLocaleFormatters()
    const { checkPermission } = useAuth()

    const notify = (detail: NotificationDetail): void => {
        window.dispatchEvent(new CustomEvent('notification', { detail }))
    }

    // Get the appropriate store based on view
    const assessStore = useAssessStore()
    const analyzeStore = useAnalyzeStore()
    const publishStore = usePublishStore()
    const osintSourceStore = useOSINTSourceStore()

    const allSelected = ref<boolean>(false)

    // Computed properties based on view
    const multiSelectActive = computed(() => {
        switch (props.view) {
            case 'assess':
                return assessStore.getMultiSelect
            case 'analyze':
                return analyzeStore.getMultiSelectReport
            case 'publish':
                return publishStore.getMultiSelect
            case 'collectors.sources':
                return osintSourceStore.getOSINTSourcesMultiSelect
            default:
                return false
        }
    })

    const selectedCount = computed(() => {
        switch (props.view) {
            case 'assess':
                return assessStore.getSelection.length
            case 'analyze':
                return analyzeStore.getSelectionReport.length
            case 'publish':
                return publishStore.getSelection.length
            case 'collectors.sources':
                return osintSourceStore.getOSINTSourcesSelection.length
            default:
                return 0
        }
    })

    // The selection is also emptied from outside this toolbar - switching group tabs, leaving the
    // view. Left alone, the button would keep offering "unselect all" over an empty selection.
    watch(selectedCount, (count) => {
        if (count === 0) {
            allSelected.value = false
        }
    })

    // Permission checks
    const canModify = computed(() => {
        if (props.view === 'assess') return checkPermission(PERMISSIONS.ASSESS_UPDATE)
        return false
    })

    const canDelete = computed(() => {
        if (props.view === 'assess') return checkPermission(PERMISSIONS.ASSESS_DELETE)
        if (props.view === 'analyze') return checkPermission(PERMISSIONS.ANALYZE_DELETE)
        if (props.view === 'publish') return checkPermission(PERMISSIONS.PUBLISH_DELETE)
        return false
    })

    const canCreateReport = computed(() => {
        if (props.view === 'assess') return checkPermission(PERMISSIONS.ANALYZE_CREATE)
        return false
    })

    const canCreateProduct = computed(() => {
        if (props.view === 'analyze') return checkPermission(PERMISSIONS.PUBLISH_CREATE)
        return false
    })

    const canImport = computed(() => checkPermission('CONFIG_OSINT_SOURCE_CREATE'))
    const canExport = computed(() => checkPermission('CONFIG_OSINT_SOURCE_ACCESS'))
    const canDeleteSources = computed(() => checkPermission('CONFIG_OSINT_SOURCE_DELETE'))

    const normalizeSelectionType = (rawType: unknown): 'AGGREGATE' | 'ITEM' => {
        // console.log('[ToolbarGroup] Normalizing selection type:', rawType)
        const typeValue = String(rawType || '').toUpperCase()
        if (typeValue.includes('AGGREGATE')) {
            return 'AGGREGATE'
        }
        return 'ITEM'
    }

    const canUngroupSelection = computed(() => {
        if (props.view !== 'assess') {
            return false
        }

        const selection = assessStore.getSelection as SelectionItem[]

        return selection.some((selectedItem) => {
            const normalizedType = normalizeSelectionType(selectedItem.type)

            // Single item selections can be ungrouped from their parent aggregate.
            if (normalizedType === 'ITEM') {
                return true
            }

            // Aggregate can only be ungrouped when it actually contains multiple news items.
            const aggregate = selectedItem.item as { news_items?: unknown[] } | undefined
            return Array.isArray(aggregate?.news_items) && aggregate.news_items.length > 1
        })
    })

    // Disable group actions when the current group is exactly "all"
    const canGroupActions = computed(() => {
        if (props.view === 'assess') {
            const groupId = route.params['groupId'] || 'all'
            return groupId !== 'all'
        }
        return false
    })

    // Toggle multi-select
    const setMultiSelect = (newState: boolean): void => {
        switch (props.view) {
            case 'assess':
                assessStore.multiSelect(newState)
                break
            case 'analyze':
                analyzeStore.multiSelectReport(newState)
                break
            case 'publish':
                publishStore.multiSelect(newState)
                break
            case 'collectors.sources':
                osintSourceStore.multiSelectOSINTSource(newState)
                break
            default:
                break
        }

        // Clear allSelected flag when turning off multi-select
        if (!newState) {
            allSelected.value = false
            if (props.view === 'collectors.sources') {
                emit('clear-selection')
            }
        }

        window.dispatchEvent(new CustomEvent('multiselect-toggled'))
    }

    const toggleMultiSelect = (): void => setMultiSelect(!multiSelectActive.value)

    // Select all
    const selectAll = async (): Promise<void> => {
        switch (props.view) {
            case 'assess':
                await selectAllAssess()
                break
            case 'analyze':
                await selectAllAnalyze()
                break
            case 'publish':
                await selectAllPublish()
                break
            case 'collectors.sources':
                emit('select-all')
                allSelected.value = true
                break
            default:
                break
        }
    }

    const selectAllAssess = async (): Promise<void> => {
        const group_id = String(route.params['groupId'] || 'all')

        // Use current filter from parent component if available, otherwise use store filter
        const storeFilter = assessStore.getFilter
        const filterSearchRaw = Reflect.get(storeFilter as object, 'search')
        const filterRangeRaw = Reflect.get(storeFilter as object, 'range')
        const filterReadRaw = Reflect.get(storeFilter as object, 'read')
        const filterImportantRaw = Reflect.get(storeFilter as object, 'important')
        const filterRelevantRaw = Reflect.get(storeFilter as object, 'relevant')
        const filterSortRaw = Reflect.get(storeFilter as object, 'sort')

        const filterSearch = typeof filterSearchRaw === 'string' ? filterSearchRaw : ''
        const filterRange = typeof filterRangeRaw === 'string' ? filterRangeRaw : 'ALL'
        const filterRead = filterReadRaw !== undefined ? filterReadRaw : 'ALL'
        const filterImportant = typeof filterImportantRaw === 'string' ? filterImportantRaw : 'ALL'
        const filterRelevant = typeof filterRelevantRaw === 'string' ? filterRelevantRaw : 'ALL'
        const filterSort = typeof filterSortRaw === 'string' ? filterSortRaw : 'DATE_DESC'
        const filter = props.currentFilter || {
            search: filterSearch,
            range: filterRange,
            read: filterRead,
            important: filterImportant,
            relevant: filterRelevant,
            sort: filterSort
        }

        // console.log('[ToolbarGroup] Select all assess - group_id:', group_id, 'filter:', filter)

        // Show loading notification
        notify({
            id: 'select-all-progress',
            type: 'info',
            loc: 'common.fetching_items',
            persistent: true,
            timeout: 0
        })

        try {
            const response = await selectAllNewsItems({
                group_id,
                filter
            })
            // console.log('[ToolbarGroup] Select all response:', response)

            if (response?.data?.items) {
                // console.log('[ToolbarGroup] Selecting', response.data.items.length, 'items')
                // "Select all" means exactly the items this request returned, so it replaces the
                // selection instead of adding to it - anything selected before (in this group or
                // a previous one) must not be carried into the following group action.
                assessStore.clearSelection()
                response.data.items.forEach((item: unknown) => {
                    const typedItem = item as ItemWithId
                    assessStore.select({
                        type: 'AGGREGATE',
                        id: typedItem.id,
                        item: typedItem
                    })
                })
                allSelected.value = true
                notify({
                    id: 'select-all-progress',
                    type: 'success',
                    loc: 'assess.select_all_success',
                    params: { count: formatNumber(response.data.items.length) },
                    pluralCount: response.data.items.length,
                    timeout: 2000
                })
                window.dispatchEvent(new CustomEvent('sync-assess-selection'))
            } else {
                console.warn('[ToolbarGroup] No items in response:', response)
                notify({ type: 'warning', loc: 'common.no_items_to_select' })
            }
        } catch (error: unknown) {
            console.error('[ToolbarGroup] Error selecting all:', error)
            notify({ type: 'error', loc: 'error.select_all_failed' })
        }
    }

    const selectAllAnalyze = async (): Promise<void> => {
        const group = analyzeStore.getCurrentReportItemGroup
        // Use current filter from parent component if available, otherwise use defaults
        const filter = props.currentFilter || {
            search: '',
            range: 'ALL',
            completed: 'ALL',
            sort: 'DATE_DESC'
        }

        // console.log('[ToolbarGroup] Select all analyze - group:', group, 'filter:', filter)

        // Show loading notification
        notify({
            id: 'select-all-progress',
            type: 'info',
            loc: 'common.fetching_items',
            persistent: true,
            timeout: 0
        })

        try {
            const response = await getAllReportItemsUnpaginated({
                group,
                filter
            })

            // console.log('[ToolbarGroup] Select all analyze response:', response, 'Items in response:', response?.data?.items?.length)

            if (response?.data?.items) {
                // console.log('[ToolbarGroup] Selecting', response.data.items.length, 'analyze items')
                analyzeStore.selection_report = []
                response.data.items.forEach((item: unknown) => {
                    const typedItem = item as ItemWithId
                    analyzeStore.selectReport({
                        id: typedItem.id,
                        item: typedItem
                    })
                })
                allSelected.value = true
                notify({
                    id: 'select-all-progress',
                    type: 'success',
                    loc: 'analyze.select_all_success',
                    params: { count: formatNumber(response.data.items.length) },
                    pluralCount: response.data.items.length,
                    timeout: 2000
                })
                window.dispatchEvent(new CustomEvent('sync-analyze-selection'))
            } else {
                console.warn('[ToolbarGroup] No items in analyze response:', response)
            }
        } catch (error: unknown) {
            console.error('[ToolbarGroup] Error selecting all analyze items:', error)
            notify({ type: 'error', loc: 'error.select_all_failed' })
        }
    }

    const selectAllPublish = async (): Promise<void> => {
        // Use current filter from parent component if available, otherwise use defaults
        const filter = props.currentFilter || {
            search: '',
            range: 'ALL',
            published: 'ALL',
            sort: 'DATE_DESC'
        }

        // console.log('[ToolbarGroup] Select all publish - filter:', filter)

        // Show loading notification
        notify({
            id: 'select-all-progress',
            type: 'info',
            loc: 'common.fetching_items',
            persistent: true,
            timeout: 0
        })

        try {
            const response = await getAllProductsUnpaginated({ filter })
            // console.log('[ToolbarGroup] Select all publish response:', response, 'Items in response:', response?.data?.items?.length)

            if (response?.data?.items) {
                // console.log('[ToolbarGroup] Selecting', response.data.items.length, 'publish items')
                publishStore.selection = []
                response.data.items.forEach((item: unknown) => {
                    const typedItem = item as ItemWithId
                    publishStore.select({
                        id: typedItem.id,
                        item: typedItem
                    })
                })
                allSelected.value = true
                notify({
                    id: 'select-all-progress',
                    type: 'success',
                    loc: 'publish.select_all_success',
                    params: { count: formatNumber(response.data.items.length) },
                    pluralCount: response.data.items.length,
                    timeout: 2000
                })
                window.dispatchEvent(new CustomEvent('sync-publish-selection'))
            } else {
                console.warn('[ToolbarGroup] No items in publish response:', response)
            }
        } catch (error: unknown) {
            console.error('[ToolbarGroup] Error selecting all publish items:', error)
            notify({ type: 'error', loc: 'error.select_all_failed' })
        }
    }

    // Unselect all
    const unselectAll = (): void => {
        allSelected.value = false
        switch (props.view) {
            case 'assess':
                assessStore.selection = []
                window.dispatchEvent(new CustomEvent('sync-assess-selection'))
                break
            case 'analyze':
                analyzeStore.selection_report = []
                window.dispatchEvent(new CustomEvent('sync-analyze-selection'))
                break
            case 'publish':
                publishStore.selection = []
                window.dispatchEvent(new CustomEvent('sync-publish-selection'))
                break
            case 'collectors.sources':
                emit('clear-selection')
                break
            default:
                break
        }
    }

    // Assess-specific actions
    const handleAnalyze = (): void => {
        const selection = assessStore.getSelection as SelectionItem[]
        const items = selection.filter((s) => s.type === 'AGGREGATE' || s.type === 'news_item_aggregate').map((s) => s.item)

        if (items.length > 0) {
            assessStore.multiSelect(false)
            window.dispatchEvent(new CustomEvent('multiselect-toggled'))
            window.dispatchEvent(new CustomEvent('new-report', { detail: items }))
        }
    }

    const handleAction = async (type: ActionKey): Promise<void> => {
        const selection = assessStore.getSelection as SelectionItem[]

        const getErrorKey = (error: unknown): string => {
            const responseData = (error as ApiErrorShape | undefined)?.response?.data

            if (responseData && typeof responseData === 'object' && 'error' in responseData) {
                const errorValue = (responseData as { error?: unknown }).error
                if (typeof errorValue === 'string' && errorValue.trim().length > 0) {
                    return errorValue
                }
            }

            if (typeof responseData === 'string') {
                const normalized = responseData.trim()
                if (normalized.toLowerCase().includes('<html')) {
                    return 'server_error'
                }
                if (normalized.length > 0) {
                    return normalized
                }
            }

            return 'server_error'
        }

        const items = selection.map((s) => ({ type: normalizeSelectionType(s.type), id: s.id }))

        if (type === Action.GROUP && items.length < 2) {
            notify({ type: 'warning', loc: 'common.select_at_least_two_to_group' })
            return
        }

        if (type === Action.UNGROUP && !canUngroupSelection.value) {
            notify({ type: 'warning', loc: 'common.no_grouped_items_selected' })
            return
        }

        if (items.length > 0) {
            const group_id = (route.params['groupId'] as string | undefined) || null

            // Show progress notification
            notify({
                id: 'assess-action-progress',
                type: 'info',
                loc: 'common.processing_items',
                params: { count: formatNumber(items.length) },
                pluralCount: items.length,
                persistent: true,
                timeout: 0
            })

            try {
                await groupAction({ group: group_id, action: type, items })

                toggleMultiSelect()

                notify({
                    id: 'assess-action-progress',
                    type: 'success',
                    loc: 'common.action_completed',
                    timeout: 2000
                })

                emit('update-data')
            } catch (error: unknown) {
                console.error('Error performing action:', error)
                notify({ type: 'error', loc: `error.${getErrorKey(error)}` })
            }
        }
    }

    const handleActionEvent = async (type: ActionKey): Promise<void> => {
        console.log(type)
        switch (type) {
            case Action.OSINT_IMPORT:
                emit('osint-import')
                break
            case Action.OSINT_EXPORT:
                emit('osint-export')
                break
            case Action.OSINT_DELETE:
                emit('osint-delete')
                break
            default:
                console.warn('[ToolbarGroup] Unhandled action event type:', type)
                break
        }
    }

    // Analyze-specific actions
    const handlePublish = (): void => {
        const selection = analyzeStore.getSelectionReport as SelectionItem[]
        const items = selection.map((s) => s.item)

        if (items.length > 0) {
            publishStore.pendingNewProduct = items
            analyzeStore.multiSelectReport(false)
            window.dispatchEvent(new CustomEvent('multiselect-toggled'))
            router.push('/publish')
        }
    }

    // Delete action (used by analyze and publish)
    const handleDelete = async (): Promise<void> => {
        if (props.view === 'analyze') {
            const selection = analyzeStore.getSelectionReport as SelectionItem[]

            if (selection.length > 0) {
                // Show progress notification
                notify({
                    id: 'analyze-delete-progress',
                    type: 'info',
                    loc: 'common.deleting_items',
                    params: { count: formatNumber(selection.length) },
                    pluralCount: selection.length,
                    persistent: true,
                    timeout: 0
                })

                try {
                    const deletePromises = selection.map((s: SelectionItem) => deleteReportItem({ id: s.id }))

                    await Promise.all(deletePromises)

                    toggleMultiSelect()

                    notify({
                        id: 'analyze-delete-progress',
                        type: 'success',
                        loc: 'common.deleted_successfully',
                        timeout: 2000
                    })

                    emit('update-data')
                } catch (error: unknown) {
                    console.error('Error deleting items:', error)
                    const responseData = (error as { response?: { data?: string } } | undefined)?.response?.data
                    notify({ type: 'error', loc: `error.${responseData || 'server_error'}` })
                }
            }
        } else if (props.view === 'publish') {
            const selection = publishStore.getSelection as SelectionItem[]

            if (selection.length > 0) {
                // Show progress notification
                notify({
                    id: 'publish-delete-progress',
                    type: 'info',
                    loc: 'common.deleting_items',
                    params: { count: formatNumber(selection.length) },
                    pluralCount: selection.length,
                    persistent: true,
                    timeout: 0
                })

                try {
                    const deletePromises = selection.map((s: SelectionItem) => deleteProduct(s.item))

                    await Promise.all(deletePromises)

                    toggleMultiSelect()

                    notify({
                        id: 'publish-delete-progress',
                        type: 'success',
                        loc: 'common.deleted_successfully',
                        timeout: 2000
                    })

                    emit('update-data')
                } catch (error: unknown) {
                    console.error('Error deleting items:', error)
                    const responseData = (error as { response?: { data?: string } } | undefined)?.response?.data
                    notify({ type: 'error', loc: `error.${responseData || 'server_error'}` })
                }
            }
        }
    }

    defineExpose({
        disableMultiSelect: () => {
            if (multiSelectActive.value) {
                toggleMultiSelect()
            }
        }
    })
</script>

<style scoped>
    .toolbar-group {
        display: flex;
        align-items: center;
        gap: 4px;
        padding: 4px 8px;
    }
</style>
