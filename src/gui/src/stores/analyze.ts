import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { getAllReportItems, getAllReportItemTypes, getAllReportItemGroups } from '@/api/analyze'

type FilterPayload = Record<string, unknown>

type ListState<T = unknown> = {
    total_count: number
    items: T[]
}

type SelectableItem = {
    id: string | number
    [key: string]: unknown
}

type ApiResponse<T> = {
    data?: T
}

const emptyListState = <T = unknown>(): ListState<T> => ({ total_count: 0, items: [] })

export const useAnalyzeStore = defineStore('analyze', () => {
    // State
    const report_items = ref<ListState>(emptyListState())
    const report_item_types = ref<ListState>(emptyListState())
    const multi_select_report = ref(false)
    const selection_report = ref<SelectableItem[]>([])
    const report_item_groups = ref<unknown[]>([])
    const current_report_item_group_id = ref<string | number | null>(null)

    // Getters
    const getReportItemGroups = computed(() => report_item_groups.value)
    const getCurrentReportItemGroup = computed(() => current_report_item_group_id.value)
    const getReportItems = computed(() => report_items.value || emptyListState())
    const getReportItemTypes = computed(() => report_item_types.value || emptyListState())
    const getMultiSelectReport = computed(() => multi_select_report.value)
    const getSelectionReport = computed(() => selection_report.value)
    const selectedReports = computed(() => {
        return new Set(selection_report.value.map((item) => item.id))
    })

    // Actions
    async function loadReportItemGroups(_data: FilterPayload): Promise<ApiResponse<unknown[]>> {
        const response = await getAllReportItemGroups()
        const responseData = response?.data
        report_item_groups.value = Array.isArray(responseData) ? responseData : []
        return response
    }

    async function loadReportItems(data: FilterPayload): Promise<ApiResponse<ListState>> {
        const response = await getAllReportItems(data)
        if (!response) {
            const fallback = { data: report_items.value }
            return fallback
        }
        report_items.value = response.data || emptyListState()
        return response
    }

    async function loadReportItemTypes(_data: FilterPayload): Promise<ApiResponse<ListState>> {
        const response = await getAllReportItemTypes()
        report_item_types.value = response.data || emptyListState()
        return response
    }

    function multiSelectReport(enable: boolean): void {
        multi_select_report.value = enable
        selection_report.value = []
    }

    function selectReport(selected_item: SelectableItem): void {
        selection_report.value.push(selected_item)
    }

    function deselectReport(selectedItem: SelectableItem): void {
        for (let i = 0; i < selection_report.value.length; i++) {
            const item = selection_report.value[i]
            if (item && item.id === selectedItem.id) {
                selection_report.value.splice(i, 1)
                break
            }
        }
    }

    function changeCurrentReportItemGroup(new_current_report_item_group: string | number | null): void {
        current_report_item_group_id.value = new_current_report_item_group
    }

    return {
        // State
        report_items,
        report_item_types,
        multi_select_report,
        selection_report,
        report_item_groups,
        current_report_item_group_id,

        // Getters
        getReportItemGroups,
        getCurrentReportItemGroup,
        getReportItems,
        getReportItemTypes,
        getMultiSelectReport,
        getSelectionReport,
        selectedReports,

        // Actions
        loadReportItemGroups,
        loadReportItems,
        loadReportItemTypes,
        multiSelectReport,
        selectReport,
        deselectReport,
        changeCurrentReportItemGroup
    }
})
