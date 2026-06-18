<template>
    <v-dialog v-model="isOpen" max-width="900px" @click:outside="close">
        <v-card>
            <v-toolbar color="primary" dark flat>
                <v-toolbar-title>
                    {{ t('assess.reports_dialog.title') }}
                </v-toolbar-title>
                <v-spacer />
                <v-btn icon @click="close">
                    <v-icon>{{ ICONS.CLOSE_BOX }}</v-icon>
                </v-btn>
            </v-toolbar>

            <v-card-text class="pa-4">
                <!-- Loading state -->
                <div v-if="loading" class="text-center pa-4">
                    <v-progress-circular indeterminate color="primary" />
                </div>

                <!-- Error state -->
                <div v-else-if="error" class="text-center pa-4">
                    <v-icon color="error" size="large">
                        {{ ICONS.ALERT_CIRCLE }}
                    </v-icon>
                    <p class="mt-2">
                        {{ error }}
                    </p>
                </div>

                <!-- List view -->
                <div v-else-if="reports.length === 0" class="text-center pa-4">
                    <v-icon size="large">
                        {{ ICONS.INFORMATION_OUTLINE }}
                    </v-icon>
                    <p class="mt-2">
                        {{ t('assess.reports_dialog.no_reports') }}
                    </p>
                </div>

                <div v-else class="space-y-3">
                    <div v-for="report in reports" :key="report.id" class="d-flex align-center ga-2">
                        <div class="flex-grow-1">
                            <CardAnalyze
                                :card="toAnalyzeCard(report)"
                                :show-remove-action="true"
                                :disable-actions="false"
                                @show-detail="viewReport"
                                @remove-report-item-from-selector="removeReport"
                            />
                        </div>
                    </div>
                </div>
            </v-card-text>
        </v-card>
    </v-dialog>
</template>

<script setup lang="ts">
    import { ref } from 'vue'
    import { ICONS } from '@/config/ui-constants'
    import { useI18n } from 'vue-i18n'
    import { getReportItemsByAggregate, updateReportItem } from '@/api/analyze'
    import { useAnalyzeStore } from '@/stores/analyze'
    import CardAnalyze from '@/components/analyze/CardAnalyze.vue'

    type ReportItem = {
        id: number | string
        access?: boolean
        modify?: boolean
        report_item_type_id?: number | string
        report_type_name?: string
        [key: string]: unknown
    }

    type AggregateCard = {
        id: number | string
        in_reports_count?: number
        [key: string]: unknown
    }

    type ReportResponse = {
        data?:
            | {
                  data?: ReportItem[]
                  [key: string]: unknown
              }
            | ReportItem[]
    }

    const { t } = useI18n()
    const analyzeStore = useAnalyzeStore()

    const isOpen = ref<boolean>(false)
    const loading = ref<boolean>(false)
    const error = ref<string | null>(null)
    const reports = ref<ReportItem[]>([])
    const currentCard = ref<AggregateCard | null>(null)

    const emit = defineEmits<{
        (e: 'view-report-detail', report: ReportItem): void
    }>()

    const normalizeReportItems = (response: ReportResponse): ReportItem[] => {
        const payload = response?.data
        if (Array.isArray(payload)) {
            return payload
        }
        if (payload && Array.isArray(payload.data)) {
            return payload.data
        }
        return []
    }

    const open = async (card: AggregateCard): Promise<void> => {
        currentCard.value = card

        // If only one report, open it directly without dialog
        if (card.in_reports_count === 1) {
            try {
                const response = (await getReportItemsByAggregate(card.id)) as ReportResponse
                const reportItems = normalizeReportItems(response)

                if (reportItems && reportItems.length === 1) {
                    const firstReportItem = reportItems[0]
                    if (firstReportItem) {
                        emit('view-report-detail', firstReportItem)
                    }
                    return
                }
            } catch (err) {
                console.error('Error fetching report:', err)
            }
        }

        // Show dialog for multiple or fallback cases
        showDialog(card)
    }

    const showDialog = async (card: AggregateCard): Promise<void> => {
        isOpen.value = true
        loading.value = true
        error.value = null
        reports.value = []

        try {
            // Report item types are needed to resolve the type name shown on each card
            // (the aggregate response only carries report_item_type_id, like the Analyze list).
            if (!analyzeStore.getReportItemTypes.items?.length) {
                await analyzeStore.loadReportItemTypes({})
            }

            const response = (await getReportItemsByAggregate(card.id)) as ReportResponse
            const reportItems = normalizeReportItems(response)
            reports.value = reportItems || []
            loading.value = false
        } catch (err) {
            console.error('Error fetching reports:', err)
            error.value = t('assess.reports_dialog.error_loading')
            loading.value = false
        }
    }

    const viewReport = (report: ReportItem): void => {
        // Emit event to open report in NewReportItem
        emit('view-report-detail', report)
        close()
    }

    const toAnalyzeCard = (report: ReportItem): ReportItem => {
        // Resolve the report type name from its id, the same way the Analyze list does,
        // so the card shows the type (the aggregate response has no report_type_name).
        const types = Array.isArray(analyzeStore.getReportItemTypes.items)
            ? (analyzeStore.getReportItemTypes.items as Array<{ id: number | string; title?: string }>)
            : []
        const reportType = types.find((x) => x.id == report.report_item_type_id)

        // CardAnalyze gates click by access/modify flags; set safe defaults for dialog usage.
        return {
            ...report,
            report_type_name: report.report_type_name ?? (reportType?.title || 'Report Item'),
            access: report.access ?? true,
            modify: report.modify ?? true
        }
    }

    const close = (): void => {
        isOpen.value = false
        reports.value = []
        currentCard.value = null
        error.value = null
    }

    const removeReport = async (report: ReportItem): Promise<void> => {
        try {
            const data: {
                delete: true
                aggregate_id?: number | string
            } = {
                delete: true
            }

            if (currentCard.value?.id !== undefined) {
                data.aggregate_id = currentCard.value.id
            }

            await updateReportItem(report.id, data)

            // Remove the report from the list
            reports.value = reports.value.filter((r) => r.id !== report.id)
            if (currentCard.value) {
                currentCard.value.in_reports_count = Math.max(0, (currentCard.value.in_reports_count || 0) - 1)
            }

            // If no reports left, close the dialog
            if (reports.value.length === 0) {
                close()
            }

            // Show success notification
            window.dispatchEvent(
                new CustomEvent('notification', {
                    detail: {
                        type: 'success',
                        message: t('report_item.removed_from_report')
                    }
                })
            )
        } catch (err) {
            console.error('Error removing aggregate:', err)
            error.value = t('assess.reports_dialog.error_removing')
        }
    }

    defineExpose({
        open,
        close
    })
</script>

<style scoped>
    .space-y-3 > * + * {
        margin-top: 12px;
    }
</style>
