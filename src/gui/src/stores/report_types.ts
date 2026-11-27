import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

type ReportTypeSelectionItem = {
    id: string | number
    [key: string]: unknown
}

export const useReportTypesStore = defineStore('report_types', () => {
    // State
    const multi_select_report_type = ref(false)
    const selection = ref<ReportTypeSelectionItem[]>([])

    // Getters
    const getReportTypesMultiSelect = computed(() => multi_select_report_type.value)
    const getReportTypesSelection = computed(() => selection.value)

    // Actions
    function multiSelectReportType(enable: boolean): void {
        multi_select_report_type.value = enable
        selection.value = []
    }

    function selectReportType(selected_item: ReportTypeSelectionItem): void {
        selection.value.push(selected_item)
    }

    function deselectReportType(selectedItem: ReportTypeSelectionItem): void {
        for (let i = 0; i < selection.value.length; i++) {
            const item = selection.value[i]
            if (item && item.id === selectedItem.id) {
                selection.value.splice(i, 1)
                break
            }
        }
    }

    return {
        // State
        multi_select_report_type,
        selection,

        // Getters
        getReportTypesMultiSelect,
        getReportTypesSelection,

        // Actions
        multiSelectReportType,
        selectReportType,
        deselectReportType
    }
})
