<template>
  <v-container>
    <!-- Dialog Container -->
    <v-dialog
      v-model="selectorOpen"
      fullscreen
      persistent
    >
      <v-card flat>
        <!-- Fixed Toolbar -->
        <v-toolbar color="primary" dark sticky>
          <v-btn icon @click="handleClose">
            <v-icon>{{ ICONS.CLOSE }}</v-icon>
          </v-btn>
          <v-toolbar-title>{{ t('report_item.select') }}</v-toolbar-title>
          <v-spacer />
          <v-btn @click="handleAdd">
            <v-icon start>{{ ICONS.PLUS_BOX }}</v-icon>
            {{ t('common.add_items') }}
          </v-btn>
        </v-toolbar>

        <!-- Main Content -->
        <v-container fluid class="pa-0 ma-0 mt-12">
          <div style="position: sticky; top: 0; z-index: 100; background: white">
            <ToolbarFilterAnalyze
              ref="toolbarFilter"
              :show-group-toolbar="false"
              @update-filter="updateFilter"
            />
          </div>

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
        </v-container>
      </v-card>
    </v-dialog>

    <!-- New Report Item Dialog -->
    <NewReportItem ref="reportItemDialog" :show-button="false" :read-only="readOnlySelector" />

    <!-- Selected Items Display -->
    <div v-if="!selectorOpen" class="selected-items-container">
      <v-spacer style="height: 8px" />
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

<script setup>
import { ref, watch, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import { ICONS } from '@/config/ui-constants'
import ContentDataAnalyze from '@/components/analyze/ContentDataAnalyze.vue'
import ToolbarFilterAnalyze from '@/components/analyze/ToolbarFilterAnalyze.vue'
import CardAnalyze from '@/components/analyze/CardAnalyze.vue'
import NewReportItem from '@/components/analyze/NewReportItem.vue'
import { useAnalyzeStore } from '@/stores/analyze'

const { t } = useI18n()
const analyzeStore = useAnalyzeStore()

const props = defineProps({
  values: {
    type: Array,
    default: () => []
  },
  modify: {
    type: Boolean,
    default: false
  },
  edit: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['items-changed'])

const selectorOpen = ref(false)
const value = ref(props.values || [])
const readOnlySelector = ref(true)
const toolbarFilter = ref(null)
const contentData = ref(null)
const reportItemDialog = ref(null)

watch(
  () => props.values,
  (newValues) => {
    value.value = Array.isArray(newValues) ? [...newValues] : []
  },
  { deep: true, immediate: true }
)

const openSelector = async () => {
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

const handleAdd = () => {
  const selection = analyzeStore.getSelectionReport || []
  selection.forEach((selectedItem) => {
    const found = value.value.some((item) => item.id === selectedItem.item.id)
    if (!found) {
      selectedItem.item.tag = ICONS.FILE_TABLE_OUTLINE
      value.value.push(selectedItem.item)
    }
  })

  handleClose()
  emit('items-changed', value.value)
}

const handleClose = () => {
  analyzeStore.multiSelectReport(false)
  selectorOpen.value = false
}

const showReportItemDetail = (reportItem) => {
  reportItemDialog.value.showDetail(reportItem)
}

const removeReportItem = (reportItem) => {
  const index = value.value.findIndex((item) => item.id === reportItem.id)
  if (index > -1) {
    value.value.splice(index, 1)
    emit('items-changed', value.value)
  }
}

const updateFilter = (filter) => {
  if (contentData.value) {
    contentData.value.updateFilter(filter)
  }
}

const handleNewDataLoaded = (count) => {
  if (toolbarFilter.value) {
    toolbarFilter.value.updateDataCount(count)
  }
}

const handleUpdateShowingCount = (count) => {
  if (toolbarFilter.value) {
    toolbarFilter.value.updateCurrentlyShowingCount(count)
  }
}

defineExpose({
  openSelector
})
</script>

<style scoped>
.selected-items-container {
  padding: 0;
  margin: 0;
  background: white;
}
</style>
