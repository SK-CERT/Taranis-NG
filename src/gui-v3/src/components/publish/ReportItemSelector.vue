<template>
    <v-container fluid class="pa-0">
        <!-- Dialog Container -->
        <v-dialog v-model="selectorOpen" fullscreen persistent>
            <v-card flat>
                <!-- Fixed Toolbar -->
                <v-toolbar color="primary" dark sticky>
                    <v-btn icon @click="handleClose">
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

                <!-- Main Content -->
                <v-container fluid class="pa-0">
                    <ToolbarFilterAnalyze ref="toolbarFilter" :show-group-toolbar="false" @update-filter="updateFilter" />

                    <ContentDataAnalyze
                        ref="contentData"
                        :show-remove-action="false"
                        :disable-actions="true"
                        :selection="value"
                        card-item="CardAnalyze"
                        class="bg-background"
                        @show-report-item-detail="showReportItemDetail"
                        @new-data-loaded="handleNewDataLoaded"
                        @update-showing-count="handleUpdateShowingCount"
                    />
                </v-container>
            </v-card>
        </v-dialog>

        <!-- New Report Item Dialog -->
        <NewReportItem ref="reportItemDialog" :show-button="false" :read-only="readOnlySelector" />

        <!-- Selected Items Display -->
        <div v-if="!selectorOpen" class="pt-2">
            <CardAnalyze
                v-for="item in value"
                :key="item.id"
                :card="item"
                :show-remove-action="true"
                @show-detail="showReportItemDetail"
                @remove-report-item-from-selector="removeReportItem"
            />
        </div>
    </v-container>
</template>

<script setup lang="ts">
    import { ref, watch, nextTick } from 'vue'
    import { useI18n } from 'vue-i18n'
    import { ICONS } from '@/config/ui-constants'
    import ContentDataAnalyze from '@/components/analyze/ContentDataAnalyze.vue'
    import ToolbarFilterAnalyze from '@/components/analyze/ToolbarFilterAnalyze.vue'
    import CardAnalyze from '@/components/analyze/CardAnalyze.vue'
    import NewReportItem from '@/components/analyze/NewReportItem.vue'
    import { useAnalyzeStore } from '@/stores/analyze'

    type ReportItem = {
        id: number | string
        tag?: string
        [key: string]: any
    }

    const { t } = useI18n()
    const analyzeStore = useAnalyzeStore()

    const props = withDefaults(
        defineProps<{
            values?: ReportItem[]
            modify?: boolean
            edit?: boolean
        }>(),
        {
            values: () => [],
            modify: false,
            edit: false
        }
    )

    const emit = defineEmits<{
        (e: 'items-changed', payload: ReportItem[]): void
    }>()

    const selectorOpen = ref<boolean>(false)
    const value = ref<ReportItem[]>(props.values || [])
    const readOnlySelector = ref<boolean>(true)
    const toolbarFilter = ref<any>(null)
    const contentData = ref<any>(null)
    const reportItemDialog = ref<any>(null)

    watch(
        () => props.values,
        (newValues: ReportItem[]) => {
            value.value = Array.isArray(newValues) ? [...newValues] : []
        },
        { deep: true, immediate: true }
    )

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

    const handleAdd = (): void => {
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
        selection.forEach((selectedItem: { item: ReportItem }) => {
            const found = value.value.some((item) => item.id === selectedItem.item.id)
            if (!found) {
                selectedItem.item.tag = ICONS.FILE_TABLE_OUTLINE
                value.value.push(selectedItem.item)
            }
        })

        handleClose()
        emit('items-changed', value.value)
    }

    const handleClose = (): void => {
        analyzeStore.multiSelectReport(false)
        selectorOpen.value = false
    }

    const showReportItemDetail = (reportItem: ReportItem): void => {
        reportItemDialog.value.showDetail(reportItem)
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
