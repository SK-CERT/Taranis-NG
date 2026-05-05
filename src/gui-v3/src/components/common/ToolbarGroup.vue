<template>
  <div class="toolbar-group">
    <!-- Multi-select toggle button -->
    <v-btn icon size="small" :color="multiSelectActive ? 'primary' : 'default'" @click="toggleMultiSelect">
      <v-tooltip activator="parent" location="bottom">
        {{ t(`${view}.tooltip.toggle_selection`) }}
      </v-tooltip>
      <v-icon>{{ ICONS.MULTISELECT }}</v-icon>
    </v-btn>

    <!-- Divider -->
    <v-divider vertical class="mx-2" />

    <!-- Action Buttons (only visible when multi-select is active) -->
    <template v-if="multiSelectActive">
      <!-- Select All / Unselect All -->
      <v-btn icon size="small" :disabled="false" @click="allSelected ? unselectAll() : selectAll()">
        <v-tooltip activator="parent" location="bottom">
          {{ allSelected ? t(`${view}.tooltip.unselect_all`) : t(`${view}.tooltip.select_all`) }}
        </v-tooltip>
        <v-icon>{{ allSelected ? ICONS.CHECKBOX_BLANK_OUTLINE : ICONS.SELECT_ALL }}</v-icon>
      </v-btn>

      <!-- View-specific action buttons -->
      <template v-if="view === 'assess'">
        <!-- Group -->
        <v-btn v-if="canModify && canGroupActions" icon size="small" :disabled="selectedCount === 0" @click="handleAction('GROUP')">
          <v-tooltip activator="parent" location="bottom">
            {{ t('assess.tooltip.group_items') }}
          </v-tooltip>
          <v-icon>{{ ICONS.GROUP }}</v-icon>
        </v-btn>

        <!-- Ungroup -->
        <v-btn v-if="canModify && canGroupActions" icon size="small" :disabled="selectedCount === 0" @click="handleAction('UNGROUP')">
          <v-tooltip activator="parent" location="bottom">
            {{ t('assess.tooltip.ungroup_items') }}
          </v-tooltip>
          <v-icon>{{ ICONS.UNGROUP }}</v-icon>
        </v-btn>

        <!-- Mark as Read -->
        <v-btn icon size="small" :disabled="selectedCount === 0" @click="handleAction('READ')">
          <v-tooltip activator="parent" location="bottom">
            {{ t('assess.tooltip.read_items') }}
          </v-tooltip>
          <v-icon>{{ ICONS.READ }}</v-icon>
        </v-btn>

        <!-- Mark as Important -->
        <v-btn icon size="small" :disabled="selectedCount === 0" @click="handleAction('IMPORTANT')">
          <v-tooltip activator="parent" location="bottom">
            {{ t('assess.tooltip.important_items') }}
          </v-tooltip>
          <v-icon>{{ ICONS.IMPORTANT }}</v-icon>
        </v-btn>

        <!-- Give a Like -->
        <v-btn icon size="small" :disabled="selectedCount === 0" @click="handleAction('LIKE')">
          <v-tooltip activator="parent" location="bottom">
            {{ t('assess.tooltip.like_items') }}
          </v-tooltip>
          <v-icon>{{ ICONS.LIKE }}</v-icon>
        </v-btn>

        <!-- Give a Dislike -->
        <v-btn icon size="small" :disabled="selectedCount === 0" @click="handleAction('DISLIKE')">
          <v-tooltip activator="parent" location="bottom">
            {{ t('assess.tooltip.dislike_items') }}
          </v-tooltip>
          <v-icon>{{ ICONS.UNLIKE }}</v-icon>
        </v-btn>

        <!-- Analyze (Create Report) -->
        <v-btn v-if="canCreateReport" icon size="small" :disabled="selectedCount === 0" @click="handleAnalyze">
          <v-tooltip activator="parent" location="bottom">
            {{ t('assess.tooltip.analyze_items') }}
          </v-tooltip>
          <v-icon>{{ ICONS.FILE_CHART_OUTLINE }}</v-icon>
        </v-btn>

        <!-- Delete -->
        <v-btn v-if="canDelete" icon size="small" color="error" :disabled="selectedCount === 0" @click="handleAction('DELETE')">
          <v-tooltip activator="parent" location="bottom">
            {{ t('assess.tooltip.delete_items') }}
          </v-tooltip>
          <v-icon>{{ ICONS.DELETE }}</v-icon>
        </v-btn>
      </template>

      <template v-else-if="view === 'analyze'">
        <!-- Publish (Create Product) -->
        <v-btn v-if="canCreateProduct" icon size="small" :disabled="selectedCount === 0" @click="handlePublish">
          <v-tooltip activator="parent" location="bottom">
            {{ t('analyze.tooltip.publish_items') }}
          </v-tooltip>
          <v-icon>{{ ICONS.PUBLISH }}</v-icon>
        </v-btn>

        <!-- Delete -->
        <v-btn v-if="canDelete" icon size="small" color="error" :disabled="selectedCount === 0" @click="handleDelete">
          <v-tooltip activator="parent" location="bottom">
            {{ t('analyze.tooltip.delete_items') }}
          </v-tooltip>
          <v-icon>{{ ICONS.DELETE }}</v-icon>
        </v-btn>
      </template>

      <template v-else-if="view === 'publish'">
        <!-- Delete -->
        <v-btn v-if="canDelete" icon size="small" color="error" :disabled="selectedCount === 0" @click="handleDelete">
          <v-tooltip activator="parent" location="bottom">
            {{ t('publish.tooltip.delete_items') }}
          </v-tooltip>
          <v-icon>{{ ICONS.DELETE }}</v-icon>
        </v-btn>
      </template>
    </template>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ICONS } from '@/config/ui-constants'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAssessStore } from '@/stores/assess'
