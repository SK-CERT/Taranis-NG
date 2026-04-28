<template>
  <BaseToolbarFilter
    ref="baseFilter"
    :title="title"
    :total-count-title="totalCountTitle"
    :total-count="totalCount"
    :currently-showing-count="currentlyShowingCount"
    :initial-filter="filter"
    :show-day-ranges="true"
    :show-sort="true"
    :show-selected-count="multiSelectActive"
    :selected-count-title="'toolbar_filter.selected_count'"
    :selected-count="selectedCount"
    :show-add-button="showAddButton"
    :add-button-label="addButtonLabel"
    sort-tooltip-prefix="analyze"
    @update-filter="handleFilterUpdate"
    @add-new="emit('add-new')"
  >
    <!-- Add Button Slot -->
    <template #addbutton>
      <slot name="addbutton" />
    </template>

    <!-- Custom Filters: Incompleted/Completed -->
    <template #custom-filters="{ filter }">
      <v-divider vertical />

      <div style="display: flex; gap: 4px; flex-wrap: wrap">
        <v-chip
          :color="filter.incompleted ? 'primary' : 'default'"
          :variant="filter.incompleted ? 'flat' : 'outlined'"
          size="small"
          @click="toggleIncompleted"
        >
          <v-tooltip activator="parent" location="bottom">
            {{ t('analyze.tooltip.filter_incomplete') }}
          </v-tooltip>
          <v-icon>mdi-clock-alert</v-icon>
        </v-chip>
        <v-chip
          :color="filter.completed ? 'primary' : 'default'"
          :variant="filter.completed ? 'flat' : 'outlined'"
          size="small"
          @click="toggleCompleted"
        >
          <v-tooltip activator="parent" location="bottom">
            {{ t('analyze.tooltip.filter_completed') }}
          </v-tooltip>
          <v-icon>mdi-check-circle</v-icon>
        </v-chip>
      </div>

      <div style="flex-grow: 1" />

      <v-divider vertical />
    </template>
  </BaseToolbarFilter>

  <!-- Selection Group Toolbar -->
  <v-toolbar
    v-if="showGroupToolbar"
    flat
    color="surface"
    density="compact"
  >
    <ToolbarGroup
      ref="toolbarGroup"
      view="analyze"
      :current-filter="filter"
      @update-data="handleUpdateData"
    />

    <v-spacer />
    <v-btn
      icon
      size="small"
      :color="compactMode ? 'primary' : 'default'"
      @click="toggleCompactMode"
    >
      <v-tooltip activator="parent" location="bottom">
        {{ t('analyze.tooltip.compact_mode') }}
      </v-tooltip>
      <v-icon>mdi-format-list-bulleted</v-icon>
    </v-btn>
  </v-toolbar>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAnalyzeStore } from '@/stores/analyze'
import BaseToolbarFilter from '@/components/common/BaseToolbarFilter.vue'
import ToolbarGroup from '@/components/common/ToolbarGroup.vue'

const props = defineProps({
  title: {
    type: String,
    default: 'nav_menu.report_items'
  },
  totalCountTitle: {
    type: String,
    default: 'analyze.total_count'
  },
  multiSelect: Boolean,
  showGroupToolbar: {
    type: Boolean,
    default: true
  },
  showAddButton: {
    type: Boolean,
    default: false
  },
  addButtonLabel: {
    type: String,
    default: 'common.add_btn'
  }
})

const emit = defineEmits(['update-filter', 'update-data', 'add-new'])

const { t } = useI18n()
const analyzeStore = useAnalyzeStore()
const baseFilter = ref(null)
const toolbarGroup = ref(null)

const totalCount = ref(0)
const currentlyShowingCount = ref(0)
const selectedCount = ref(0)
const filter = ref({
  search: '',
  range: 'ALL',
  completed: false,
  incompleted: true,
  sort: 'DATE_DESC'
})

const compactMode = ref(false)

const multiSelectActive = computed(() => analyzeStore.getMultiSelectReport)

const handleFilterUpdate = (updatedFilter) => {
  filter.value = { ...filter.value, ...updatedFilter }
  emitFilter()
}

const toggleCompleted = () => {
  filter.value.completed = !filter.value.completed
  filter.value.incompleted = false
  emitFilter()
}

const toggleIncompleted = () => {
  filter.value.incompleted = !filter.value.incompleted
  filter.value.completed = false
  emitFilter()
}

const toggleCompactMode = () => {
  compactMode.value = !compactMode.value
  emitFilter()
}

const emitFilter = () => {
  emit('update-filter', {
    ...filter.value,
    compact_mode: compactMode.value
  })
}

const handleUpdateData = () => {
  emit('update-data')
}

watch(
  () => analyzeStore.getSelectionReport,
  (newSelection) => {
    selectedCount.value = newSelection.length
  },
  { deep: true }
)

defineExpose({
  updateDataCount: (count) => {
    totalCount.value = count
  },
  updateCurrentlyShowingCount: (count) => {
    currentlyShowingCount.value = count
  },
  updateShowingCount: (count) => {
    currentlyShowingCount.value = count
  },
  toolbarGroup
})

onMounted(() => {
  // Emit default filter on mount
  emitFilter()
})
</script>
