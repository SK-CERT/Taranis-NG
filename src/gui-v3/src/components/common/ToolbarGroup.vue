<template>
    <div class="toolbar-group">
        <!-- Multi-select toggle button -->
        <v-btn
            icon
            size="small"
            :color="multiSelectActive ? 'primary' : 'default'"
            :title="t(`${view}.tooltip.toggle_selection`)"
            @click="toggleMultiSelect"
        >
            <v-icon>{{ ICONS.MULTISELECT }}</v-icon>
        </v-btn>

        <!-- Divider -->
        <v-divider vertical class="mx-2" />

        <!-- Action Buttons (only visible when multi-select is active) -->
        <template v-if="multiSelectActive">
            <!-- Select All / Unselect All -->
            <v-btn
                icon
                size="small"
                :disabled="false"
                :title="allSelected ? t(`${view}.tooltip.unselect_all`) : t(`${view}.tooltip.select_all`)"
                @click="allSelected ? unselectAll() : selectAll()"
            >
                <v-icon>{{ allSelected ? ICONS.CHECKBOX_BLANK_OUTLINE : ICONS.SELECT_ALL }}</v-icon>
            </v-btn>

            <!-- View-specific action buttons -->
            <template v-if="view === 'assess'">
                <!-- Group -->
                <v-btn
                    v-if="canModify && canGroupActions"
                    icon
                    size="small"
                    :disabled="selectedCount < 2"
                    :title="t('assess.tooltip.group_items')"
                    @click="handleAction('GROUP')"
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
                    @click="handleAction('UNGROUP')"
                >
                    <v-icon>{{ ICONS.UNGROUP }}</v-icon>
                </v-btn>

                <!-- Mark as Read -->
                <v-btn
                    icon
                    size="small"
                    :disabled="selectedCount === 0"
                    :title="t('assess.tooltip.read_items')"
                    @click="handleAction('READ')"
                >
                    <v-icon>{{ ICONS.READ }}</v-icon>
                </v-btn>

                <!-- Mark as Important -->
                <v-btn
                    icon
                    size="small"
                    :disabled="selectedCount === 0"
                    :title="t('assess.tooltip.important_items')"
                    @click="handleAction('IMPORTANT')"
                >
                    <v-icon>{{ ICONS.IMPORTANT }}</v-icon>
                </v-btn>

                <!-- Give a Like -->
                <v-btn
                    icon
                    size="small"
                    :disabled="selectedCount === 0"
                    :title="t('assess.tooltip.like_items')"
                    @click="handleAction('LIKE')"
                >
                    <v-icon>{{ ICONS.LIKE }}</v-icon>
                </v-btn>

                <!-- Give a Dislike -->
                <v-btn
                    icon
                    size="small"
                    :disabled="selectedCount === 0"
                    :title="t('assess.tooltip.dislike_items')"
                    @click="handleAction('DISLIKE')"
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
                    @click="handleAction('DELETE')"
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
    import { ref, computed } from 'vue'
    import { ICONS } from '@/config/ui-constants'
    import { useRoute, useRouter } from 'vue-router'
    import { useI18n } from 'vue-i18n'
    import { useAssessStore } from '@/stores/assess'
    import { useAnalyzeStore } from '@/stores/analyze'
    import { usePublishStore } from '@/stores/publish'
    import { useAuth } from '@/composables/useAuth'
    import { PERMISSIONS } from '@/services/auth/permissions'
    import { groupAction, selectAllNewsItems } from '@/api/assess'
    import { getAllReportItemsUnpaginated, deleteReportItem } from '@/api/analyze'
    import { getAllProductsUnpaginated, deleteProduct } from '@/api/publish'

    type ViewMode = 'assess' | 'analyze' | 'publish'
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
    }>()

    const route = useRoute()
    const router = useRouter()
    const { t } = useI18n()
    const { checkPermission } = useAuth()

    const notify = (detail: NotificationDetail): void => {
        window.dispatchEvent(new CustomEvent('notification', { detail }))
    }

    // Get the appropriate store based on view
    const assessStore = useAssessStore()
    const analyzeStore = useAnalyzeStore()
    const publishStore = usePublishStore()

    const allSelected = ref<boolean>(false)

    // Computed properties based on view
    const multiSelectActive = computed(() => {
        if (props.view === 'assess') return assessStore.getMultiSelect
        if (props.view === 'analyze') return analyzeStore.getMultiSelectReport
        return publishStore.getMultiSelect
    })

    const selectedCount = computed(() => {
        if (props.view === 'assess') return assessStore.getSelection.length
        if (props.view === 'analyze') return analyzeStore.getSelectionReport.length
        return publishStore.getSelection.length
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

    const normalizeSelectionType = (rawType: unknown): 'AGGREGATE' | 'ITEM' => {
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
    const toggleMultiSelect = (): void => {
        const newState = !multiSelectActive.value

        if (props.view === 'assess') {
            assessStore.multiSelect(newState)
        } else if (props.view === 'analyze') {
            analyzeStore.multiSelectReport(newState)
        } else {
            publishStore.multiSelect(newState)
        }

        // Clear allSelected flag when turning off multi-select
        if (!newState) {
            allSelected.value = false
        }

        window.dispatchEvent(new CustomEvent('multiselect-toggled'))
    }

    // Select all
    const selectAll = async (): Promise<void> => {
        if (props.view === 'assess') {
            await selectAllAssess()
        } else if (props.view === 'analyze') {
            await selectAllAnalyze()
        } else {
            await selectAllPublish()
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

        console.log('[ToolbarGroup] Select all assess - group_id:', group_id, 'filter:', filter)

        // Show loading notification
        notify({
            id: 'select-all-progress',
            type: 'info',
            message: 'Fetching all items...',
            persistent: true,
            timeout: 0
        })

        try {
            const response = await selectAllNewsItems({
                group_id,
                filter
            })

            console.log('[ToolbarGroup] Select all response:', response)

            if (response?.data?.items) {
                console.log('[ToolbarGroup] Selecting', response.data.items.length, 'items')
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
                    params: { count: response.data.items.length },
                    timeout: 2000
                })
                window.dispatchEvent(new CustomEvent('sync-assess-selection'))
            } else {
                console.warn('[ToolbarGroup] No items in response:', response)
                notify({ type: 'warning', message: 'No items to select' })
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

        console.log('[ToolbarGroup] Select all analyze - group:', group, 'filter:', filter)

        // Show loading notification
        notify({
            id: 'select-all-progress',
            type: 'info',
            message: 'Fetching all items...',
            persistent: true,
            timeout: 0
        })

        try {
            const response = await getAllReportItemsUnpaginated({
                group,
                filter
            })

            console.log('[ToolbarGroup] Select all analyze response:', response)
            console.log('[ToolbarGroup] Items in response:', response?.data?.items?.length)

            if (response?.data?.items) {
                console.log('[ToolbarGroup] Selecting', response.data.items.length, 'analyze items')
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
                    params: { count: response.data.items.length },
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

        console.log('[ToolbarGroup] Select all publish - filter:', filter)

        // Show loading notification
        notify({
            id: 'select-all-progress',
            type: 'info',
            message: 'Fetching all items...',
            persistent: true,
            timeout: 0
        })

        try {
            const response = await getAllProductsUnpaginated({ filter })

            console.log('[ToolbarGroup] Select all publish response:', response)
            console.log('[ToolbarGroup] Items in response:', response?.data?.items?.length)

            if (response?.data?.items) {
                console.log('[ToolbarGroup] Selecting', response.data.items.length, 'publish items')
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
                    params: { count: response.data.items.length },
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

        if (props.view === 'assess') {
            assessStore.selection = []
            window.dispatchEvent(new CustomEvent('sync-assess-selection'))
        } else if (props.view === 'analyze') {
            analyzeStore.selection_report = []
            window.dispatchEvent(new CustomEvent('sync-analyze-selection'))
        } else {
            publishStore.selection = []
            window.dispatchEvent(new CustomEvent('sync-publish-selection'))
        }
    }

    // Assess-specific actions
    const handleAnalyze = (): void => {
        const selection = assessStore.getSelection as SelectionItem[]
        const items = selection.filter((s) => s.type === 'news_item_aggregate').map((s) => s.item)

        if (items.length > 0) {
            assessStore.multiSelect(false)
            window.dispatchEvent(new CustomEvent('multiselect-toggled'))
            window.dispatchEvent(new CustomEvent('new-report', { detail: items }))
        }
    }

    const handleAction = async (type: string): Promise<void> => {
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

        if (type === 'GROUP' && items.length < 2) {
            notify({ type: 'warning', message: 'Select at least two items to group.' })
            return
        }

        if (type === 'UNGROUP' && !canUngroupSelection.value) {
            notify({ type: 'warning', message: 'No grouped items selected.' })
            return
        }

        if (items.length > 0) {
            const group_id = (route.params['groupId'] as string | undefined) || null

            // Show progress notification
            notify({
                id: 'assess-action-progress',
                type: 'info',
                message: `Processing ${items.length} item(s)...`,
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
                    message: `Deleting ${selection.length} item(s)...`,
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
                    message: `Deleting ${selection.length} item(s)...`,
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
