import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { getAllReportItems, getAllReportItemTypes, getAllReportItemGroups } from '@/api/analyze'

export const useAnalyzeStore = defineStore('analyze', () => {
  // State
  const report_items = ref({ total_count: 0, items: [] })
  const report_item_types = ref({ total_count: 0, items: [] })
  const multi_select_report = ref(false)
  const selection_report = ref([])
  const report_item_groups = ref([])
  const current_report_item_group_id = ref(null)

  // Getters
  const getReportItemGroups = computed(() => report_item_groups.value)
  const getCurrentReportItemGroup = computed(() => current_report_item_group_id.value)
  const getReportItems = computed(() => report_items.value || { total_count: 0, items: [] })
  const getReportItemTypes = computed(
    () => report_item_types.value || { total_count: 0, items: [] }
  )
  const getMultiSelectReport = computed(() => multi_select_report.value)
  const getSelectionReport = computed(() => selection_report.value)
  const selectedReports = computed(() => {
    return new Set(selection_report.value.map((item) => item.id))
  })

  // Actions
  async function loadReportItemGroups(data) {
    const response = await getAllReportItemGroups(data)
    report_item_groups.value = response.data || []
    return response
  }

  async function loadReportItems(data) {
    const response = await getAllReportItems(data)
    if (response) {
      report_items.value = response.data || { total_count: 0, items: [] }
    }
    return response
  }

  async function loadReportItemTypes(data) {
    const response = await getAllReportItemTypes(data)
    report_item_types.value = response.data || { total_count: 0, items: [] }
    return response
  }

  function multiSelectReport(enable) {
    multi_select_report.value = enable
    selection_report.value = []
  }

  function selectReport(selected_item) {
    selection_report.value.push(selected_item)
  }

  function deselectReport(selectedItem) {
    for (let i = 0; i < selection_report.value.length; i++) {
      if (selection_report.value[i].id === selectedItem.id) {
        selection_report.value.splice(i, 1)
        break
      }
    }
  }

  function changeCurrentReportItemGroup(new_current_report_item_group) {
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
