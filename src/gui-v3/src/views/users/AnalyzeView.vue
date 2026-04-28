<template>
  <ViewLayout>
    <template #panel>
      <ToolbarFilterAnalyze
        ref="toolbarFilter"
        :multi-select="true"
        title="nav_menu.report_items"
        total-count-title="toolbar_filter.total_count"
        :show-add-button="canCreateReportItem"
        @update-filter="updateFilter"
        @update-data="updateData"
        @add-new="handleAddNew"
      />
    </template>
    <template #content>
      <ContentDataAnalyze
        ref="contentData"
        :show-remove-action="false"
        :remote-reports="false"
        :selection="analyzeStore.getSelectionReport"
        @new-data-loaded="newDataLoaded"
        @update-showing-count="updateShowingCount"
        @show-report-item-detail="showReportItemDetail"
      />
    </template>
  </ViewLayout>

  <NewReportItem ref="newReportItemRef" :show-button="false" @data-updated="updateData" />
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAnalyzeStore } from '@/stores/analyze'
import { useAuth } from '@/composables/useAuth'
import ViewLayout from '@/components/layouts/ViewLayout.vue'
import ToolbarFilterAnalyze from '@/components/analyze/ToolbarFilterAnalyze.vue'
import ContentDataAnalyze from '@/components/analyze/ContentDataAnalyze.vue'
import NewReportItem from '@/components/analyze/NewReportItem.vue'

const route = useRoute()
const analyzeStore = useAnalyzeStore()
const { checkPermission } = useAuth()
const toolbarFilter = ref(null)
const contentData = ref(null)
const newReportItemRef = ref(null)

const canCreateReportItem = computed(() => {
  return checkPermission('ANALYZE_CREATE') && !route.path.includes('/group/')
})

const handleAddNew = () => {
  if (newReportItemRef.value) {
    newReportItemRef.value.openDialog()
  }
}

const newDataLoaded = (count) => {
  if (toolbarFilter.value) {
    toolbarFilter.value.updateDataCount(count)
  }
}

const updateShowingCount = (count) => {
  if (toolbarFilter.value) {
    toolbarFilter.value.updateShowingCount(count)
  }
}

const updateFilter = (filter) => {
  if (contentData.value) {
    contentData.value.updateFilter(filter)
  }
}

const updateData = () => {
  if (contentData.value) {
    contentData.value.updateData(false, true)
  }
}

const showReportItemDetail = (reportItem) => {
  if (newReportItemRef.value) {
    newReportItemRef.value.showDetail(reportItem)
  }
}
</script>
