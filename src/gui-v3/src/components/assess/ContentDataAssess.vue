<template>
  <v-container fluid class="py-4">
    <!-- News Items Cards -->
    <TransitionGroup name="card-list" tag="div" class="w-100">
      <component
        :is="currentCard"
        v-for="news_item in news_items_data"
        :key="news_item.id"
        :card="news_item"
        :analyze-selector="analyze_selector"
        :data_set="data_set"
        :multi-select-active="multiSelectActive"
        :preselected="isPreselected(news_item.id)"
        :hide-reviews="filter.hide_reviews"
        :hide-source-links="filter.hide_source_links"
        :highlight-wordlist="filter.highlight_wordlist"
        @show-detail="showDetail"
        @show-reports-for-item="showReportsForItem"
        @update-item="updateItem"
        @delete-item="handleDelete"
      />
    </TransitionGroup>

    <!-- Infinite Scroll Trigger -->
    <div v-intersect="onIntersect" class="mt-4" style="min-height: 100px; display: flex; align-items: center; justify-content: center">
      <div v-if="loading" class="text-center text-grey">
        <v-progress-circular indeterminate size="small" />
        <p class="text-caption mt-2">{{ t('common.loading_more') }}</p>
      </div>
      <div v-else class="text-caption text-grey">
        {{ t('common.end_of_list') }}
      </div>
    </div>

    <!-- Loading Indicator -->
    <v-row v-if="loading" justify="center" class="my-4">
      <v-progress-circular indeterminate color="primary" />
    </v-row>

    <!-- Empty State -->
    <v-row v-if="!loading && news_items_data.length === 0" justify="center" class="my-8">
      <v-col cols="12" md="6" class="text-center">
        <v-icon size="64" color="grey">{{ ICONS.NEWSPAPER_VARIANT_OUTLINE }}</v-icon>
        <p class="text-h6 text-grey mt-4">{{ t('assess.no_items') }}</p>
      </v-col>
    </v-row>

    <!-- News Item Detail Dialog -->
    <NewsItemDetailDialog
      v-model="detailDialog"
      :news-item="selectedItem"
      :multi-select-active="multiSelectActive"
      @action="handleDetailAction"
      @delete="handleDetailDelete"
    />

    <!-- Reports List Dialog -->
    <ReportsListDialog ref="reportsListDialogRef" @view-report-detail="handleViewReportDetail" />

    <!-- Report Item Detail Modal (opened from ReportsListDialog) -->
    <NewReportItem ref="reportItemModalRef" :show-button="false" />
  </v-container>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import { ICONS } from '@/config/ui-constants'
import { useAssessStore } from '@/stores/assess'
import CardAssess from './CardAssess.vue'
import CardCompact from '@/components/common/CardCompact.vue'
import NewsItemDetailDialog from './NewsItemDetailDialog.vue'
import NewReportItem from '@/components/analyze/NewReportItem.vue'
import ReportsListDialog from './ReportsListDialog.vue'

const props = defineProps({
  analyze_selector: Boolean,
  selection: Array,
  cardItem: String,
  selfID: String,
  data_set: String
})

const emit = defineEmits(['new-data-loaded', 'card-items-reindex', 'update-showing-count'])

const { t } = useI18n()
const route = useRoute()
const assessStore = useAssessStore()

const news_items_data = ref([])
const loading = ref(false)
const news_items_data_loaded = ref(false)
const detailDialog = ref(false)
const selectedItem = ref(null)
const reportsListDialogRef = ref(null)
const reportItemModalRef = ref(null)
const current_group_id = ref('')
const lastIntersectTime = ref(0)
const INTERSECT_DEBOUNCE_MS = 500
const filter = ref({
  search: '',
  range: 'ALL',
  read: false,
  important: 'ALL',
  relevant: 'ALL',
  sort: 'DATE_DESC',
  hide_reviews: false,
  hide_source_links: false,
  highlight_wordlist: false
})

const currentCard = computed(() => {
  return filter.value.compact_mode ? CardCompact : CardAssess
})

