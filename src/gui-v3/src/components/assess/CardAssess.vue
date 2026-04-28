<template>
  <BaseCard
    :multi-select-active="multiSelectActive"
    :show-selection-checkbox="true"
    :preselected="preselected"
    :checkbox-label="t('assess.select')"
    :card-color="selectedColor"
    :class="{ 'read-item': card.read }"
    @card-click="showDetail"
    @selection-change="selectionChanged"
  >
    <!-- Content Slot -->
    <template #content>
      <!-- Header: Source and Date Info -->
      <div class="text-label-small text-grey mb-2">
        <v-row align="center" no-gutters>
          <v-col cols="auto">
            <span v-if="card.news_items && card.news_items.length > 0">
              {{ t('card_item.source') }}:
              <strong>
                {{ card.news_items[0].news_item_data?.osint_source_name || card.news_items[0].news_item_data?.source || 'Unknown' }}
                <span v-if="card.news_items[0].news_item_data?.osint_source_type">({{ card.news_items[0].news_item_data.osint_source_type.split(' ')[0] }})</span>
              </strong>
            </span>
          </v-col>
          <v-spacer />
          <v-col cols="auto">
            <span v-if="card.news_items && card.news_items.length > 0">
              <strong>{{ t('card_item.published') }}:</strong>
              {{ card.news_items[0].news_item_data?.published || 'N/A' }}
            </span>
          </v-col>
          <v-spacer />
          <v-col cols="auto">
            <strong>{{ t('card_item.collected') }}:</strong>
            {{ card.created }}
          </v-col>
        </v-row>
      </div>

      <!-- Title -->
      <h3 class="mb-2" style="font-size: 1.25rem; font-weight: 700; line-height: 1.35; color: rgba(255, 255, 255, 0.95);">
        {{ card.title }}
      </h3>

      <!-- Description -->
      <p v-if="!hideReviews" class="text-grey mb-3">
        {{ card.description }}
      </p>

      <!-- Footer: Metadata Badges and Actions -->
      <v-row align="center" no-gutters>
        <v-col class="d-flex align-center flex-wrap" style="gap: 12px">
          <!-- Source Link URL (non-clickable text) -->
          <span
            v-if="
              !hideSourceLinks &&
                card.news_items &&
                card.news_items.length > 0 &&
                card.news_items[0].news_item_data?.link
            "
            class="text-label-small text-primary"
            style="
              display: inline-block;
              max-width: 300px;
              overflow: hidden;
              text-overflow: ellipsis;
              white-space: nowrap;
            "
          >
            {{ card.news_items[0].news_item_data.link }}
          </span>

          <!-- Aggregate Badge -->
          <v-chip
            v-if="card.news_items && card.news_items.length > 1"
            size="small"
            color="primary"
            variant="outlined"
          >
            <v-icon start>mdi-file-multiple</v-icon>
            {{ t('card_item.aggregated_items') }}: {{ card.news_items.length }}
          </v-chip>

          <!-- In Reports Badge -->
          <v-chip
            v-if="card.in_reports_count > 0"
            size="small"
            color="orange"
            variant="outlined"
            :disabled="analyzeSelector"
            :style="analyzeSelector ? '' : 'cursor: pointer'"
            @click.stop="!analyzeSelector && showInReports()"
          >
            <v-icon start>mdi-file-document</v-icon>
            {{ t('card_item.in_analyze') }}
            <span v-if="card.in_reports_count > 1">&nbsp;({{ card.in_reports_count }})</span>
          </v-chip>

          <!-- Comments Icon -->
          <v-icon v-if="hasComments" color="orange" size="small">mdi-comment</v-icon>
        </v-col>

        <!-- Actions -->
        <v-col
          v-if="!multiSelectActive && !analyzeSelector"
          cols="auto"
          class="d-flex align-center"
          style="gap: 4px"
        >
          <AssessItemActions
            :item="card"
            size="small"
            variant="text"
            icon-size="default"
            :show-counts="true"
            show-create-report
            @action="handleCardAction"
          />
        </v-col>
      </v-row>
    </template>
  </BaseCard>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAssessStore } from '@/stores/assess'
import { useAuth } from '@/composables/useAuth'
import { deleteNewsItemAggregate } from '@/api/assess'
import BaseCard from '@/components/common/BaseCard.vue'
import AssessItemActions from '@/components/assess/AssessItemActions.vue'

const props = defineProps({
  card: {
    type: Object,
    required: true
  },
  data_set: {
    type: String,
    default: 'assess'
  },
  preselected: {
    type: Boolean,
    default: false
  },
  analyzeSelector: {
    type: Boolean,
    default: false
  },
  hideReviews: {
    type: Boolean,
    default: false
  },
  hideSourceLinks: {
    type: Boolean,
    default: false
  },
  highlightWordlist: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['show-detail', 'update-item', 'delete-item', 'show-reports-for-item'])

const { t } = useI18n()
const assessStore = useAssessStore()
const { checkPermission } = useAuth()

const multiSelectActive = computed(() => assessStore.getMultiSelect)

const selectedColor = computed(() => {
  return assessStore.selectedItems.has(props.card.id) ? 'orange-lighten-4' : ''
})

const hasComments = computed(() => {
  if (!props.card.comments) return false
  // Strip HTML tags and check if there's actual content
  const plainText = props.card.comments.replace(/<[^>]*>/g, '').trim()
  return plainText.length > 0
})

const selectionChanged = (isSelected) => {
  if (isSelected) {
    assessStore.select({ type: 'news_item_aggregate', id: props.card.id, item: props.card })
  } else {
    assessStore.deselect({ type: 'news_item_aggregate', id: props.card.id })
  }
}

const showDetail = () => {
  emit('show-detail', props.card)
}

const showInReports = () => {
  emit('show-reports-for-item', props.card)
}

const handleCardAction = (action) => {
  if (action === 'delete') {
    handleDelete()
  } else {
    updateCard(action)
  }
}

const updateCard = (action) => {
  emit('update-item', props.card, action)
}

const handleDelete = async () => {
  try {
    await deleteNewsItemAggregate(null, props.card.id)
    emit('delete-item', props.card)

    // Show success notification
    window.dispatchEvent(
      new CustomEvent('notification', {
        detail: { type: 'success', loc: 'common.deleted_successfully' }
      })
    )
  } catch (error) {
    console.error('Error deleting news item aggregate:', error)

    // Check if it's an "in use" error
    if (error.response?.data === 'aggregate_in_use' || error.response?.status === 500) {
      window.dispatchEvent(
        new CustomEvent('notification', {
          detail: {
            type: 'error',
            message: t('error.aggregate_in_use')
          }
        })
      )
    } else {
      window.dispatchEvent(
        new CustomEvent('notification', {
          detail: {
            type: 'error',
            message: t('error.server_error')
          }
        })
      )
    }
  }
}
</script>

<style scoped>
.read-item {
  opacity: 0.7;
}

.read-item:hover {
  opacity: 1;
}
</style>