import { useAnalyzeStore } from '@/stores/analyze'
import { usePublishStore } from '@/stores/publish'
import { useAuth } from '@/composables/useAuth'
import { PERMISSIONS } from '@/services/auth/permissions'
import { groupAction, selectAllNewsItems } from '@/api/assess'
import { getAllReportItemsUnpaginated, deleteReportItem } from '@/api/analyze'
import { getAllProductsUnpaginated, deleteProduct } from '@/api/publish'

const props = defineProps({
  view: {
    type: String,
    required: true,
    validator: (value) => ['assess', 'analyze', 'publish'].includes(value)
  },
  currentFilter: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['update-data'])

const route = useRoute()
const router = useRouter()
const { t } = useI18n()
const { checkPermission } = useAuth()

// Get the appropriate store based on view
const assessStore = props.view === 'assess' ? useAssessStore() : null
const analyzeStore = props.view === 'analyze' ? useAnalyzeStore() : null
const publishStore = props.view === 'publish' ? usePublishStore() : null

const allSelected = ref(false)

// Computed properties based on view
const multiSelectActive = computed(() => {
  if (props.view === 'assess') return assessStore.getMultiSelect
  if (props.view === 'analyze') return analyzeStore.getMultiSelectReport
  return publishStore.getMultiSelect
})

const selectedCount = computed(() => {
  if (props.view === 'assess') return assessStore.getSelection.length
  if (props.view === 'analyze') return analyzeStore.getSelectionReport.length
  return publishStore.getSelection.length
})

// Permission checks
const canModify = computed(() => {
  if (props.view === 'assess') return checkPermission(PERMISSIONS.ASSESS_UPDATE)
  return false
})

const canDelete = computed(() => {
  if (props.view === 'assess') return checkPermission(PERMISSIONS.ASSESS_DELETE)
  if (props.view === 'analyze') return checkPermission(PERMISSIONS.ANALYZE_DELETE)
  if (props.view === 'publish') return checkPermission(PERMISSIONS.PUBLISH_DELETE)
  return false
})

const canCreateReport = computed(() => {
  if (props.view === 'assess') return checkPermission(PERMISSIONS.ANALYZE_CREATE)
  return false
})

const canCreateProduct = computed(() => {
  if (props.view === 'analyze') return checkPermission(PERMISSIONS.PUBLISH_CREATE)
  return false
})

// Disable group actions when the current group is exactly "all"
const canGroupActions = computed(() => {
  if (props.view === 'assess') {
    const groupId = route.params.groupId || 'all'
    return groupId !== 'all'
  }
  return false
})

// Toggle multi-select
const toggleMultiSelect = () => {
  const newState = !multiSelectActive.value

  if (props.view === 'assess') {
    assessStore.multiSelect(newState)
  } else if (props.view === 'analyze') {
    analyzeStore.multiSelectReport(newState)
  } else {
    publishStore.multiSelect(newState)
  }

  // Clear allSelected flag when turning off multi-select
  if (!newState) {
    allSelected.value = false
  }

  window.dispatchEvent(new CustomEvent('multiselect-toggled'))
}

// Select all
const selectAll = async () => {
  if (props.view === 'assess') {
    await selectAllAssess()
  } else if (props.view === 'analyze') {
    await selectAllAnalyze()
  } else {
    await selectAllPublish()
  }
}

const selectAllAssess = async () => {
  const group_id = route.params.groupId || 'all'

  // Use current filter from parent component if available, otherwise use store filter
  const storeFilter = assessStore.getFilter
  const filter = props.currentFilter || {
    search: storeFilter.search || '',
    range: storeFilter.range || 'ALL',
    read: storeFilter.read !== undefined ? storeFilter.read : 'ALL',
    important: storeFilter.important || 'ALL',
    relevant: storeFilter.relevant || 'ALL',
    sort: storeFilter.sort || 'DATE_DESC'
  }

  console.log('[ToolbarGroup] Select all assess - group_id:', group_id, 'filter:', filter)

  // Show loading notification
  window.dispatchEvent(
    new CustomEvent('notification', {
      detail: {
        id: 'select-all-progress',
        type: 'info',
        message: 'Fetching all items...',
        persistent: true,
        timeout: 0
      }
    })
  )

  try {
    const response = await selectAllNewsItems({
      group_id,
      data: { filter }
    })

    console.log('[ToolbarGroup] Select all response:', response)

    if (response?.data?.items) {
      console.log('[ToolbarGroup] Selecting', response.data.items.length, 'items')
      response.data.items.forEach((item) => {
        assessStore.select({
          type: 'AGGREGATE',
          id: item.id,
          item: item
        })
      })
      allSelected.value = true
      window.dispatchEvent(
        new CustomEvent('notification', {
          detail: {
            id: 'select-all-progress',
            type: 'success',
            loc: 'assess.select_all_success',
            params: { count: response.data.items.length },
            timeout: 2000
          }
        })
      )
      window.dispatchEvent(new CustomEvent('sync-assess-selection'))
    } else {
      console.warn('[ToolbarGroup] No items in response:', response)
      window.dispatchEvent(
        new CustomEvent('notification', {
          detail: { type: 'warning', message: 'No items to select' }
        })
      )
    }
  } catch (error) {
    console.error('[ToolbarGroup] Error selecting all:', error)
    window.dispatchEvent(
      new CustomEvent('notification', {
        detail: { type: 'error', loc: 'error.select_all_failed' }
      })
    )
  }
}

const selectAllAnalyze = async () => {
  const group = analyzeStore.getCurrentReportItemGroup
  // Use current filter from parent component if available, otherwise use defaults
  const filter = props.currentFilter || {
    search: '',
    range: 'ALL',
    incompleted: true,
    sort: 'DATE_DESC'
  }

  console.log('[ToolbarGroup] Select all analyze - group:', group, 'filter:', filter)

  // Show loading notification
  window.dispatchEvent(
    new CustomEvent('notification', {
      detail: {
        id: 'select-all-progress',
        type: 'info',
        message: 'Fetching all items...',
        persistent: true,
        timeout: 0
      }
    })
  )

  try {
    const response = await getAllReportItemsUnpaginated({
      group,
      filter
    })

    console.log('[ToolbarGroup] Select all analyze response:', response)
    console.log('[ToolbarGroup] Items in response:', response?.data?.items?.length)

    if (response?.data?.items) {
      console.log('[ToolbarGroup] Selecting', response.data.items.length, 'analyze items')
      response.data.items.forEach((item) => {
        analyzeStore.selectReport({
          id: item.id,
          item: item
        })
      })
      allSelected.value = true
      window.dispatchEvent(
        new CustomEvent('notification', {
          detail: {
            id: 'select-all-progress',
            type: 'success',
            loc: 'analyze.select_all_success',
            params: { count: response.data.items.length },
            timeout: 2000
          }
        })
      )
      window.dispatchEvent(new CustomEvent('sync-analyze-selection'))
    } else {
      console.warn('[ToolbarGroup] No items in analyze response:', response)
    }
  } catch (error) {
    console.error('[ToolbarGroup] Error selecting all analyze items:', error)
    window.dispatchEvent(
      new CustomEvent('notification', {
        detail: { type: 'error', loc: 'error.select_all_failed' }
      })
    )
  }
}

const selectAllPublish = async () => {
  // Use current filter from parent component if available, otherwise use defaults
  const filter = props.currentFilter || {
    search: '',
    range: 'ALL',
    published: false,
    unpublished: true,
    sort: 'DATE_DESC'
  }

  console.log('[ToolbarGroup] Select all publish - filter:', filter)

  // Show loading notification
  window.dispatchEvent(
    new CustomEvent('notification', {
      detail: {
        id: 'select-all-progress',
        type: 'info',
        message: 'Fetching all items...',
        persistent: true,
        timeout: 0
      }
    })
  )

  try {
    const response = await getAllProductsUnpaginated({ filter })

    console.log('[ToolbarGroup] Select all publish response:', response)
    console.log('[ToolbarGroup] Items in response:', response?.data?.items?.length)

    if (response?.data?.items) {
      console.log('[ToolbarGroup] Selecting', response.data.items.length, 'publish items')
      response.data.items.forEach((item) => {
        publishStore.select({
          id: item.id,
          item: item
        })
      })
      allSelected.value = true
      window.dispatchEvent(
        new CustomEvent('notification', {
          detail: {
            id: 'select-all-progress',
            type: 'success',
            loc: 'publish.select_all_success',
            params: { count: response.data.items.length },
            timeout: 2000
          }
        })
      )
      window.dispatchEvent(new CustomEvent('sync-publish-selection'))
    } else {
      console.warn('[ToolbarGroup] No items in publish response:', response)
    }
  } catch (error) {
    console.error('[ToolbarGroup] Error selecting all publish items:', error)
    window.dispatchEvent(
      new CustomEvent('notification', {
        detail: { type: 'error', loc: 'error.select_all_failed' }
      })
    )
  }
}

// Unselect all
const unselectAll = () => {
  allSelected.value = false

  if (props.view === 'assess') {
    assessStore.selection = []
    window.dispatchEvent(new CustomEvent('sync-assess-selection'))
  } else if (props.view === 'analyze') {
    analyzeStore.selection_report = []
    window.dispatchEvent(new CustomEvent('sync-analyze-selection'))
  } else {
    publishStore.selection = []
    window.dispatchEvent(new CustomEvent('sync-publish-selection'))
  }
}

// Assess-specific actions
const handleAnalyze = () => {
  const selection = assessStore.getSelection
  const items = selection.filter((s) => s.type === 'news_item_aggregate').map((s) => s.item)

  if (items.length > 0) {
    assessStore.multiSelect(false)
    window.dispatchEvent(new CustomEvent('multiselect-toggled'))
    window.dispatchEvent(new CustomEvent('new-report', { detail: items }))
  }
}

const handleAction = async (type) => {
  const selection = assessStore.getSelection
  const items = selection.map((s) => ({ type: s.type, id: s.id }))

  if (items.length > 0) {
    const group_id = route.params.groupId || null

    // Show progress notification
    window.dispatchEvent(
      new CustomEvent('notification', {
        detail: {
          id: 'assess-action-progress',
          type: 'info',
          message: `Processing ${items.length} item(s)...`,
          persistent: true,
          timeout: 0
        }
      })
    )

    try {
      await groupAction({ group: group_id, action: type, items })

      toggleMultiSelect()

      window.dispatchEvent(
        new CustomEvent('notification', {
          detail: {
            id: 'assess-action-progress',
            type: 'success',
            loc: 'common.action_completed',
            timeout: 2000
          }
        })
      )

      emit('update-data')
    } catch (error) {
      console.error('Error performing action:', error)
      window.dispatchEvent(
        new CustomEvent('notification', {
          detail: { type: 'error', loc: `error.${error.response?.data || 'server_error'}` }
        })
      )
    }
  }
}

// Analyze-specific actions
const handlePublish = () => {
  const selection = analyzeStore.getSelectionReport
  const items = selection.map((s) => s.item)

  if (items.length > 0) {
    publishStore.pendingNewProduct = items
    analyzeStore.multiSelectReport(false)
    window.dispatchEvent(new CustomEvent('multiselect-toggled'))
    router.push('/publish')
  }
}

// Delete action (used by analyze and publish)
const handleDelete = async () => {
  if (props.view === 'analyze') {
    const selection = analyzeStore.getSelectionReport

    if (selection.length > 0) {
      // Show progress notification
      window.dispatchEvent(
        new CustomEvent('notification', {
          detail: {
            id: 'analyze-delete-progress',
            type: 'info',
            message: `Deleting ${selection.length} item(s)...`,
            persistent: true,
            timeout: 0
          }
        })
      )

      try {
        const deletePromises = selection.map((s) => deleteReportItem({ id: s.id }))

        await Promise.all(deletePromises)

        toggleMultiSelect()

        window.dispatchEvent(
          new CustomEvent('notification', {
            detail: {
              id: 'analyze-delete-progress',
              type: 'success',
              loc: 'common.deleted_successfully',
              timeout: 2000
            }
          })
        )

        emit('update-data')
      } catch (error) {
        console.error('Error deleting items:', error)
        window.dispatchEvent(
          new CustomEvent('notification', {
            detail: { type: 'error', loc: `error.${error.response?.data || 'server_error'}` }
          })
        )
      }
    }
  } else if (props.view === 'publish') {
    const selection = publishStore.getSelection

    if (selection.length > 0) {
      // Show progress notification
      window.dispatchEvent(
        new CustomEvent('notification', {
          detail: {
            id: 'publish-delete-progress',
            type: 'info',
            message: `Deleting ${selection.length} item(s)...`,
            persistent: true,
            timeout: 0
          }
        })
      )

      try {
        const deletePromises = selection.map((s) => deleteProduct(s.item))

        await Promise.all(deletePromises)

        toggleMultiSelect()

        window.dispatchEvent(
          new CustomEvent('notification', {
            detail: {
              id: 'publish-delete-progress',
              type: 'success',
              loc: 'common.deleted_successfully',
              timeout: 2000
            }
          })
        )

        emit('update-data')
      } catch (error) {
        console.error('Error deleting items:', error)
        window.dispatchEvent(
          new CustomEvent('notification', {
            detail: { type: 'error', loc: `error.${error.response?.data || 'server_error'}` }
          })
        )
      }
    }
  }
}

defineExpose({
  disableMultiSelect: () => {
    if (multiSelectActive.value) {
      toggleMultiSelect()
    }
  }
})
</script>

<style scoped>
.toolbar-group {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
}
</style>
