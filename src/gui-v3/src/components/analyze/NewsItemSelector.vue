<template>
  <v-container>
    <!-- Dialog Container -->
    <v-dialog
      v-model="selectorOpen"
      fullscreen
      persistent
    >
      <v-card flat class="selector-layout">
        <!-- Fixed Toolbar -->
        <v-toolbar color="primary" dark>
          <v-btn icon @click="handleClose">
            <v-icon>mdi-close-circle</v-icon>
          </v-btn>
          <v-toolbar-title>{{ t('assess.attached_news_items') }}</v-toolbar-title>
          <v-spacer />
          <v-btn @click="handleAdd">
            <v-icon start>mdi-plus-box</v-icon>
            {{ t('common.add_items') }}
          </v-btn>
        </v-toolbar>

        <!-- Main Content Row -->
        <div class="selector-body">
          <!-- Left Sidebar: Groups -->
          <div class="bg-surface selector-sidebar">
            <v-list
              v-model:selected="selectedGroupList"
              density="compact"
              nav
            >
              <v-list-item
                v-for="link in groups"
                :key="link.id"
                :value="link.id"
                class="px-1"
                @click="changeGroup(link.id)"
              >
                <template #prepend>
                  <v-icon :color="link.color || 'default'">{{ link.icon }}</v-icon>
                </template>
                <v-list-item-title class="text-caption" style="white-space: break-spaces">
                  {{ link.translate ? t(link.title) : link.title }}
                </v-list-item-title>
              </v-list-item>
            </v-list>
          </div>

          <!-- Right Content Area: Toolbar + Items -->
          <div class="selector-main">
            <!-- Toolbar Filter -->
            <div class="bg-surface pa-3 selector-filter">
              <ToolbarFilterAssess
                ref="toolbarFilter"
                :analyze_selector="true"
                :total-count-title="'assess.total_count'"
                @update-filter="handleFilterUpdate"
              />
            </div>

            <div class="selector-results">
              <!-- Content Data -->
              <ContentDataAssess
                ref="contentData"
                :analyze_selector="true"
                :selection="selectedItems"
                class="item-selector"
                :self-i-d="'selector_assess_analyze'"
                :data_set="'assess_news_item'"
                @new-data-loaded="handleNewDataLoaded"
                @update-showing-count="handleUpdateShowingCount"
                @card-items-reindex="handleCardItemsReindex"
              />
            </div>
          </div>
        </div>
      </v-card>
    </v-dialog>

    <!-- Selected Items Display (outside dialog) -->
    <v-container v-if="!selectorOpen" fluid>
      <v-row>
        <v-col
          v-for="item in value"
          :key="item.id"
          cols="12"
        >
          <BaseCard
            :multi-select-active="false"
            :show-selection-checkbox="false"
            :preselected="false"
            card-class="card-item"
          >
            <!-- Content Slot -->
            <template #content>
              <div class="d-flex align-center" style="gap: 12px">
                <!-- News Item Content -->
                <div class="flex-grow-1">
                  <!-- Source and Date Info -->
                  <div class="text-caption text-grey mb-2">
                    <v-row align="center" no-gutters>
                      <v-col cols="auto">
                        <span v-if="item.news_items && item.news_items.length > 0">
                          <strong>{{ t('card_item.source') }}:</strong>
                          {{
                            item.news_items[0].news_item_data?.osint_source_name ||
                              item.news_items[0].news_item_data?.source ||
                              'Unknown'
                          }}
                        </span>
                      </v-col>
                      <v-spacer />
                      <v-col cols="auto">
                        <span v-if="item.news_items && item.news_items.length > 0">
                          <strong>{{ t('card_item.published') }}:</strong>
                          {{ item.news_items[0].news_item_data?.published || 'N/A' }}
                        </span>
                      </v-col>
                    </v-row>
                  </div>
                  <div class="text-h6 font-weight-medium mb-2">
                    {{ item.title }}
                  </div>
                  <div class="text-body-2 mb-3">
                    {{ item.description }}
                  </div>
                </div>

                <!-- Remove Button on the Right, Centered -->
                <v-btn
                  size="small"
                  variant="text"
                  :title="t('common.remove')"
                  style="flex-shrink: 0"
                  @click.stop="handleRemoveItem(item)"
                >
                  <v-icon :color="'error'">{{ ICONS.REMOVE }}</v-icon>
                </v-btn>
              </div>
            </template>
          </BaseCard>
        </v-col>
      </v-row>
    </v-container>

    <!-- Confirmation Dialog: Remove Item -->
    <v-dialog v-model="showRemoveConfirm" max-width="500">
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon color="primary" class="mr-2">mdi-help-circle</v-icon>
          {{ t('common.messagebox.remove') }}
        </v-card-title>
        <v-card-text>
          {{ itemToDelete?.title }}
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="showRemoveConfirm = false">
            {{ t('common.cancel') }}
          </v-btn>
          <v-btn color="primary" variant="text" @click="confirmRemoveItem">
            {{ t('common.remove') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup>
import { ref, computed, nextTick, onMounted, onUnmounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAssessStore } from '@/stores/assess'
import { useAuth } from '@/composables/useAuth'
import { PERMISSIONS } from '@/services/auth/permissions'
import { updateReportItem, getReportItemData } from '@/api/analyze'
import { ICONS } from '@/config/ui-constants'
import ToolbarFilterAssess from '@/components/assess/ToolbarFilterAssess.vue'
import ContentDataAssess from '@/components/assess/ContentDataAssess.vue'
import BaseCard from '@/components/common/BaseCard.vue'

const props = defineProps({
  values: {
    type: Array,
    default: () => []
  },
  reportItemId: {
    type: Number,
    required: false
  },
  edit: {
    type: Boolean,
    default: false
  },
  modify: {
    type: Boolean,
    default: true
  },
  attach: {
    type: [String, Object],
    default: undefined
  },
  verticalView: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:modelValue', 'items-changed'])

const { t } = useI18n()
const assessStore = useAssessStore()
const { checkPermission, getUserId } = useAuth()

// Refs
const toolbarFilter = ref(null)
const contentData = ref(null)

// Reactive state
const selectorOpen = ref(false)
const value = ref(props.values || [])
const selectedItems = ref(props.values || [])
const groups = ref([])
const selectedGroupId = ref(null)
const selectedGroupList = ref([])
const showRemoveConfirm = ref(false)
const itemToDelete = ref(null)

watch(
  () => props.values,
  (newValues) => {
    const normalized = Array.isArray(newValues) ? [...newValues] : []
    value.value = normalized
    selectedItems.value = normalized
  },
  { deep: true, immediate: true }
)

// Computed
const canModify = computed(() => {
  return props.edit === false || (checkPermission(PERMISSIONS.ANALYZE_UPDATE) && props.modify === true)
})

// Methods
const changeGroup = async (groupId) => {
  selectedGroupId.value = groupId
  assessStore.changeCurrentGroup(groupId)
  if (contentData.value) {
    contentData.value.updateData?.(false, false)
  }
}

const openSelector = async () => {
  // Initialize selected group
  selectedGroupId.value = selectedGroupId.value || groups.value[0]?.id || 'all'

  // Ensure the store has a current group set so ContentDataAssess can build the API URL
  assessStore.changeCurrentGroup(selectedGroupId.value)

  // Clear previous selections
  assessStore.multiSelect(false)
  window.dispatchEvent(new CustomEvent('multi-select-off'))

  // Enable multi-select for this session
  assessStore.multiSelect(true)

  selectorOpen.value = true

  await nextTick()

  for (const item of value.value) {
    if (item?.id) {
      assessStore.select({ type: 'news_item_aggregate', id: item.id, item })
    }
  }

  if (toolbarFilter.value) {
    toolbarFilter.value.updateSelectedCount?.(value.value.length)
  }
}

const handleAdd = async () => {
  try {
    const selection = assessStore.getSelection || []
    const addedValues = []
    const aggregateIds = []

    // Find selected aggregate items that aren't already in values
    for (const selItem of selection) {
      const isAggregateType =
        selItem?.type === 'AGGREGATE' ||
        selItem?.type === 'news_item_aggregate'

      const item = selItem?.item
      if (isAggregateType && item?.id) {
        const found = value.value.some((v) => v.id === item.id)
        if (!found) {
          addedValues.push(item)
          aggregateIds.push(item.id)
        }
      }
    }

    // If editing with a valid report item ID, make API call
    if (props.edit === true && props.reportItemId && props.reportItemId > 0) {
      const data = {
        add: true,
        report_item_id: props.reportItemId,
        aggregate_ids: aggregateIds
      }

      await updateReportItem(props.reportItemId, data)

      // Update counts and add to values
      for (const item of addedValues) {
        item.in_reports_count = (item.in_reports_count || 0) + 1
        value.value.push(item)
      }
    } else {
      // Just update locally (for pre-save or read-only)
      for (const item of addedValues) {
        item.in_reports_count = (item.in_reports_count || 0) + 1
        value.value.push(item)
      }
    }

    // Deselect and close
    assessStore.multiSelect(false)
    selectorOpen.value = false

    // Emit event for parent
    emit('items-changed', value.value)
  } catch (error) {
    console.error('Error adding items to report:', error)
    window.dispatchEvent(
      new CustomEvent('notification', {
        detail: { type: 'error', message: t('error.server_error') }
      })
    )
  }
}

const handleClose = () => {
  assessStore.multiSelect(false)
  selectorOpen.value = false
}

const handleNewDataLoaded = (count) => {
  if (toolbarFilter.value) {
    toolbarFilter.value.updateDataCount?.(count)
  }
}

const handleUpdateShowingCount = (count) => {
  if (toolbarFilter.value) {
    toolbarFilter.value.updateCurrentlyShowingCount?.(count)
  }
}

const handleCardItemsReindex = () => {
  // Handle reindexing if needed
}

const handleFilterUpdate = (filter) => {
  if (contentData.value) {
    contentData.value.updateFilter?.(filter)
  }
}

const handleRemoveItem = (item) => {
  // Check permissions before allowing removal
  if (!canModify.value) {
    window.dispatchEvent(
      new CustomEvent('notification', {
        detail: { type: 'warning', message: t('common.no_permission') }
      })
    )
    return
  }
  itemToDelete.value = item
  showRemoveConfirm.value = true
}

const handleUpdateItem = (_item) => {
  // Handle item updates if needed
}

const confirmRemoveItem = async () => {
  if (!itemToDelete.value) return

  try {
    const data = {
      delete: true,
      aggregate_id: itemToDelete.value.id
    }

    if (props.edit === true && props.reportItemId && props.reportItemId > 0) {
      await updateReportItem(props.reportItemId, data)
    }

    // Remove from array
    const index = value.value.indexOf(itemToDelete.value)
    if (index > -1) {
      value.value.splice(index, 1)
    }

    showRemoveConfirm.value = false
    itemToDelete.value = null

    // Emit event for parent
    emit('items-changed', value.value)
  } catch (error) {
    console.error('Error removing item from report:', error)
    window.dispatchEvent(
      new CustomEvent('notification', {
        detail: { type: 'error', message: t('error.server_error') }
      })
    )
  }
}

const handleReportItemUpdated = (dataInfo) => {
  if (props.edit === true && props.reportItemId && props.reportItemId > 0 && props.reportItemId === dataInfo.report_item_id) {
    const currentUserId = getUserId()
    if (dataInfo.user_id !== currentUserId) {
      if (dataInfo.add !== undefined) {
        getReportItemData(props.reportItemId, dataInfo).then((response) => {
          const data = response.data
          if (data.news_item_aggregates) {
            value.value.push(...data.news_item_aggregates)
            emit('items-changed', value.value)
          }
        })
      } else if (dataInfo.delete !== undefined) {
        value.value = value.value.filter((item) => item.id !== dataInfo.aggregate_id)
        emit('items-changed', value.value)
      }
    }
  }
}

const handleReportItemUpdatedEvent = (event) => {
  handleReportItemUpdated(event.detail)
}

// Lifecycle
onMounted(async () => {
  // Load groups (OSINT sources for Assess)
  // TODO: Load from store or API
  groups.value = [
    { id: 'all', title: 'All', icon: 'mdi-folder', color: undefined, translate: false },
    { id: 'unread', title: 'assess.unread', icon: 'mdi-email-multiple', color: 'primary', translate: true }
  ]

  selectedGroupId.value = groups.value[0].id

  // Listen for report item updates
  window.addEventListener('report-item-updated', handleReportItemUpdatedEvent)
})

onUnmounted(() => {
  window.removeEventListener('report-item-updated', handleReportItemUpdatedEvent)
})

// Expose methods for external use
defineExpose({
  openSelector
})
</script>

<style scoped>
.item-selector {
  cursor: pointer;
}

.selector-layout {
  height: 100vh;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  overflow: hidden;
}

.selector-body {
  min-height: 0;
  display: grid;
  grid-template-columns: 96px minmax(0, 1fr);
  overflow: hidden;
}

.selector-sidebar {
  border-right: 1px solid rgba(0, 0, 0, 0.12);
  overflow: hidden;
}

.selector-main {
  min-width: 0;
  min-height: 0;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  overflow: hidden;
}

.selector-filter {
  border-bottom: 1px solid rgba(0, 0, 0, 0.12);
}

.selector-results {
  min-height: 0;
  overflow-y: auto;
}
</style>
