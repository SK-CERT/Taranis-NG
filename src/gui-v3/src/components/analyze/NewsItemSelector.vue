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
        >
            <v-card
                flat
                class="selector-layout"
            >
                <!-- Fixed Toolbar -->
                <v-toolbar
                    color="primary"
                    dark
                >
                    <v-btn
                        icon
                        @click="handleClose"
                    >
                        <v-icon>mdi-close-circle</v-icon>
                    </v-btn>
                    <v-toolbar-title>{{ t('assess.attached_news_items') }}</v-toolbar-title>
                    <v-spacer />
                    <v-btn @click="handleAdd">
                        <v-icon start> mdi-plus-box </v-icon>
                        {{ t('common.add_items') }}
                    </v-btn>
                </v-toolbar>

                <!-- Main Content Row -->
                <div class="selector-body">
                    <!-- Left Sidebar: Groups -->
                    <GroupNavList
                        :groups="groups"
                        :active-id="selectedGroupId"
                        @select="onGroupSelect"
                    />

                    <!-- Right Content Area: Toolbar + Items -->
                    <div class="selector-main">
                        <!-- Toolbar Filter -->
                        <ToolbarFilterAssess
                            ref="toolbarFilter"
                            :analyze_selector="true"
                            :total_count_title="'assess.total_count'"
                            @update-filter="handleFilterUpdate"
                        />

                        <div class="selector-results bg-background">
                            <!-- Content Data -->
                            <ContentDataAssess
                                ref="contentData"
                                :analyze_selector="true"
                                :selection="selectedItems"
                                class="item-selector"
                                :self-i-d="'selector_assess_analyze'"
                                :data_set="'assess_news_item'"
                                @new-data-loaded="handleNewDataLoaded"
                                @update-showing-count="handleUpdateShowingCount"
                                @card-items-reindex="handleCardItemsReindex"
                            />
                        </div>
                    </div>
                </div>
            </v-card>
        </v-dialog>

        <!-- Items Display (outside dialog) -->
        <v-row v-if="!selectorOpen">
            <v-col
                v-for="item in value"
                :key="item.id"
                cols="12"
            >
                <BaseCard
                    :multi-select-active="false"
                    :show-selection-checkbox="false"
                    :preselected="false"
                    card-class="card-item"
                >
                    <!-- Content Slot -->
                    <template #content>
                        <div
                            class="d-flex align-center"
                            style="gap: 12px"
                        >
                            <!-- News Item Content (click to read) -->
                            <div
                                class="flex-grow-1"
                                style="cursor: pointer"
                                :title="t('assess.read_news_item')"
                                @click="openDetail(item)"
                            >
                                <!-- Source and Date Info -->
                                <div class="text-caption text-grey mb-2">
                                    <v-row align="center">
                                        <v-col cols="auto">
                                            <span v-if="getNewsItemCount(item) > 0">
                                                {{
                                                    getFirstNewsItem(item)?.news_item_data?.osint_source_name ||
                                                    getFirstNewsItem(item)?.news_item_data?.source ||
                                                    'Unknown'
                                                }}
                                            </span>
                                        </v-col>
                                        <v-spacer />
                                        <v-col cols="auto">
                                            <span v-if="getNewsItemCount(item) > 0">
                                                {{ t('card_item.published') }}:
                                                {{ getFirstNewsItem(item)?.news_item_data?.published || 'N/A' }}
                                            </span>
                                        </v-col>
                                    </v-row>
                                </div>
                                <div class="text-h6 font-weight-medium mb-2">
                                    {{ item.title }}
                                </div>
                                <div class="text-body-2 mb-3">
                                    {{ item.description }}
                                </div>

                                <!-- Aggregate: expand to reveal the child news items (like Assess) -->
                                <v-btn
                                    v-if="getNewsItemCount(item) > 1"
                                    size="small"
                                    color="primary"
                                    variant="outlined"
                                    @click.stop="toggleExpand(item.id)"
                                >
                                    <v-icon start>
                                        {{ isExpanded(item.id) ? ICONS.ARROW_DOWN_DROP_CIRCLE : ICONS.ARROW_RIGHT_DROP_CIRCLE }}
                                    </v-icon>
                                    {{ t('card_item.aggregated_items') }}: {{ getNewsItemCount(item) }}
                                </v-btn>
                            </div>

                            <!-- Remove Button on the Right, Centered -->
                            <v-btn
                                size="small"
                                variant="text"
                                :title="t('common.remove')"
                                style="flex-shrink: 0"
                                @click.stop="handleRemoveItem(item)"
                            >
                                <v-icon :color="'error'">
                                    {{ ICONS.REMOVE }}
                                </v-icon>
                            </v-btn>
                        </div>
                    </template>
                </BaseCard>

                <!-- Child news items of the aggregate; click one to read it. -->
                <div
                    v-if="isExpanded(item.id) && getNewsItemCount(item) > 1"
                    class="mt-1"
                >
                    <CardAssessItem
                        v-for="child in item.news_items"
                        :key="child.id"
                        :news-item="child"
                        :analyze-selector="true"
                        @show-detail="openDetail"
                    />
                </div>
            </v-col>
        </v-row>

        <!-- Confirmation Dialog: Remove Item -->
        <v-dialog
            v-model="showRemoveConfirm"
            max-width="500"
        >
            <v-card>
                <v-card-title class="d-flex align-center">
                    <v-icon
                        color="primary"
                        class="mr-2"
                    >
                        mdi-help-circle
                    </v-icon>
                    {{ t('common.messagebox.remove') }}
                </v-card-title>
                <v-card-text>
                    {{ itemToDelete?.title }}
                </v-card-text>
                <v-card-actions>
                    <v-spacer />
                    <v-btn
                        variant="text"
                        @click="showRemoveConfirm = false"
                    >
                        {{ t('common.cancel') }}
                    </v-btn>
                    <v-btn
                        color="primary"
                        variant="text"
                        @click="confirmRemoveItem"
                    >
                        {{ t('common.remove') }}
                    </v-btn>
                </v-card-actions>
            </v-card>
        </v-dialog>

        <!-- News item reader. Contained to the right column in side-by-side mode;
             a normal centered modal otherwise. Read-only (actions hidden). -->
        <NewsItemDetailDialog
            v-model="detailDialog"
            :news-item="detailItem"
            :contained="verticalView"
            multi-select-active
        />
    </v-container>
