<template>
  <div>
    <BaseCard
      :multi-select-active="multiSelectActive"
      :show-selection-checkbox="true"
      :preselected="preselected"
      :checkbox-label="t('analyze.select')"
      :card-class="'card-item'"
      :card-color="selectedColor"
      @card-click="cardItemClick"
      @selection-change="selectionChanged"
    >
      <!-- Content Slot -->
      <template #content>
        <!-- Header Row: Icon+Type, State, Updated Info, Actions -->
        <div class="mb-2">
          <v-row align="center" no-gutters class="ga-2">
            <!-- Icon + Type Name (tight together using inline-flex) -->
            <v-col shrink class="d-inline-flex align-center" style="gap: 4px;">
              <v-icon size="large" :icon="card.tag || ICONS.FILE_DOCUMENT" />
              <span class="text-caption text-medium-emphasis">{{ card.report_type_name }}</span>
            </v-col>
            <!-- Spacer to push state/updated/actions to the right -->
            <v-spacer />
            <!-- State -->
            <v-col
              v-if="card.state"
              shrink
              class="d-flex align-center"
              style="gap: 3px; padding: 0;"
            >
              <v-icon :color="card.state.color" size="small">{{ card.state.icon }}</v-icon>
              <span class="text-caption">{{ t('workflow.states.' + card.state.display_name, card.state.display_name) }}</span>
            </v-col>
            <!-- Updated Info -->
            <v-col shrink class="d-flex flex-column justify-center" style="gap: 0; padding: 0; margin-left: 8px;">
              <div class="text-caption text-medium-emphasis">{{ t('card_item.updated') }}</div>
              <div class="text-body-2">
                {{ card.last_updated }}
                <span v-if="card.updated_by" class="text-medium-emphasis">&nbsp;&nbsp;{{ card.updated_by }}</span>
              </div>
            </v-col>
            <!-- Actions - flat buttons without circles -->
            <v-col
              v-if="!disableActions"
              shrink
              class="d-flex align-center"
              style="gap: 0; padding: 0; margin-left: 4px;"
            >
              <!-- Publish -->
              <ActionButton
                v-if="canCreateProduct && !showRemoveAction"
                action="publish"
                size="x-small"
                :title="t('analyze.tooltip.publish_item')"
                @click.stop="handlePublish"
              />
              <!-- Delete -->
              <ActionButton
                v-if="canDelete && !showRemoveAction"
                action="delete"
                size="x-small"
                :title="t('analyze.tooltip.delete_item')"
                @click.stop="showDeleteDialog = true"
              />
              <!-- Remove from Group -->
              <ActionButton
                v-if="canModify && showRemoveAction"
                action="remove"
                size="x-small"
                :title="t('analyze.tooltip.remove_item')"
                @click.stop="showRemoveDialog = true"
              />
            </v-col>
          </v-row>
          <!-- Title Row -->
          <v-row no-gutters class="mt-2">
            <v-col>
              <div class="text-body-1 font-weight-medium">
                <span v-if="card.title_prefix">{{ card.title_prefix }} -</span>
                {{ card.title }}
                <span v-if="card.news_items_count" class="text-medium-emphasis">
                  &nbsp;({{ card.news_items_count }})
                </span>
              </div>
            </v-col>
          </v-row>
        </div>
      </template>
    </BaseCard>

    <!-- Delete Confirmation Dialog -->
    <ConfirmationDialog
      v-model="showDeleteDialog"
      :message="card.title"
      max-width="500px"
      @confirm="handleDelete"
    />

    <!-- Remove Confirmation Dialog -->
    <ConfirmationDialog
      v-model="showRemoveDialog"
      :message="card.title"
      title-key="common.messagebox.remove"
      confirm-label-key="common.remove"
      max-width="500px"
      @confirm="handleRemove"
    />
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ICONS } from '@/config/ui-constants'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { useAnalyzeStore } from '@/stores/analyze'
import { usePublishStore } from '@/stores/publish'
import { useAuth } from '@/composables/useAuth'
import { PERMISSIONS } from '@/services/auth/permissions'
import { deleteReportItem } from '@/api/analyze'
import BaseCard from '@/components/common/BaseCard.vue'
import ActionButton from '@/components/common/buttons/ActionButton.vue'
import ConfirmationDialog from '@/components/common/dialogs/ConfirmationDialog.vue'

const props = defineProps({
  card: {
    type: Object,
    required: true
  },
  showRemoveAction: {
    type: Boolean,
    default: false
  },
  disableActions: {
    type: Boolean,
    default: false
  },
  preselected: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['remove-report-item-from-selector', 'delete-item', 'show-detail'])

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const analyzeStore = useAnalyzeStore()
const publishStore = usePublishStore()
const { checkPermission } = useAuth()

const showDeleteDialog = ref(false)
const showRemoveDialog = ref(false)

const canModify = computed(() => {
  return (
    checkPermission(PERMISSIONS.ANALYZE_UPDATE) &&
    (props.card.modify === true || props.card.remote_user !== null)
  )
})

const canDelete = computed(() => {
  return (
    checkPermission(PERMISSIONS.ANALYZE_DELETE) &&
    (props.card.modify === true || props.card.remote_user !== null)
  )
})

const canCreateProduct = computed(() => {
  return checkPermission(PERMISSIONS.PUBLISH_CREATE) && !route.path.includes('/group/')
})

const multiSelectActive = computed(() => {
  return analyzeStore.getMultiSelectReport
})

const selectedColor = computed(() => {
  return analyzeStore.selectedReports.has(props.card.id) ? 'orange-lighten-4' : ''
})

const itemStatus = computed(() => {
  if (props.card.state) {
    return props.card.state.name
  }
  return 'no_state'
})

const selectionChanged = (isSelected) => {
  if (isSelected) {
    analyzeStore.selectReport({ id: props.card.id, item: props.card })
  } else {
    analyzeStore.deselectReport({ id: props.card.id, item: props.card })
  }
}

const cardItemClick = () => {
  if (
    checkPermission(PERMISSIONS.ANALYZE_ACCESS) &&
    (props.card.access === true || props.card.remote_user !== null)
  ) {
    // Emit event to open report item detail dialog
    emit('show-detail', props.card)
  }
}

const handleDelete = async () => {
  showDeleteDialog.value = false
  try {
    await deleteReportItem(props.card)

    // Emit event to parent to remove from list and trigger animation
    emit('delete-item', props.card)

    // Show success notification
    window.dispatchEvent(
      new CustomEvent('notification', {
        detail: { type: 'success', loc: 'common.deleted_successfully' }
      })
    )
  } catch (error) {
    console.error('Error deleting report item:', error)
    window.dispatchEvent(
      new CustomEvent('notification', {
        detail: { type: 'error', message: t('error.server_error') }
      })
    )
  }
}

const handleRemove = () => {
  showRemoveDialog.value = false
  emit('remove-report-item-from-selector', props.card)
}

const handlePublish = () => {
  publishStore.pendingNewProduct = [props.card]
  router.push('/publish')
}
</script>

<style scoped>
.card-item {
  cursor: pointer;
  transition: all 0.3s ease;
}
</style>
