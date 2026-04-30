<template>
  <v-container id="selector_analyze" fluid>
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
      style="min-height: 100px; display: flex; align-items: center; justify-content: center;"
    >
      <div v-if="!dataLoaded" class="text-center text-grey">
        <v-progress-circular indeterminate size="small" />
        <p class="text-caption mt-2">{{ t('common.loading_more') }}</p>
      </div>
      <div v-else class="text-caption text-grey">
        {{ t('common.scroll_to_load_more') }}
      </div>
    </div>
  </v-container>
</template>

<script setup>
import { ref, watch, onMounted, onUnmounted, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import { useAnalyzeStore } from '@/stores/analyze'
import CardAnalyze from './CardAnalyze.vue'
import CardCompact from '@/components/common/CardCompact.vue'

const props = defineProps({
  showRemoveAction: Boolean,
  disableActions: {
    type: Boolean,
    default: false
  },
  remoteReports: Boolean,
  selection: Array,
  cardItem: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['new-data-loaded', 'show-report-item-detail', 'update-showing-count'])

const { t } = useI18n()
const route = useRoute()
const analyzeStore = useAnalyzeStore()

const collections = ref([])
const dataLoaded = ref(false)
const filter = ref({
  search: '',
  range: 'ALL',
  completed: false,
  incompleted: true,
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

const preselected = (itemId) => {
  if (props.selection != null) {
    for (let i = 0; i < props.selection.length; i++) {
      if (props.selection[i].id === itemId) {
        return true
      }
    }
  }
  return false
}

const infiniteScrolling = (isIntersecting) => {
  const totalCount = analyzeStore.getReportItems.total_count || 0
  if (dataLoaded.value && isIntersecting && collections.value.length < totalCount) {
    updateData(true, false)
  }
}

const updateData = async (append, reloadAll) => {
  dataLoaded.value = false

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
    group = analyzeStore.getCurrentReportItemGroup
  } else {
    // Extract scope from route params
    const scope = route.params.scope || 'local'
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

    await analyzeStore.loadReportItemTypes()

    const reportTypes = analyzeStore.getReportItemTypes.items || []
    const newItems = analyzeStore.getReportItems.items || []

    if (Array.isArray(newItems) && Array.isArray(reportTypes)) {
      for (let i = 0; i < newItems.length; i++) {
        const reportType = reportTypes.find((x) => x.id == newItems[i].report_item_type_id)
        if (reportType) {
          newItems[i].report_type_name = reportType.title
        } else {
          newItems[i].report_type_name = 'Report Item'
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

const handleSelectionChange = (itemId, isSelected) => {
  // Get the full item from collections
  const item = collections.value.find(c => c.id === itemId)
  if (item) {
    if (isSelected) {
      analyzeStore.selectReport({ id: itemId, item: item })
    } else {
      analyzeStore.deselectReport({ id: itemId })
    }
  }
}

const updateFilter = (newFilter) => {
  filter.value = newFilter
  updateData(false, false)
}

watch(
  () => route.params.scope,
  () => {
    updateData(false, false)
  }
)

const handleReportItemUpdate = () => {
  updateData(false, true)
}

const handleReportItemsUpdate = () => {
  updateData(false, true)
}

onMounted(() => {
  updateData(false, false)
  window.addEventListener('report-item-updated', handleReportItemUpdate)
  window.addEventListener('report-items-updated', handleReportItemsUpdate)
})

onUnmounted(() => {
  window.removeEventListener('report-item-updated', handleReportItemUpdate)
  window.removeEventListener('report-items-updated', handleReportItemsUpdate)
})

const handleDelete = async () => {
  // Reload current view after successful deletion
  // The animation will trigger when the deleted item is missing from the new data
  await updateData(false, true)
}

defineExpose({
  updateData,
  updateFilter
})
</script>
