<template>
  <BaseToolbarFilter
    ref="baseFilter"
    :title="title"
    :total-count-title="total_count_title"
    :total-count="totalCount"
    :currently-showing-count="currentlyShowingCount"
    :initial-filter="filter"
    :show-day-ranges="true"
    :show-sort="true"
    :show-selected-count="multiSelectActive"
    :selected-count-title="selected_count_title"
    :selected-count="selectedCount"
    :show-add-button="showAddButton"
    :add-button-label="addButtonLabel"
    sort-tooltip-prefix="assess"
    @update-filter="handleFilterUpdate"
    @add-new="emit('add-new')"
  >
    <!-- Add Button Slot -->
    <template #addbutton>
      <slot name="addbutton" />
    </template>

    <!-- Custom Filters: Three-state filters -->
    <template #custom-filters="{ filter }">
      <v-divider vertical />

      <div style="display: flex; gap: 4px; flex-wrap: wrap">
        <v-chip
          size="small"
          :color="filter.read === 'ALL' ? 'default' : 'primary'"
          :variant="filter.read === 'ALL' ? 'outlined' : 'flat'"
          @click="cycleFilter('read')"
        >
          <v-tooltip activator="parent" location="bottom">{{ readFilterTooltip }}</v-tooltip>
          <v-icon>{{ readFilterIcon }}</v-icon>
        </v-chip>
        <v-chip
          size="small"
          :color="filter.important === 'ALL' ? 'default' : 'primary'"
          :variant="filter.important === 'ALL' ? 'outlined' : 'flat'"
          @click="cycleFilter('important')"
        >
          <v-tooltip activator="parent" location="bottom">{{ importantFilterTooltip }}</v-tooltip>
          <v-icon>{{ importantFilterIcon }}</v-icon>
        </v-chip>
        <v-chip
          size="small"
          :color="filter.relevant === 'ALL' ? 'default' : 'primary'"
          :variant="filter.relevant === 'ALL' ? 'outlined' : 'flat'"
          @click="cycleFilter('relevant')"
        >
          <v-tooltip activator="parent" location="bottom">{{ relevantFilterTooltip }}</v-tooltip>
          <v-icon>{{ relevantFilterIcon }}</v-icon>
        </v-chip>
      </div>

      <div style="flex-grow: 1" />

      <v-divider vertical />
    </template>

    <!-- Sort Buttons: Use default date sort + add relevance sort -->
    <template #sort-buttons="{ filter, toggleDateSort }">
      <!-- Universal date sort button from base -->
      <v-chip
        size="small"
        :color="filter.sort === 'DATE_DESC' || filter.sort === 'DATE_ASC' ? 'primary' : 'default'"
        :variant="filter.sort === 'DATE_DESC' || filter.sort === 'DATE_ASC' ? 'flat' : 'outlined'"
        @click="toggleDateSort"
      >
        <v-tooltip activator="parent" location="bottom">{{ dateSortTooltip }}</v-tooltip>
        <v-icon start>mdi-clock</v-icon>
        <v-icon>{{ dateSortIcon }}</v-icon>
      </v-chip>
      <!-- Relevance sort button (Assess-specific) -->
      <v-chip
        size="small"
        :color="filter.sort === 'RELEVANCE_DESC' ? 'primary' : 'default'"
        :variant="filter.sort === 'RELEVANCE_DESC' ? 'flat' : 'outlined'"
        @click="toggleRelevanceSort"
      >
        <v-tooltip activator="parent" location="bottom">
          {{ t('assess.tooltip.sort.relevance.descending') }}
        </v-tooltip>
        <v-icon start>mdi-thumb-up</v-icon>
        <v-icon>mdi-arrow-down</v-icon>
      </v-chip>
    </template>
  </BaseToolbarFilter>

  <!-- Additional Row: Selection Group and View Options -->
  <v-toolbar flat color="surface" density="compact">
    <ToolbarGroup
      ref="toolbarGroup"
      view="assess"
      :current-filter="filter"
      @update-data="handleUpdateData"
    />

    <v-spacer />

    <!-- Hide Reviews Button -->
    <v-btn
      icon
      size="small"
      :color="hideReviews ? 'primary' : 'default'"
      @click="toggleHideReviews"
    >
      <v-tooltip activator="parent" location="bottom">
        {{ t('assess.tooltip.hide_review') }}
      </v-tooltip>
      <v-icon>{{ hideReviews ? 'mdi-text-short' : 'mdi-text-long' }}</v-icon>
    </v-btn>

    <!-- Hide Source Links Button -->
    <v-btn
      icon
      size="small"
      :color="hideSourceLinks ? 'primary' : 'default'"
      @click="toggleHideSourceLinks"
    >
      <v-tooltip activator="parent" location="bottom">
        {{ t('assess.tooltip.hide_source_link') }}
      </v-tooltip>
      <v-icon>{{ hideSourceLinks ? 'mdi-link-off' : 'mdi-link' }}</v-icon>
    </v-btn>

    <!-- Highlight Wordlist Button -->
    <v-btn
      icon
      size="small"
      :color="highlightWordlist ? 'primary' : 'default'"
      @click="toggleHighlightWordlist"
    >
      <v-tooltip activator="parent" location="bottom">
        {{ t('assess.tooltip.highlight_wordlist') }}
      </v-tooltip>
      <v-icon>{{ highlightWordlist ? 'mdi-alphabetical-off' : 'mdi-alphabetical' }}</v-icon>
    </v-btn>

    <!-- Compact Mode Button -->
    <v-btn
      icon
      size="small"
      :color="compactMode ? 'primary' : 'default'"
      @click="toggleCompactMode"
    >
      <v-tooltip activator="parent" location="bottom">
        {{ t('assess.tooltip.compact_mode') }}
      </v-tooltip>
      <v-icon>mdi-format-list-bulleted</v-icon>
    </v-btn>
  </v-toolbar>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAssessStore } from '@/stores/assess'
