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
    sort-tooltip-prefix="publish"
    :search-debounce-ms="800"
    @update-filter="handleFilterUpdate"
    @add-new="emit('add-new')"
  >
    <!-- Add Button Slot -->
    <template #addbutton>
      <slot name="addbutton" />
    </template>

    <!-- Custom Filters: Unpublished/Published -->
    <template #custom-filters="{ filter }">
      <v-divider vertical />

      <div style="display: flex; gap: 4px; flex-wrap: wrap">
        <v-chip
          :color="filter.unpublished ? 'primary' : 'default'"
          :variant="filter.unpublished ? 'flat' : 'outlined'"
          size="small"
          @click="toggleUnpublished"
        >
          <v-tooltip activator="parent" location="bottom">
            {{ t('publish.tooltip.filter_unpublished') }}
          </v-tooltip>
          <v-icon>{{ ICONS.CLOCK_ALERT }}</v-icon>
        </v-chip>
        <v-chip
          :color="filter.published ? 'primary' : 'default'"
          :variant="filter.published ? 'flat' : 'outlined'"
          size="small"
          @click="togglePublished"
        >
          <v-tooltip activator="parent" location="bottom">
            {{ t('publish.tooltip.filter_published') }}
          </v-tooltip>
          <v-icon>{{ ICONS.CHECK_CIRCLE }}</v-icon>
        </v-chip>
      </div>

      <div style="flex-grow: 1" />

      <v-divider vertical />
    </template>
  </BaseToolbarFilter>

  <!-- Selection Group Toolbar -->
  <v-toolbar flat color="surface" density="compact">
    <ToolbarGroup
      ref="toolbarGroup"
      view="publish"
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
        {{ t('publish.tooltip.compact_mode') }}
      </v-tooltip>
      <v-icon>{{ ICONS.FORMAT_LIST_BULLETED }}</v-icon>
    </v-btn>
  </v-toolbar>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { ICONS } from '@/config/ui-constants'
import { usePublishStore } from '@/stores/publish'
import BaseToolbarFilter from '@/components/common/BaseToolbarFilter.vue'
import ToolbarGroup from '@/components/common/ToolbarGroup.vue'

const props = defineProps({
  title: String,
  totalCountTitle: String,
  showAddButton: {
    type: Boolean,
    default: false
  },
  addButtonLabel: {
    type: String,
    default: 'common.add_btn'
  }
})

const emit = defineEmits(['add-new'])

const { t } = useI18n()
const publishStore = usePublishStore()
const baseFilter = ref(null)
const toolbarGroup = ref(null)

const currentlyShowingCount = ref(0)
const selectedCount = ref(0)
const filter = ref({
  search: '',
  range: 'ALL',
  published: false,
  unpublished: true,
  sort: 'DATE_DESC'
})

const compactMode = ref(false)

const multiSelectActive = computed(() => publishStore.getMultiSelect)

const totalCount = computed(() => {
  return publishStore.getProducts.total_count
})

const handleFilterUpdate = (updatedFilter) => {
  filter.value = { ...filter.value, ...updatedFilter }
  emitFilterUpdate()
}

const togglePublished = () => {
  filter.value.published = !filter.value.published
  filter.value.unpublished = false
  emitFilterUpdate()
}

const toggleUnpublished = () => {
  filter.value.unpublished = !filter.value.unpublished
  filter.value.published = false
  emitFilterUpdate()
}

const toggleCompactMode = () => {
  compactMode.value = !compactMode.value
  emitFilterUpdate()
}

const emitFilterUpdate = () => {
  // Emit custom event for content to listen to
  window.dispatchEvent(new CustomEvent('update-products-filter', { detail: {
    ...filter.value,
    compact_mode: compactMode.value
  }}))
}

const handleUpdateData = () => {
  // Emit custom event for content to refresh data
  window.dispatchEvent(new CustomEvent('product-updated'))
}

watch(
  () => publishStore.getSelection,
  (newSelection) => {
    selectedCount.value = newSelection.length
  },
  { deep: true }
)

defineExpose({
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
  emitFilterUpdate()
})
</script>