</template>

<script setup lang="ts">
    import { ref, computed, nextTick, onMounted, onUnmounted, watch } from 'vue'
    import { useI18n } from 'vue-i18n'
    import { useAssessStore } from '@/stores/assess'
    import { useConfigStore } from '@/stores/config'
    import { useAuth } from '@/composables/useAuth'
    import { PERMISSIONS } from '@/services/auth/permissions'
    import { updateReportItem, getReportItemData } from '@/api/analyze'
    import { ICONS } from '@/config/ui-constants'
    import ToolbarFilterAssess from '@/components/assess/ToolbarFilterAssess.vue'
    import NewsItemDetailDialog from '@/components/assess/NewsItemDetailDialog.vue'
    import CardAssessItem from '@/components/assess/CardAssessItem.vue'
    import ContentDataAssess from '@/components/assess/ContentDataAssess.vue'
    import BaseCard from '@/components/common/BaseCard.vue'
    import GroupNavList from '@/components/common/GroupNavList.vue'

    type SelectorItem = {
        id: number | string
        title?: string
        description?: string
        in_reports_count?: number
        news_items?: Array<{
            id: number | string
            news_item_data?: {
                osint_source_name?: string
                source?: string
                published?: string
                link?: string
                [key: string]: unknown
            }
            [key: string]: unknown
        }>
        [key: string]: unknown
    }

    type SelectorGroup = {
        id: string
        title: string
        icon: string
        color?: string
        translate?: boolean
    }

    type ReportItemUpdateDetail = {
        report_item_id?: number
        user_id?: number | string
        add?: boolean
        delete?: boolean
        aggregate_id?: number | string
        [key: string]: unknown
    }

    const props = withDefaults(
        defineProps<{
            values?: SelectorItem[]
            reportItemId?: number
            edit?: boolean
            modify?: boolean
            attach?: string | object | boolean
            verticalView?: boolean
        }>(),
        {
            values: () => [],
            edit: false,
            modify: true,
            verticalView: false
        }
    )

    const emit = defineEmits<{
        (e: 'update:modelValue', value: SelectorItem[]): void
        (e: 'items-changed', value: SelectorItem[]): void
    }>()

    const { t } = useI18n()
    const assessStore = useAssessStore()
    const configStore = useConfigStore()
    const { checkPermission, getUserId } = useAuth()

    // Refs
    const toolbarFilter = ref<any>(null)
    const contentData = ref<any>(null)

    // Reactive state
    const selectorOpen = ref<boolean>(false)
    const detailDialog = ref<boolean>(false)
    const detailItem = ref<SelectorItem | null>(null)
    const value = ref<SelectorItem[]>(props.values || [])
    const selectedItems = ref<SelectorItem[]>(props.values || [])
    const groups = ref<SelectorGroup[]>([])
    const selectedGroupId = ref<string | null>(null)
    const showRemoveConfirm = ref<boolean>(false)
    const itemToDelete = ref<SelectorItem | null>(null)

    watch(
        () => props.values,
        (newValues: SelectorItem[]) => {
            const normalized = Array.isArray(newValues) ? [...newValues] : []
            value.value = normalized
            selectedItems.value = normalized
        },
        { deep: true, immediate: true }
    )

    // Computed
    const canModify = computed(() => {
        return props.edit === false || (checkPermission(PERMISSIONS.ANALYZE_UPDATE) && props.modify === true)
    })

    const getFirstNewsItem = (item: SelectorItem): NonNullable<SelectorItem['news_items']>[number] | null => {
        return item.news_items?.[0] ?? null
    }

    const getNewsItemCount = (item: SelectorItem): number => {
        return item.news_items?.length ?? 0
    }

    // Open the news item for reading. In side-by-side mode the dialog is contained to the
    // right-hand column so the user can read it next to the report form.
    const openDetail = (item: SelectorItem): void => {
        detailItem.value = item
        detailDialog.value = true
    }

    // Track which aggregate cards are expanded to reveal their child news items.
    const expandedItems = ref<Record<string, boolean>>({})
    const isExpanded = (id: string | number): boolean => !!expandedItems.value[String(id)]
    const toggleExpand = (id: string | number): void => {
        expandedItems.value[String(id)] = !expandedItems.value[String(id)]
    }

    // Methods
    const changeGroup = async (groupId: string): Promise<void> => {
        selectedGroupId.value = groupId
        assessStore.changeCurrentGroup(groupId)
        if (contentData.value) {
            contentData.value.updateData?.(false, false)
        }
    }

    const onGroupSelect = (group: { id: string | number }): void => {
        changeGroup(String(group.id))
    }

    const openSelector = async (): Promise<void> => {
        // Initialize selected group
        selectedGroupId.value = selectedGroupId.value || groups.value[0]?.id || 'all'

        // Ensure the store has a current group set so ContentDataAssess can build the API URL
        assessStore.changeCurrentGroup(selectedGroupId.value)

        // Clear previous selections
        assessStore.multiSelect(false)
        window.dispatchEvent(new CustomEvent('multi-select-off'))

        // Enable multi-select for this session
        assessStore.multiSelect(true)

        selectorOpen.value = true

        await nextTick()

        for (const item of value.value) {
            if (item?.id) {
                assessStore.select({ type: 'news_item_aggregate', id: item.id, item })
            }
        }

        if (toolbarFilter.value) {
            toolbarFilter.value.updateSelectedCount?.(value.value.length)
        }
    }

    const handleAdd = async (): Promise<void> => {
        try {
            const selection = (assessStore.getSelection || []) as Array<{ type?: string; item?: SelectorItem }>
            const addedValues: SelectorItem[] = []
            const aggregateIds: Array<number | string> = []

            // Find selected aggregate items that aren't already in values
            for (const selItem of selection) {
                const isAggregateType = selItem?.type === 'AGGREGATE' || selItem?.type === 'news_item_aggregate'

                const item = selItem?.item
                if (isAggregateType && item?.id) {
                    const found = value.value.some((v) => v.id === item.id)
                    if (!found) {
                        addedValues.push(item)
                        aggregateIds.push(item.id)
                    }
                }
            }

            // If editing with a valid report item ID, make API call
            if (props.edit === true && props.reportItemId && props.reportItemId > 0) {
                const data = {
                    add: true,
                    report_item_id: props.reportItemId,
                    aggregate_ids: aggregateIds
                }

                await updateReportItem(props.reportItemId, data)

                // Update counts and add to values
                for (const item of addedValues) {
                    item.in_reports_count = (item.in_reports_count || 0) + 1
                    value.value.push(item)
                }
            } else {
                // Just update locally (for pre-save or read-only)
                for (const item of addedValues) {
                    item.in_reports_count = (item.in_reports_count || 0) + 1
                    value.value.push(item)
                }
            }

            // Deselect and close
            assessStore.multiSelect(false)
            selectorOpen.value = false

            // Emit event for parent
            emit('items-changed', value.value)
        } catch (error: unknown) {
            console.error('Error adding items to report:', error)
            window.dispatchEvent(
                new CustomEvent('notification', {
                    detail: { type: 'error', message: t('error.server_error') }
                })
            )
        }
    }

    const handleClose = (): void => {
        assessStore.multiSelect(false)
        selectorOpen.value = false
    }

    const handleNewDataLoaded = (count: number): void => {
        if (toolbarFilter.value) {
            toolbarFilter.value.updateDataCount?.(count)
        }
    }

    const handleUpdateShowingCount = (count: number): void => {
        if (toolbarFilter.value) {
            toolbarFilter.value.updateCurrentlyShowingCount?.(count)
        }
    }

    const handleCardItemsReindex = (): void => {
        // Handle reindexing if needed
    }

    const handleFilterUpdate = (filter: Record<string, unknown>): void => {
        if (contentData.value) {
            contentData.value.updateFilter?.(filter)
        }
    }

    const handleRemoveItem = (item: SelectorItem): void => {
        // Check permissions before allowing removal
        if (!canModify.value) {
            window.dispatchEvent(
                new CustomEvent('notification', {
                    detail: { type: 'warning', message: t('common.no_permission') }
                })
            )
            return
        }
        itemToDelete.value = item
        showRemoveConfirm.value = true
    }

    const handleUpdateItem = (_item: SelectorItem): void => {
        // Handle item updates if needed
    }

    const confirmRemoveItem = async (): Promise<void> => {
        if (!itemToDelete.value) return

        try {
            const data = {
                delete: true,
                aggregate_id: itemToDelete.value.id
            }

            if (props.edit === true && props.reportItemId && props.reportItemId > 0) {
                await updateReportItem(props.reportItemId, data)
            }

            // Remove from array
            const index = value.value.indexOf(itemToDelete.value)
            if (index > -1) {
                value.value.splice(index, 1)
            }

            showRemoveConfirm.value = false
            itemToDelete.value = null

            // Emit event for parent
            emit('items-changed', value.value)
        } catch (error: unknown) {
            console.error('Error removing item from report:', error)
            window.dispatchEvent(
                new CustomEvent('notification', {
                    detail: { type: 'error', message: t('error.server_error') }
                })
            )
        }
    }

    const handleReportItemUpdated = async (dataInfo: ReportItemUpdateDetail): Promise<void> => {
        if (props.edit === true && props.reportItemId && props.reportItemId > 0 && props.reportItemId === dataInfo.report_item_id) {
            const currentUserId = getUserId()
            if (dataInfo.user_id !== currentUserId) {
                if (dataInfo.add !== undefined) {
                    const response = await getReportItemData(props.reportItemId, dataInfo)
                    const data = (response as { data?: { news_item_aggregates?: SelectorItem[] } }).data
                    if (data?.news_item_aggregates) {
                        value.value.push(...data.news_item_aggregates)
                        emit('items-changed', value.value)
                    }
                } else if (dataInfo.delete !== undefined) {
                    value.value = value.value.filter((item) => item.id !== dataInfo.aggregate_id)
                    emit('items-changed', value.value)
                }
            }
        }
    }

    const handleReportItemUpdatedEvent = (event: Event): void => {
        const customEvent = event as CustomEvent<ReportItemUpdateDetail>
        handleReportItemUpdated(customEvent.detail)
    }

    // Lifecycle
    onMounted(async () => {
        // Load the same OSINT source groups the Assess view shows in its sidebar
        // (includes the leading "All" category). Read/unread is handled by the toolbar filter.
        try {
            await configStore.loadOSINTSourceGroupsAssess({ search: '' })
            groups.value = configStore.osintSourceGroupsForAssess.map((g) => {
                const group: SelectorGroup = {
                    id: String(g.id),
                    title: g.title,
                    icon: g.icon,
                    translate: !!g.translate
                }
                if (g.color) group.color = g.color
                return group
            })
        } catch (error) {
            console.error('Error loading OSINT source groups:', error)
        }

        const firstGroup = groups.value[0]
        selectedGroupId.value = firstGroup ? firstGroup.id : ''

        // Listen for report item updates
        window.addEventListener('report-item-updated', handleReportItemUpdatedEvent)
    })

    onUnmounted(() => {
        window.removeEventListener('report-item-updated', handleReportItemUpdatedEvent)
    })

    // Expose methods for external use
    defineExpose({
        openSelector
    })
</script>

<style scoped>
    .item-selector {
        cursor: pointer;
    }

    .selector-layout {
        height: 100vh;
        display: grid;
        grid-template-rows: auto minmax(0, 1fr);
        overflow: hidden;
    }

    .selector-body {
        min-height: 0;
        display: grid;
        grid-template-columns: 100px minmax(0, 1fr);
        overflow: hidden;
    }

    .selector-main {
        min-width: 0;
        min-height: 0;
        display: grid;
        grid-template-rows: auto minmax(0, 1fr);
        overflow: hidden;
    }

    .selector-results {
        min-height: 0;
        overflow-y: auto;
    }
</style>