import BaseToolbarFilter from '@/components/common/BaseToolbarFilter.vue'
import ToolbarGroup from '@/components/common/ToolbarGroup.vue'

const props = defineProps({
  title: {
    type: String,
    default: 'nav_menu.newsitems'
  },
  total_count_title: {
    type: String,
    default: 'assess.total_count'
  },
  selected_count_title: {
    type: String,
    default: 'toolbar_filter.selected_count'
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

const emit = defineEmits(['update-filter', 'update-data-count', 'update-data', 'add-new'])

const { t } = useI18n()
const assessStore = useAssessStore()
const baseFilter = ref(null)
const toolbarGroup = ref(null)

// Filter state with three-state values: "ALL", true, false
const filter = ref({
  search: '',
  range: 'ALL',
  read: false,
  important: 'ALL',
  relevant: 'ALL',
  sort: 'DATE_DESC'
})

const compactMode = ref(false)
const hideReviews = ref(false)
const hideSourceLinks = ref(false)
const highlightWordlist = ref(false)
const totalCount = ref(0)
const currentlyShowingCount = ref(0)
const selectedCount = ref(0)

const multiSelectActive = computed(() => assessStore.getMultiSelect)

// Filter icons and tooltips
const readFilterIcon = computed(() => {
  if (filter.value.read === 'ALL') return 'mdi-eye-outline'
  if (filter.value.read === false) return 'mdi-eye-off'
  return 'mdi-eye'
})

const readFilterTooltip = computed(() => {
  if (filter.value.read === 'ALL') return t('assess.tooltip.filter_all')
  if (filter.value.read === true) return t('assess.tooltip.filter_read')
  return t('assess.tooltip.filter_unread')
})

const importantFilterIcon = computed(() => {
  if (filter.value.important === 'ALL') return 'mdi-star-outline'
  if (filter.value.important === false) return 'mdi-star-off'
  return 'mdi-star'
})

const importantFilterTooltip = computed(() => {
  if (filter.value.important === 'ALL') return t('assess.tooltip.filter_all')
  if (filter.value.important === true) return t('assess.tooltip.filter_important')
  return t('assess.tooltip.filter_unimportant')
})

const relevantFilterIcon = computed(() => {
  if (filter.value.relevant === 'ALL') return 'mdi-thumbs-up-down-outline'
  if (filter.value.relevant === false) return 'mdi-thumb-down'
  return 'mdi-thumb-up'
})

const relevantFilterTooltip = computed(() => {
  if (filter.value.relevant === 'ALL') return t('assess.tooltip.filter_all')
  if (filter.value.relevant === true) return t('assess.tooltip.filter_relevant')
  return t('assess.tooltip.filter_irrelevant')
})

const dateSortIcon = computed(() => {
  return filter.value.sort === 'DATE_DESC' ? 'mdi-arrow-down' : 'mdi-arrow-up'
})

const dateSortTooltip = computed(() => {
  return filter.value.sort === 'DATE_DESC'
    ? t('assess.tooltip.sort.date.descending')
    : t('assess.tooltip.sort.date.ascending')
})

// Handle filter updates from base component
const handleFilterUpdate = (updatedFilter) => {
  // Merge the base filter updates with our local filter
  filter.value = { ...filter.value, ...updatedFilter }
  emitFilter()
}

// Cycle through three states: "ALL" -> true -> false -> "ALL"
const cycleFilter = (filterType) => {
  if (filter.value[filterType] === 'ALL') {
    filter.value[filterType] = true
  } else if (filter.value[filterType] === true) {
    filter.value[filterType] = false
  } else {
    filter.value[filterType] = 'ALL'
  }
  emitFilter()
}

const toggleRelevanceSort = () => {
  // Toggle between RELEVANCE_DESC and default DATE_DESC
  if (filter.value.sort === 'RELEVANCE_DESC') {
    filter.value.sort = 'DATE_DESC'
  } else {
    filter.value.sort = 'RELEVANCE_DESC'
  }
  emitFilter()
}

const toggleCompactMode = () => {
  compactMode.value = !compactMode.value
  emitFilter()
}

const toggleHideReviews = () => {
  hideReviews.value = !hideReviews.value
  emitFilter()
}

const toggleHideSourceLinks = () => {
  hideSourceLinks.value = !hideSourceLinks.value
  emitFilter()
}

const toggleHighlightWordlist = () => {
  highlightWordlist.value = !highlightWordlist.value
  emitFilter()
}

const emitFilter = () => {
  emit('update-filter', {
    ...filter.value,
    compact_mode: compactMode.value,
    hide_reviews: hideReviews.value,
    hide_source_links: hideSourceLinks.value,
    highlight_wordlist: highlightWordlist.value
  })
}

const updateDataCount = (count) => {
  totalCount.value = count
}

const updateSelectedCount = (count) => {
  selectedCount.value = count
}

const updateCurrentlyShowingCount = (count) => {
  currentlyShowingCount.value = count
}

const handleUpdateData = () => {
  emit('update-data')
}

// Watch for selection changes
watch(
  () => assessStore.getSelection,
  (newSelection) => {
    selectedCount.value = newSelection.length
  },
  { deep: true }
)

// Expose methods for parent component
defineExpose({
  updateDataCount,
  updateSelectedCount,
  updateCurrentlyShowingCount,
  updateShowingCount: updateCurrentlyShowingCount,
  toolbarGroup
})
</script>
