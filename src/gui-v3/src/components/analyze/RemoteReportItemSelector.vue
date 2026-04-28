<template>
  <v-container>
    <!-- Activate Button -->
    <v-btn
      v-if="canModify && groups.length > 0"
      variant="elevated"
      size="small"
      class="mb-4"
      @click="openSelector"
    >
      <v-icon start>mdi-plus</v-icon>
      {{ t('report_item.select_remote') }}
    </v-btn>

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
            <v-icon>mdi-close-circle</v-icon>
          </v-btn>
          <v-toolbar-title>{{ t('report_item.select_remote') }}</v-toolbar-title>
          <v-spacer />
          <v-btn @click="handleAdd">
            <v-icon start>mdi-plus-box</v-icon>
            {{ t('common.add') }}
          </v-btn>
        </v-toolbar>

        <!-- Main Content Row -->
        <v-row no-gutters class="mt-12">
          <!-- Left Sidebar: Groups -->
          <v-col
            cols="auto"
            class="bg-surface pa-0"
            style="max-width: 96px; min-height: calc(100vh - 64px); border-right: 1px solid rgba(0, 0, 0, 0.12); overflow-y: auto"
          >
            <v-list
              v-model:selected="selectedGroupList"
              density="compact"
              nav
            >
              <v-list-item
                v-for="link in links"
                :key="link.id"
                :value="link.id"
                class="px-1"
                @click="changeGroup(link.id)"
              >
                <template #prepend>
                  <v-icon>{{ link.icon }}</v-icon>
                </template>
                <v-list-item-title class="text-caption" style="white-space: break-spaces">
                  {{ link.title }}
                </v-list-item-title>
              </v-list-item>
            </v-list>
          </v-col>

          <!-- Main content: Filter toolbar + ContentDataAnalyze -->
          <v-col class="flex-grow-1 pa-0">
            <div class="bg-surface pa-3" style="position: sticky; top: 0; z-index: 100">
              <ToolbarFilterAnalyze
                ref="toolbarFilter"
                :show-group-toolbar="false"
                @update-filter="updateFilter"
              />
            </div>
            <ContentDataAnalyze
              ref="contentData"
              :show-remove-action="false"
              :remote-reports="true"
              card-item="CardAnalyze"
              @show-remote-report-item-detail="showReportItemDetail"
              @new-data-loaded="handleNewDataLoaded"
            />
          </v-col>
        </v-row>
      </v-card>
    </v-dialog>

    <!-- Remote Report Item Dialog -->
    <RemoteReportItem ref="remoteReportItemDialog" />

    <!-- Selected Items Display -->
    <div v-if="!selectorOpen" class="selected-items-container ml-4">
      <v-spacer style="height: 8px" />
      <CardAnalyze
        v-for="item in value"
        :key="item.id"
        :card="item"
        :show-remove-action="true"
        @show-remote-report-item-detail="showReportItemDetail"
        @remove-report-item-from-selector="removeReportItem"
      />
    </div>
  </v-container>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import ContentDataAnalyze from '@/components/analyze/ContentDataAnalyze.vue'
import ToolbarFilterAnalyze from '@/components/analyze/ToolbarFilterAnalyze.vue'
import CardAnalyze from '@/components/analyze/CardAnalyze.vue'
import RemoteReportItem from '@/components/analyze/RemoteReportItem.vue'
import { useAnalyzeStore } from '@/stores/analyze'
import { useAuth } from '@/composables/useAuth'
import { updateReportItem, getReportItemData } from '@/api/analyze'
import { PERMISSIONS } from '@/services/auth/permissions'

const { t } = useI18n()
const { checkPermission, getUserId } = useAuth()
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
  },
  reportItemId: {
    type: Number,
    default: null
  }
})

const emit = defineEmits(['remote-report-items-changed'])

const selectorOpen = ref(false)
const value = ref(props.values || [])
const groups = ref([])
const links = ref([])
const selectedGroupId = ref(null)
const selectedGroupList = ref([])
const toolbarFilter = ref(null)
const contentData = ref(null)
const remoteReportItemDialog = ref(null)

const canModify = computed(() => {
  if (!props.edit) return true
  return checkPermission(PERMISSIONS.ANALYZE_UPDATE) && props.modify
})

