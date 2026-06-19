<template>
    <v-container id="selector_analyze" fluid class="pa-2">
        <TransitionGroup name="card-list" tag="div" class="w-100">
            <component
                :is="currentCard"
                v-for="collection in collections"
                :key="collection.id"
                :card="collection"
                :disable-actions="disableActions"
                :multi-select-active="multiSelectActive"
                :show-remove-action="showRemoveAction"
                :preselected="preselected(collection.id)"
                @delete-item="handleDelete"
                @selection-change="handleSelectionChange(collection.id, $event)"
                @show-detail="emit('show-report-item-detail', $event)"
                @edit="emit('show-report-item-detail', $event)"
            />
        </TransitionGroup>
        <div
            v-intersect="infiniteScrolling"
            class="mt-4"
            style="min-height: 100px; display: flex; align-items: center; justify-content: center"
        >
            <div v-if="!dataLoaded" class="text-center text-grey">
                <v-progress-circular indeterminate size="small" />
                <p class="text-caption mt-2">
                    {{ t('common.loading_more') }}
                </p>
            </div>
            <div v-else class="text-caption text-grey">
                {{ t('common.end_of_list') }}
            </div>
        </div>
    </v-container>
</template>

<script setup lang="ts">
    import { ref, watch, onMounted, onUnmounted, computed } from 'vue'
    import { useI18n } from 'vue-i18n'
    import { useRoute } from 'vue-router'
    import { useAnalyzeStore } from '@/stores/analyze'
    import CardAnalyze from './CardAnalyze.vue'
    import CardCompact from '@/components/common/CardCompact.vue'

    type ReportItem = {
        id: string | number
        report_item_type_id?: string | number
        report_type_name?: string
        [key: string]: unknown
    }

    type FilterState = {
        search: string
        range: string
        completed: boolean | string
        sort: string
        compact_mode?: boolean
    }

    const props = withDefaults(
        defineProps<{
            showRemoveAction?: boolean
            disableActions?: boolean
            remoteReports?: boolean
            selection?: Array<{ id: string | number }>
            cardItem?: string
        }>(),
        {
            showRemoveAction: false,
            disableActions: false,
            remoteReports: false,
            selection: () => [],
            cardItem: ''
        }
    )

    const emit = defineEmits(['new-data-loaded', 'show-report-item-detail', 'update-showing-count'])

    const { t } = useI18n()
    const route = useRoute()
    const analyzeStore = useAnalyzeStore()

    const collections = ref<ReportItem[]>([])
    const dataLoaded = ref(false)
    const filter = ref<FilterState>({
        search: '',
        range: 'ALL',
        completed: 'ALL',
        sort: 'DATE_DESC'
    })

    const currentCard = computed(() => {
        if (props.cardItem === 'CardCompact') {
            return CardCompact
        }
        if (props.cardItem === 'CardAnalyze') {
            return CardAnalyze
        }
        return filter.value.compact_mode ? CardCompact : CardAnalyze
    })

    const multiSelectActive = computed(() => analyzeStore.getMultiSelectReport)

    const preselected = (itemId: string | number): boolean => props.selection.some((item) => item.id === itemId)

    const getNormalizedScope = (): string => {
        const scope = route.params['scope']
        if (typeof scope === 'string') {
            return scope
        }
        if (Array.isArray(scope)) {
            return scope[0] || 'local'
        }
        return 'local'
    }

    const infiniteScrolling = (isIntersecting: boolean): void => {
        const totalCount = analyzeStore.getReportItems.total_count || 0
        if (dataLoaded.value && isIntersecting && collections.value.length < totalCount) {
            updateData(true, false)
        }
    }

    const updateData = async (append = false, reloadAll = false): Promise<void> => {
        dataLoaded.value = false

        const totalCount = analyzeStore.getReportItems.total_count || 0
        if (append && totalCount > 0 && collections.value.length >= totalCount) {
            dataLoaded.value = true
            return
        }

        let offset = collections.value.length
        let limit = 20
        if (reloadAll) {
            offset = 0
            if (collections.value.length > limit) {
                limit = collections.value.length
            }
        } else if (append === false) {
            offset = 0
        }

        let group = ''
        if (props.remoteReports) {
            group = typeof analyzeStore.getCurrentReportItemGroup === 'string' ? analyzeStore.getCurrentReportItemGroup : ''
        } else {
            // Extract scope from route params
            const scope = getNormalizedScope()
            if (scope !== 'local') {
                // If scope starts with 'group-', extract the group name
                if (scope.startsWith('group-')) {
                    group = scope.substring(6).replaceAll('-', ' ')
                } else {
                    group = scope.replaceAll('-', ' ')
                }
            }
        }

        try {
            await analyzeStore.loadReportItems({
                group: group,
                filter: filter.value,
                offset: offset,
                limit: limit
            })

            await analyzeStore.loadReportItemTypes({})

            const reportTypes = Array.isArray(analyzeStore.getReportItemTypes.items)
                ? (analyzeStore.getReportItemTypes.items as ReportItem[])
                : []
            const newItems = Array.isArray(analyzeStore.getReportItems.items) ? (analyzeStore.getReportItems.items as ReportItem[]) : []

            if (Array.isArray(newItems) && Array.isArray(reportTypes)) {
                for (let i = 0; i < newItems.length; i++) {
                    const item = newItems[i]
                    if (!item) {
                        continue
                    }
                    const reportType = reportTypes.find((x) => x.id == item.report_item_type_id)
                    if (reportType) {
                        item.report_type_name = String(reportType['title'] || 'Report Item')
                    } else {
                        item.report_type_name = 'Report Item'
                    }
                }
            }

            // Directly assign or concat - Vue will detect removed items and animate them
            if (append) {
                collections.value = collections.value.concat(newItems)
            } else {
                collections.value = newItems
            }

            const totalCount = analyzeStore.getReportItems.total_count || 0
            emit('new-data-loaded', totalCount)
            emit('update-showing-count', collections.value.length)

            setTimeout(() => {
                dataLoaded.value = true
            }, 1000)
        } catch (error) {
            console.error('Error loading report items:', error)
            dataLoaded.value = true
        }
    }

    const handleSelectionChange = (itemId: string | number, isSelected: boolean): void => {
        // Get the full item from collections
        const item = collections.value.find((c) => c.id === itemId)
        if (item) {
            if (isSelected) {
                analyzeStore.selectReport({ id: itemId, item: item })
            } else {
                analyzeStore.deselectReport({ id: itemId })
            }
        }
    }

    const updateFilter = (newFilter: FilterState): void => {
        filter.value = newFilter
        updateData(false, false)
    }

    watch(
        () => route.params['scope'],
        () => {
            updateData(false, false)
        }
    )

    const handleReportItemUpdate = (): void => {
        updateData(false, true)
    }

    const handleReportItemsUpdate = (): void => {
        updateData(false, true)
    }

    onMounted(() => {
        updateData(false, false)
        window.addEventListener('report-item-updated', handleReportItemUpdate as EventListener)
        window.addEventListener('report-items-updated', handleReportItemsUpdate as EventListener)
    })

    onUnmounted(() => {
        window.removeEventListener('report-item-updated', handleReportItemUpdate as EventListener)
        window.removeEventListener('report-items-updated', handleReportItemsUpdate as EventListener)
    })

    const handleDelete = async (): Promise<void> => {
        // Reload current view after successful deletion
        // The animation will trigger when the deleted item is missing from the new data
        await updateData(false, true)
    }

    defineExpose({
        updateData,
        updateFilter
    })
</script>