const multiSelectActive = computed(() => assessStore.getMultiSelect)

const isPreselected = (item_id) => {
  if (props.selection) {
    return props.selection.some((item) => item.id === item_id)
  }
  return false
}

const onIntersect = (entries) => {
  // v-intersect passes a boolean directly
  let isIntersecting = false
  if (typeof entries === 'boolean') {
    isIntersecting = entries
  } else if (Array.isArray(entries) && entries.length > 0) {
    isIntersecting = entries[0].isIntersecting === true
  } else if (entries && typeof entries === 'object') {
    isIntersecting = entries.isIntersecting === true
  }

  if (isIntersecting && news_items_data_loaded.value && !loading.value) {
    // Debounce: only trigger if enough time has passed since last trigger
    const now = Date.now()
    if (now - lastIntersectTime.value >= INTERSECT_DEBOUNCE_MS) {
      lastIntersectTime.value = now
      updateData(true, false)
    }
  }
}

const showDetail = (news_item) => {
  selectedItem.value = news_item
  detailDialog.value = true
}

const showReportsForItem = (card) => {
  if (reportsListDialogRef.value) {
    reportsListDialogRef.value.open(card)
  }
}

const handleViewReportDetail = (report) => {
  // Open report in NewReportItem modal without navigation
  if (reportItemModalRef.value) {
    reportItemModalRef.value.showDetail(report)
  }
}

const handleDetailAction = async (payload) => {
  const { action, newsItem } = payload
  const group_id = current_group_id.value || route.params.groupId || 'all'

  try {
    switch (action) {
      case 'like':
        await assessStore.voteNewsItemAggregate(group_id, newsItem.id, 1)
        break
      case 'dislike':
        await assessStore.voteNewsItemAggregate(group_id, newsItem.id, -1)
        break
      case 'important':
        await assessStore.importantNewsItemAggregate(group_id, newsItem.id)
        break
      case 'read':
        await assessStore.readNewsItemAggregate(group_id, newsItem.id)
        break
      case 'create-report':
        if (reportItemModalRef.value) {
          reportItemModalRef.value.openDialog([newsItem])
        }
        return
      case 'ungroup':
        // Handle ungrouping
        // This would split the aggregate into individual items
        break
      case 'comment':
        // Save comment to aggregate
        await assessStore.saveNewsItemAggregate(group_id, newsItem.id, newsItem.title, newsItem.description, payload.comment)
        break
      case 'update-aggregate':
        // Save aggregate metadata (title, description)
        await assessStore.saveNewsItemAggregate(group_id, newsItem.id, payload.title, payload.description, newsItem.comments)
        break
    }

    // Reload current view
    await updateData(false, true)

    // Update the selected item in the dialog to show fresh data with updated colors
    if (selectedItem.value && action !== 'delete') {
      const updatedItem = news_items_data.value.find((item) => item.id === selectedItem.value.id)
      if (updatedItem) {
        selectedItem.value = updatedItem
      }
    }

    window.dispatchEvent(
      new CustomEvent('notification', {
        detail: { type: 'success', loc: 'assess.item_updated' }
      })
    )
  } catch (error) {
    console.error('Error handling detail action:', error)
    window.dispatchEvent(
      new CustomEvent('notification', {
        detail: { type: 'error', loc: 'assess.error_updating' }
      })
    )
  }
}

const handleDetailDelete = async (newsItem) => {
  try {
    const group_id = current_group_id.value || route.params.groupId || 'all'
    await assessStore.deleteNewsItemAggregate(group_id, newsItem.id)

    // Close dialog and reload
    detailDialog.value = false
    selectedItem.value = null
    await updateData(false, true)

    window.dispatchEvent(
      new CustomEvent('notification', {
        detail: { type: 'success', loc: 'assess.item_deleted' }
      })
    )
  } catch (error) {
    console.error('Error deleting item:', error)

    const responseData = error?.response?.data
    const isAggregateInUse =
      responseData === 'aggregate_in_use' ||
      responseData?.error === 'aggregate_in_use' ||
      (typeof responseData === 'string' && responseData.includes('aggregate_in_use'))

    if (isAggregateInUse) {
      window.dispatchEvent(
        new CustomEvent('notification', {
          detail: {
            type: 'error',
            message: t('error.aggregate_in_use')
          }
        })
      )
      return
    }

    window.dispatchEvent(
      new CustomEvent('notification', {
        detail: { type: 'error', loc: 'assess.error_deleting' }
      })
    )
  }
}

