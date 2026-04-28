<template>
  <div>
    <BaseCard
      :multi-select-active="multiSelectActive"
      :show-selection-checkbox="true"
      :preselected="preselected"
      :checkbox-label="t('publish.select')"
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
              <span class="text-caption text-medium-emphasis">{{ card.product_type_name }}</span>
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
                {{ card.updated_at }}
                <span v-if="card.updated_by" class="text-medium-emphasis">&nbsp;&nbsp;{{ card.updated_by }}</span>
              </div>
            </v-col>
            <!-- Actions - inline in header, like Analyze -->
            <v-col shrink class="d-flex align-center" style="gap: 0; padding: 0; margin-left: 4px;">
              <!-- Delete -->
              <ActionButton
                v-if="canDelete"
                action="delete"
                size="x-small"
                :title="t('publish.tooltip.delete_item')"
                @click.stop="showDeleteDialog = true"
              />
            </v-col>
          </v-row>
          <!-- Title + Description Row -->
          <v-row no-gutters class="mt-2">
            <v-col cols="12" md="6">
              <div class="text-body-1 font-weight-medium">
                {{ card.title }}
                <span v-if="card.report_items_count" class="text-medium-emphasis">
                  &nbsp;({{ card.report_items_count }})
                </span>
              </div>
            </v-col>
            <v-col v-if="card.subtitle" cols="12" md="6">
              <div class="text-caption text-medium-emphasis">{{ t('card_item.description') }}</div>
              <div class="text-body-2">{{ card.subtitle }}</div>
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
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { usePublishStore } from '@/stores/publish'
import { useAuth } from '@/composables/useAuth'
import { ICONS } from '@/config/ui-constants'
import { PERMISSIONS } from '@/services/auth/permissions'
import { deleteProduct } from '@/api/publish'
import BaseCard from '@/components/common/BaseCard.vue'
import ActionButton from '@/components/common/buttons/ActionButton.vue'
import ConfirmationDialog from '@/components/common/dialogs/ConfirmationDialog.vue'

const props = defineProps({
  card: {
    type: Object,
    required: true
  },
  preselected: {
    type: Boolean,
    default: false
  }
})

const { t } = useI18n()
const publishStore = usePublishStore()
const { checkPermission } = useAuth()

const showDeleteDialog = ref(false)

const multiSelectActive = computed(() => publishStore.getMultiSelect)

const selectedColor = computed(() => {
  return publishStore.selectedProducts.has(props.card.id) ? 'orange-lighten-4' : ''
})

const canDelete = computed(() => {
  // Check permission - modify check may not be needed or property may be named differently
  return checkPermission(PERMISSIONS.PUBLISH_DELETE)
})

const selectionChanged = (isSelected) => {
  if (isSelected) {
    publishStore.select({ id: props.card.id, item: props.card })
  } else {
    publishStore.deselect({ id: props.card.id })
  }
}

const cardItemClick = () => {
  // Emit event to open edit dialog
  const editData = {
    id: props.card.id,
    title: props.card.title,
    description: props.card.subtitle || '',
    product_type_id: props.card.product_type_id,
    state_id: props.card.state?.id || null,
    report_items: props.card.report_items || [],
    modify: props.card.modify === true,
    access: props.card.access === true
  }
  window.dispatchEvent(new CustomEvent('show-product-edit', { detail: editData }))
}

const handleDelete = async () => {
  showDeleteDialog.value = false
  try {
    await deleteProduct(props.card)

    // Show success notification
    window.dispatchEvent(
      new CustomEvent('notification', {
        detail: { type: 'success', loc: 'common.deleted_successfully' }
      })
    )

    // Emit event to refresh the list
    window.dispatchEvent(new CustomEvent('product-updated'))
  } catch (error) {
    console.error('Error deleting product:', error)

    // Show error notification
    window.dispatchEvent(
      new CustomEvent('notification', {
        detail: { type: 'error', loc: 'common.error_deleting' }
      })
    )
  }
}
</script>

<style scoped>
.card-item {
  cursor: pointer;
  transition: all 0.3s ease;
}
</style>
