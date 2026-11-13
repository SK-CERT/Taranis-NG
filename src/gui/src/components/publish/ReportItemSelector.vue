<template>
    <v-container
        fluid
        class="pa-0"
    >
        <!-- Dialog Container -->
        <v-dialog
            v-model="selectorOpen"
            fullscreen
            persistent
            @keydown.esc.stop="handleClose"
        >
            <v-card
                flat
                class="d-flex flex-column"
                style="height: 100vh"
            >
                <!-- Fixed header (toolbar + filter stay put while the list below scrolls) -->
                <div class="flex-grow-0 flex-shrink-0">
                    <v-toolbar
                        color="primary"
                        dark
                    >
                        <v-btn
                            icon
                            @click="handleClose"
                        >
                            <v-icon>{{ ICONS.CLOSE }}</v-icon>
                        </v-btn>
                        <v-toolbar-title>{{ t('report_item.select') }}</v-toolbar-title>
                        <v-spacer />
                        <v-btn @click="handleAdd">
                            <v-icon start>
                                {{ ICONS.PLUS_BOX }}
                            </v-icon>
                            {{ t('common.add_items') }}
                        </v-btn>
                    </v-toolbar>

                    <div class="selector-filter-panel">
                        <ToolbarFilterAnalyze
                            ref="toolbarFilter"
                            :show-group-toolbar="false"
                            @update-filter="updateFilter"
                        />
                    </div>
                </div>

                <!-- Main Content (scrollable area) -->
                <div class="selector-results flex-grow-1 overflow-y-auto">
                    <ContentDataAnalyze
                        ref="contentData"
                        :show-remove-action="false"
                        :disable-actions="true"
                        :selection="value"
                        card-item="CardAnalyze"
                        @show-report-item-detail="showReportItemDetail"
                        @new-data-loaded="handleNewDataLoaded"
                        @update-showing-count="handleUpdateShowingCount"
                    />
                </div>
            </v-card>
        </v-dialog>

        <!-- New Report Item Dialog -->
        <NewReportItem
            ref="reportItemDialog"
            :show-button="false"
            :read-only="readOnlySelector"
        />

        <!-- Confirm adding non-final reports to a final/published product -->
        <v-dialog
            v-model="showCompletionConfirm"
            max-width="500px"
            persistent
        >
            <v-card>
                <v-card-title class="text-h5">
                    {{ t('product.add_incomplete_reports.title') }}
                </v-card-title>
                <v-card-text>
                    <p class="mb-2">{{ confirmMessage }}</p>
                    <v-list
                        v-if="incompleteReportTitles.length > 0"
                        density="compact"
                        class="mb-2"
                        style="max-height: 200px; overflow-y: auto"
                    >
                        <v-list-item
                            v-for="(title, index) in incompleteReportTitles"
                            :key="index"
                            class="px-0"
                        >
                            <template #prepend>
                                <v-icon
                                    color="orange"
                                    size="small"
                                >
                                    {{ ICONS.FILE_DOCUMENT }}
                                </v-icon>
                            </template>
                            <v-list-item-title class="text-body-2">
                                <bdi dir="auto">{{ title }}</bdi>
                            </v-list-item-title>
                        </v-list-item>
                    </v-list>
                </v-card-text>
                <v-card-actions>
                    <v-spacer />
                    <v-btn @click="cancelAddReports">
                        {{ t('common.cancel') }}
                    </v-btn>
                    <v-btn
                        color="primary"
                        variant="elevated"
                        @click="confirmAddReports"
                    >
                        {{ confirmButton }}
                    </v-btn>
                </v-card-actions>
            </v-card>
        </v-dialog>

        <!-- Selected Items Display: in the product's order, which the controls change -->
        <div
            v-if="!selectorOpen"
            class="pt-2"
        >
            <div
                v-for="(item, index) in displayItems"
                :key="item.id"
                class="report-order__row"
                :class="{ 'drag-over': dragOverIndex === index, 'dragging': dragIndex === index }"
                data-test="report-order-row"
                @dragover="onDragOver(index, $event)"
                @drop="onDrop(index)"
                @dragleave="onDragLeave(index)"
            >
                <div
                    v-if="canReorder"
                    class="report-order__controls"
                >
                    <v-icon
                        class="drag-handle"
                        size="small"
                        draggable="true"
                        :title="t('report_item.tooltip.drag_to_reorder')"
                        :icon="ICONS.DRAG_HANDLE"
                        data-test="report-drag-handle"
                        @dragstart="onDragStart(index, $event)"
                        @dragend="onDragEnd"
                    />
                    <div class="d-flex flex-column ms-1">
                        <v-btn
                            variant="text"
                            density="compact"
                            size="x-small"
                            :icon="ICONS.ARROW_UP"
                            :disabled="index === 0"
                            :title="t('report_item.tooltip.move_up')"
                            :aria-label="t('report_item.tooltip.move_up')"
                            data-test="report-move-up"
                            @click="moveReportItem(index, index - 1)"
                        />
                        <v-btn
                            variant="text"
                            density="compact"
                            size="x-small"
                            :icon="ICONS.ARROW_DOWN"
                            :disabled="index === displayItems.length - 1"
                            :title="t('report_item.tooltip.move_down')"
                            :aria-label="t('report_item.tooltip.move_down')"
                            data-test="report-move-down"
                            @click="moveReportItem(index, index + 1)"
                        />
                    </div>
                </div>
                <div class="report-order__card">
                    <CardAnalyze
                        :card="item"
                        :show-remove-action="true"
                        @show-detail="showReportItemDetail"
                        @remove-report-item-from-selector="removeReportItem"
                    />
                </div>
            </div>
        </div>
    </v-container>
