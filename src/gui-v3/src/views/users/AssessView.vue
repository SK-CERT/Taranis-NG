<template>
  <ViewLayout>
    <template #panel>
      <ToolbarFilterAssess
        ref="toolbarFilter"
        title="nav_menu.newsitems"
        total_count_title="toolbar_filter.total_count"
        selected_count_title="toolbar_filter.selected_count"
        :show-add-button="hasManualSources"
        @update-filter="updateFilter"
        @update-data="updateData"
        @add-new="showAddNewsItemDialog = true"
      />
    </template>

    <template #content>
      <ContentDataAssess
        ref="contentData"
        card-item="CardAssess"
        self-i-d="selector_assess"
        data_set="assess"
        :analyze_selector="analyze_selector"
        :selection="assessStore.getSelection"
        @new-data-loaded="newDataLoaded"
        @card-items-reindex="cardReindex"
        @update-showing-count="updateShowingCount"
      />
    </template>
  </ViewLayout>

  <!-- Add News Item Dialog -->
  <AddNewsItemDialog
    v-model="showAddNewsItemDialog"
    :manual-sources="assessStore.getManualOSINTSourcesList"
    @news-item-added="handleNewsItemAdded"
  />
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAssessStore } from '@/stores/assess'
import ViewLayout from '@/components/layouts/ViewLayout.vue'
import ToolbarFilterAssess from '@/components/assess/ToolbarFilterAssess.vue'
import ContentDataAssess from '@/components/assess/ContentDataAssess.vue'
import AddNewsItemDialog from '@/components/assess/AddNewsItemDialog.vue'

const props = defineProps({
  analyze_selector: {
    type: Boolean,
    default: false
  }
})

const route = useRoute()
const assessStore = useAssessStore()
const { t } = useI18n()

const toolbarFilter = ref(null)
const contentData = ref(null)
const showAddNewsItemDialog = ref(false)

// Computed property to check if manual sources exist
const hasManualSources = computed(
  () => assessStore.getManualOSINTSourcesList && assessStore.getManualOSINTSourcesList.length > 0
)

const newDataLoaded = (count) => {
  if (toolbarFilter.value) {
    toolbarFilter.value.updateDataCount(count)
  }
}

const updateFilter = (filter) => {
  if (contentData.value) {
    contentData.value.updateFilter(filter)
    assessStore.setFilter(filter)
  }
}

const updateData = () => {
  if (contentData.value) {
    contentData.value.updateData(false, true)
  }
}

const cardReindex = () => {
  // Handle card reindexing (for keyboard navigation in future enhancement)
}

const updateShowingCount = (count) => {
  if (toolbarFilter.value) {
    toolbarFilter.value.updateCurrentlyShowingCount(count)
  }
}

const handleNewsItemAdded = () => {
  // Refresh the data when a new news item is added
  updateData()
}

// Handle route changes
const handleRouteChange = () => {
  if (contentData.value) {
    contentData.value.updateData(false, false)
  }
}

onMounted(() => {
  // Load manual OSINT sources to show "Add New" button (non-blocking)
  assessStore.loadManualOSINTSources().catch((error) => {
    console.error('Error loading manual OSINT sources:', error)
  })

  if (route.path.includes('/group/')) {
    handleRouteChange()
  }
})
</script>
