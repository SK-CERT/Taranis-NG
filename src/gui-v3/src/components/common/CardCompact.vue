<template>
  <v-container fluid class="pa-2">
    <div class="card-container d-flex align-center" :class="{ 'ga-3': multiSelectActive }">
      <!-- Checkbox for multi-select -->
      <div v-if="multiSelectActive" class="checkbox-column" @click.stop>
        <v-checkbox
          v-model="internalSelected"
          density="compact"
          hide-details
          @update:model-value="emitSelectionChange"
        />
      </div>

      <!-- Card -->
      <v-hover v-slot="{ isHovering, props: hoverProps }" class="flex-grow-1">
        <v-card
          v-bind="hoverProps"
          :elevation="isHovering ? 12 : 2"
          class="card-compact flex-grow-1"
          @click="handleClick"
        >
          <v-card-text>
            <v-row align="center">
              <!-- Icon/Tag -->
              <v-col cols="auto" class="pr-4">
                <v-icon size="large" color="primary">
                  {{ card.tag || ICONS.FILE_DOCUMENT }}
                </v-icon>
              </v-col>

              <!-- Title -->
              <v-col>
                <div class="text-label-small text-grey">{{ typeLabel }}</div>
                <div class="text-body-large">{{ typeValue }}</div>
              </v-col>

              <!-- Description/Subtitle -->
              <v-col v-if="card.subtitle || card.description">
                <div class="text-label-small text-grey">{{ t('card_item.description') }}</div>
                <div class="text-body-medium">{{ card.subtitle || card.description }}</div>
              </v-col>

              <!-- Actions -->
              <v-col v-if="canDelete" cols="auto">
                <ActionButton
                  action="delete"
                  @click.stop="showDeleteDialog"
                />
              </v-col>
            </v-row>
          </v-card-text>
        </v-card>
      </v-hover>
    </div>

    <!-- Delete confirmation dialog -->
    <v-dialog v-model="deleteDialog" max-width="400">
      <v-card>
        <v-card-title class="text-headline-small">
          {{ t('common.messagebox.delete') }}
        </v-card-title>
        <v-card-text>
          {{ card.title || card.name }}
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn text @click="deleteDialog = false">
            {{ t('common.cancel') }}
          </v-btn>
          <v-btn color="error" text @click="handleDelete">
            {{ t('common.delete') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAuth } from '@/composables/useAuth'
import { ICONS } from '@/config/ui-constants'
import ActionButton from '@/components/common/buttons/ActionButton.vue'

const props = defineProps({
  card: {
    type: Object,
    required: true
  },
  deletePermission: {
    type: String,
    default: ''
  },
  multiSelectActive: {
    type: Boolean,
    default: false
  },
  preselected: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['click', 'delete', 'edit', 'selection-change'])

const { t } = useI18n()
const { checkPermission } = useAuth()

const deleteDialog = ref(false)
const internalSelected = ref(props.preselected)

// Watch preselected prop and sync with internalSelected
watch(
  () => props.preselected,
  (newValue) => {
    internalSelected.value = newValue
  }
)

const canDelete = computed(() => {
  if (!props.deletePermission) return false
  return checkPermission(props.deletePermission)
})

const typeLabel = computed(() => {
  if (props.card?.report_type_name) {
    return props.card.report_type_name
  }
  if (props.card?.product_type_name) {
    return props.card.product_type_name
  }
  const sourceName =
    props.card?.news_items?.[0]?.news_item_data?.osint_source_name ||
    props.card?.news_items?.[0]?.news_item_data?.source
  const sourceType = props.card?.news_items?.[0]?.news_item_data?.osint_source_type
  if (sourceName) {
    return sourceType ? `${sourceName} (${sourceType})` : sourceName
  }
  return t('card_item.title')
})

const typeValue = computed(() => {
  return props.card?.title || props.card?.name || ''
})

const handleClick = () => {
  emit('edit', props.card)
}

const showDeleteDialog = () => {
  deleteDialog.value = true
}

const handleDelete = () => {
  deleteDialog.value = false
  emit('delete', props.card)
}

const emitSelectionChange = () => {
  emit('selection-change', internalSelected.value)
}
</script>

<style scoped>
.card-container {
  width: 100%;
  display: flex;
  flex-direction: row;
  align-items: center;
  flex: 1 1 0;
}

.checkbox-column {
  flex-shrink: 0;
  display: flex;
  align-items: flex-start;
  padding-top: 12px;
}

.card-compact {
  cursor: pointer;
  transition: all 0.3s ease;
  flex-grow: 1;
}

.card-compact:hover {
  transform: translateY(-2px);
}
</style>