const updateItem = async (news_item, action) => {
  try {
    const group_id = current_group_id.value || route.params.groupId || 'all'

    switch (action) {
      case 'like':
        await assessStore.voteNewsItemAggregate(group_id, news_item.id, 1)
        break
      case 'dislike':
        await assessStore.voteNewsItemAggregate(group_id, news_item.id, -1)
        break
      case 'important':
        await assessStore.importantNewsItemAggregate(group_id, news_item.id)
        break
      case 'read':
        await assessStore.readNewsItemAggregate(group_id, news_item.id)
        break
      case 'create-report':
        if (reportItemModalRef.value) {
          reportItemModalRef.value.openDialog([news_item])
        }
        return
    }

    // Reload current view
    await updateData(false, true)

    window.dispatchEvent(
      new CustomEvent('notification', {
        detail: { type: 'success', loc: 'assess.item_updated' }
      })
    )
  } catch (error) {
    console.error('Error updating item:', error)
    window.dispatchEvent(
      new CustomEvent('notification', {
        detail: { type: 'error', loc: 'assess.error_updating' }
      })
    )
  }
}

const handleDelete = async () => {
  // Reload current view after successful deletion
  // The animation will trigger when the deleted item is missing from the new data
  await updateData(false, true)
}

const updateFilter = (newFilter) => {
  filter.value = { ...filter.value, ...newFilter }
  updateData(false, false)
}

const handleNewsItemsUpdated = () => {
  updateData(false, true)
}

const handleSelectionChange = (itemId, isSelected) => {
  // Get the full item from news_items_data
  const item = news_items_data.value.find((n) => n.id === itemId)
  if (item) {
    if (isSelected) {
      assessStore.select({ type: 'AGGREGATE', id: itemId, item: item })
    } else {
      assessStore.deselect({ type: 'AGGREGATE', id: itemId })
    }
  }
}

const updateData = async (append = false, reload_all = false) => {
  loading.value = true
  news_items_data_loaded.value = false

  let offset = 0
  let limit = 20

  if (reload_all) {
    if (news_items_data.value.length > limit) {
      limit = news_items_data.value.length
    }
  } else if (append) {
    offset = news_items_data.value.length
  }

  // Get group from route or store
  let group
  if (props.analyze_selector) {
    group = assessStore.getCurrentGroup
  } else {
    // Get groupId from route params
    group = route.params.groupId || 'all'
    assessStore.changeCurrentGroup(group)
  }
  current_group_id.value = group

  try {
    const response = await assessStore.loadNewsItemsByGroup({
      group_id: group,
      data: {
        filter: filter.value,
        offset: offset,
        limit: limit
      }
    })

    if (response) {
      const newItems = assessStore.getNewsItems.items
      if (append) {
        news_items_data.value = news_items_data.value.concat(newItems)
      } else {
        // Directly assign new data - Vue will detect removed items and animate them
        news_items_data.value = newItems
      }

      emit('new-data-loaded', assessStore.getNewsItems.total_count)
      emit('update-showing-count', news_items_data.value.length)
      emit('card-items-reindex')
    }
  } catch (error) {
    console.error('Error loading news items:', error)
  } finally {
    loading.value = false
    news_items_data_loaded.value = true
  }
}

// Watch route changes
watch(
  () => route.params.groupId,
  () => {
    updateData(false, false)
  }
)

// Initial load
onMounted(() => {
  updateData(false, false)
  window.addEventListener('news-items-updated', handleNewsItemsUpdated)
})

onUnmounted(() => {
  window.removeEventListener('news-items-updated', handleNewsItemsUpdated)
})

defineExpose({
  updateFilter,
  updateData
})
</script>