const loadGroups = async () => {
  try {
    await analyzeStore.loadReportItemGroups({ search: '' })
    const allGroups = analyzeStore.getReportItemGroups
    groups.value = allGroups || []

    links.value = groups.value.map((group) => ({
      icon: 'mdi-arrow-down-bold-circle-outline',
      title: group,
      id: group
    }))

    // Set initial group
    if (links.value.length > 0) {
      const currentGroup = analyzeStore.currentReportItemGroup
      if (currentGroup) {
        selectedGroupId.value = currentGroup
      } else {
        selectedGroupId.value = links.value[0].id
        await analyzeStore.changeCurrentReportItemGroup(selectedGroupId.value)
      }
      selectedGroupList.value = [selectedGroupId.value]
    }
  } catch (_error) {
    window.dispatchEvent(new CustomEvent('notification', {
      detail: { type: 'error', message: t('error.load_groups') }
    }))
  }
}

const changeGroup = async (groupId) => {
  selectedGroupId.value = groupId
  selectedGroupList.value = [groupId]
  await analyzeStore.changeCurrentReportItemGroup(groupId)
  if (contentData.value) {
    contentData.value.updateData(false, false)
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

const showReportItemDetail = (reportItem) => {
  if (remoteReportItemDialog.value) {
    remoteReportItemDialog.value.showDetail(reportItem)
  }
}

const handleAdd = async () => {
  const selection = analyzeStore.selectionReport
  const addedValues = []
  const data = {
    add: true,
    report_item_id: props.reportItemId,
    remote_report_item_ids: []
  }

  selection.forEach((selectedItem) => {
    const found = value.value.some((item) => item.id === selectedItem.item.id)
    if (!found) {
      addedValues.push(selectedItem.item)
      data.remote_report_item_ids.push(selectedItem.item.id)
    }
  })

  if (props.edit && props.reportItemId && props.reportItemId > 0) {
    try {
      await updateReportItem(props.reportItemId, data)
      value.value.push(...addedValues)
    } catch (_error) {
      window.dispatchEvent(new CustomEvent('notification', {
        detail: { type: 'error', message: t('error.save_failed') }
      }))
      return
    }
  } else {
    value.value.push(...addedValues)
  }

  emit('remote-report-items-changed', null)
  handleClose()
}

const removeReportItem = async (reportItem) => {
  const data = {
    delete: true,
    remote_report_item_id: reportItem.id
  }

  if (props.edit && props.reportItemId && props.reportItemId > 0) {
    try {
      await updateReportItem(props.reportItemId, data)
      const index = value.value.findIndex((item) => item.id === reportItem.id)
      if (index > -1) {
        value.value.splice(index, 1)
      }
    } catch (_error) {
      window.dispatchEvent(new CustomEvent('notification', {
        detail: { type: 'error', message: t('error.delete_failed') }
      }))
      return
    }
  } else {
    const index = value.value.findIndex((item) => item.id === reportItem.id)
    if (index > -1) {
      value.value.splice(index, 1)
    }
  }

  emit('remote-report-items-changed', null)
}

const openSelector = () => {
  analyzeStore.multiSelectReport(true)
  selectorOpen.value = true
  if (contentData.value) {
    contentData.value.updateData(false, false)
  }
}

const handleClose = () => {
  analyzeStore.multiSelectReport(false)
  selectorOpen.value = false
}

const handleReportItemUpdated = async (dataInfo) => {
  if (!props.edit || !props.reportItemId || props.reportItemId <= 0 || props.reportItemId !== dataInfo.report_item_id) return
  if (dataInfo.user_id === getUserId()) return

  try {
    if (dataInfo.add !== undefined) {
      const response = await getReportItemData(props.reportItemId, dataInfo)
      if (response?.data?.remote_report_items) {
        value.value.push(...response.data.remote_report_items)
      }
    } else if (dataInfo.delete !== undefined) {
      const index = value.value.findIndex((item) => item.id === dataInfo.remote_report_item_id)
      if (index > -1) {
        value.value.splice(index, 1)
      }
    }

    emit('remote-report-items-changed', null)
  } catch (_error) {
    // Silent error handling for SSE updates
  }
}

const handleReportItemUpdatedEvent = (event) => {
  handleReportItemUpdated(event.detail)
}

onMounted(async () => {
  await loadGroups()
  window.addEventListener('report-item-updated', handleReportItemUpdatedEvent)
})

onUnmounted(() => {
  window.removeEventListener('report-item-updated', handleReportItemUpdatedEvent)
})

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