</template>

<script setup lang="ts">
    import { ref, computed, watch, onMounted, nextTick } from 'vue'
    import { useI18n } from 'vue-i18n'
    import { ICONS } from '@/config/ui-constants'
    import ContentDataAnalyze from '@/components/analyze/ContentDataAnalyze.vue'
    import ToolbarFilterAnalyze from '@/components/analyze/ToolbarFilterAnalyze.vue'
    import CardAnalyze from '@/components/analyze/CardAnalyze.vue'
    import NewReportItem from '@/components/analyze/NewReportItem.vue'
    import { useAnalyzeStore } from '@/stores/analyze'
    import { useSettingsStore } from '@/stores/settings'
    import { Settings } from '@/types/settings'
    import { getEntityTypeStates } from '@/api/state'
    import { useContentLanguages } from '@/composables/useContentLanguages'

    type ReportItem = {
        id: number | string
        title?: string
        tag?: string
        report_item_type_id?: number | string
        report_type_name?: string
        state?: {
            name?: string
            display_name?: string
            color?: string
            icon?: string
            description?: string
        } | null
        [key: string]: any
    }

    const { t } = useI18n()
    const { titleOf } = useContentLanguages()
    const analyzeStore = useAnalyzeStore()
    const settingsStore = useSettingsStore()

    const props = withDefaults(
        defineProps<{
            values?: ReportItem[]
            modify?: boolean
            edit?: boolean
            productStateIsFinal?: boolean
        }>(),
        {
            values: () => [],
            modify: false,
            edit: false,
            productStateIsFinal: false
        }
    )

    const emit = defineEmits<{
        (e: 'items-changed', payload: ReportItem[]): void
    }>()

    const selectorOpen = ref<boolean>(false)
    const value = ref<ReportItem[]>(props.values || [])
    const toolbarFilter = ref<any>(null)
    const contentData = ref<any>(null)
    const reportItemDialog = ref<any>(null)
    // Display names of report-item states marked as FINAL (state_type === 'final').
    // Loaded once from /state/entity-types/report_item/states so we can detect
    // non-final reports when adding them to an already-published product.
    const finalReportStateNames = ref<Set<string>>(new Set())
    // Pending selection awaiting confirmation when adding non-final reports to a final product.
    const pendingSelection = ref<ReportItem[] | null>(null)
    const showCompletionConfirm = ref<boolean>(false)

    watch(
        () => props.values,
        (newValues: ReportItem[]) => {
            value.value = Array.isArray(newValues) ? [...newValues] : []
        },
        { deep: true, immediate: true }
    )

    // The selected report items only carry report_item_type_id; resolve the type
    // name from the loaded report item types so the cards show the type like the
    // Analyze list does.
    const displayItems = computed<ReportItem[]>(() => {
        const types = Array.isArray(analyzeStore.getReportItemTypes.items)
            ? (analyzeStore.getReportItemTypes.items as Array<{ id: number | string; title?: string }>)
            : []
        return value.value.map((item) => {
            if (item.report_type_name) return item
            const reportType = types.find((x) => x.id == item.report_item_type_id)
            return { ...item, report_type_name: reportType?.title || t('workflow.entity_types.report_item') }
        })
    })

    const isReportFinal = (item: ReportItem): boolean => {
        const displayName = item.state?.display_name
        if (!displayName) return false
        return finalReportStateNames.value.has(displayName)
    }

    // REPORT_SELECTOR_READ_ONLY decides whether a report item opened from the selector is
    // just viewable or editable. Read-only is the safer default if the setting is missing.
    const readOnlySelector = computed(() => settingsStore.getSettingBoolean(Settings.REPORT_SELECTOR_READ_ONLY, true))

    // Whether the backend "Automatic cascade state changes" (CASCADE_STATES_ENABLED)
    // app setting is on. The completion-confirmation dialog only makes sense when
    // the backend would actually auto-complete newly-added non-final reports.
    const cascadeStatesEnabled = computed(() => settingsStore.getSettingBoolean(Settings.CASCADE_STATES_ENABLED, true))

    const loadReportItemStates = async (): Promise<void> => {
        try {
            const response = await getEntityTypeStates('report_item')
            const states = Array.isArray(response?.data?.states) ? response.data.states : []
            finalReportStateNames.value = new Set(
                states
                    .filter((s: { state_type?: string; display_name?: string }) => s.state_type === 'final')
                    .map((s: { display_name?: string }) => s.display_name)
                    .filter((name?: string): name is string => Boolean(name))
            )
        } catch (error: unknown) {
            console.error('Failed to load report item states:', error)
        }
    }

    onMounted(async () => {
        if (!analyzeStore.getReportItemTypes.items?.length) {
            await analyzeStore.loadReportItemTypes({})
        }
        if (finalReportStateNames.value.size === 0) {
            await loadReportItemStates()
        }
    })

    const openSelector = async (): Promise<void> => {
        // Disable multi-select from previous selections
        window.dispatchEvent(new CustomEvent('multi-select-off'))
        analyzeStore.multiSelectReport(true)
        selectorOpen.value = true

        // Seed existing items into selection state so checkboxes/counters are correct on open.
        await nextTick()
        for (const item of value.value) {
            if (item?.id) {
                analyzeStore.selectReport({ id: item.id, item })
            }
        }
    }

    const collectNewItems = (): ReportItem[] => {
        const rawSelection = analyzeStore.getSelectionReport
        const selection: Array<{ item: ReportItem }> = Array.isArray(rawSelection)
            ? rawSelection
                  .map((entry): { item: ReportItem } | null => {
                      if (!entry || typeof entry !== 'object') return null
                      const candidate = (entry as { item?: unknown }).item
                      if (!candidate || typeof candidate !== 'object') return null
                      const id = (candidate as { id?: unknown }).id
                      if (typeof id !== 'string' && typeof id !== 'number') return null
                      return { item: candidate as ReportItem }
                  })
                  .filter((entry): entry is { item: ReportItem } => entry !== null)
            : []
        const newItems: ReportItem[] = []
        selection.forEach((selectedItem: { item: ReportItem }) => {
            const found = value.value.some((item) => item.id === selectedItem.item.id)
            if (!found) {
                selectedItem.item.tag = ICONS.FILE_TABLE_OUTLINE
                newItems.push(selectedItem.item)
            }
        })
        return newItems
    }

    const handleAdd = (): void => {
        const newItems = collectNewItems()

        // Confirm whenever any non-completed report is being added, but only when
        // the backend "Automatic cascade state changes" setting is enabled —
        // otherwise adding incomplete reports has no cascade side effect.
        if (cascadeStatesEnabled.value && newItems.some((item) => !isReportFinal(item))) {
            pendingSelection.value = newItems
            showCompletionConfirm.value = true
            return
        }

        applySelection(newItems)
    }

    const confirmMessage = computed(() => {
        if (props.productStateIsFinal) {
            return t('product.add_incomplete_reports.message_published')
        }
        return t('product.add_incomplete_reports.message')
    })

    // Display titles of the non-final reports pending confirmation.
    const incompleteReportTitles = computed<string[]>(() => {
        if (!pendingSelection.value) return []
        return pendingSelection.value
            .filter((item) => !isReportFinal(item))
            .map((item) => titleOf(item).title || item.report_type_name || t('product.add_incomplete_reports.untitled'))
    })

    const confirmButton = computed(() => {
        if (props.productStateIsFinal) {
            return t('product.add_incomplete_reports.confirm_published')
        }
        return t('product.add_incomplete_reports.confirm')
    })

    const applySelection = (newItems: ReportItem[]): void => {
        value.value.push(...newItems)
        handleClose()
        emit('items-changed', value.value)
    }

    const confirmAddReports = (): void => {
        showCompletionConfirm.value = false
        if (pendingSelection.value) {
            applySelection(pendingSelection.value)
            pendingSelection.value = null
        }
    }

    const cancelAddReports = (): void => {
        showCompletionConfirm.value = false
        pendingSelection.value = null
    }

    const handleClose = (): void => {
        analyzeStore.multiSelectReport(false)
        selectorOpen.value = false
    }

    const showReportItemDetail = (reportItem: ReportItem): void => {
        reportItemDialog.value.showDetail(reportItem)
    }

    // The product lists its reports in this order: the public web, the presenters and the
    // citation numbers follow it. A change is handed on like any other.
    const canReorder = computed<boolean>(() => props.modify && value.value.length > 1)

    const moveReportItem = (from: number, to: number): void => {
        const items = value.value
        if (from === to || from < 0 || to < 0 || from >= items.length || to >= items.length) return
        items.splice(to, 0, ...items.splice(from, 1))
        emit('items-changed', items)
    }

    // Drag-and-drop reordering, as in the link list editor: the dragged report takes the place
    // of the one it is dropped on.
    const dragIndex = ref<number | null>(null)
    const dragOverIndex = ref<number | null>(null)

    const onDragStart = (index: number, event: DragEvent): void => {
        dragIndex.value = index
        if (event.dataTransfer) {
            event.dataTransfer.effectAllowed = 'move'
            // Some browsers require data to be set for the drag to initiate.
            event.dataTransfer.setData('text/plain', String(index))
        }
    }

    const onDragOver = (index: number, event: DragEvent): void => {
        if (dragIndex.value === null) return
        event.preventDefault()
        if (event.dataTransfer) {
            event.dataTransfer.dropEffect = 'move'
        }
        dragOverIndex.value = index
    }

    const onDragLeave = (index: number): void => {
        if (dragOverIndex.value === index) {
            dragOverIndex.value = null
        }
    }

    const onDrop = (index: number): void => {
        if (dragIndex.value !== null && canReorder.value) {
            moveReportItem(dragIndex.value, index)
        }
        dragIndex.value = null
        dragOverIndex.value = null
    }

    const onDragEnd = (): void => {
        dragIndex.value = null
        dragOverIndex.value = null
    }

    const removeReportItem = (reportItem: ReportItem): void => {
        const index = value.value.findIndex((item) => item.id === reportItem.id)
        if (index > -1) {
            value.value.splice(index, 1)
            emit('items-changed', value.value)
        }
    }

    const updateFilter = (filter: Record<string, unknown>): void => {
        if (contentData.value) {
            contentData.value.updateFilter(filter)
        }
    }

    const handleNewDataLoaded = (count: number): void => {
        if (toolbarFilter.value) {
            toolbarFilter.value.updateDataCount(count)
        }
    }

    const handleUpdateShowingCount = (count: number): void => {
        if (toolbarFilter.value) {
            toolbarFilter.value.updateCurrentlyShowingCount(count)
        }
    }

    defineExpose({
        openSelector
    })
</script>

<style scoped>
    .selector-filter-panel,
    .selector-results {
        overflow: hidden;
        margin: 0.65rem;
        border: 2px solid var(--review-panel-border);
        border-radius: 4px;
        background: var(--review-list-row);
    }

    .selector-results {
        min-height: 0;
        overflow-y: auto;
    }

    .report-order__row {
        display: flex;
        align-items: center;
        border-top: 2px solid transparent;
    }

    .report-order__row.drag-over {
        border-top-color: rgb(var(--v-theme-primary));
    }

    .report-order__row.dragging {
        opacity: 0.5;
    }

    .report-order__controls {
        display: flex;
        flex: 0 0 auto;
        align-items: center;
        margin-inline-end: 4px;
    }

    .report-order__card {
        flex: 1 1 auto;
        min-width: 0;
    }

    .drag-handle {
        cursor: grab;
    }

    .drag-handle:active {
        cursor: grabbing;
    }

    :deep(.v-dialog .v-card) {
        background-color: var(--review-workspace);
        background-image: var(--v-workspace-gradient, none);
    }
</style>
