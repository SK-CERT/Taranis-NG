<template>
  <div class="assess-item-actions">
    <!-- Open Link -->
    <v-btn
      v-if="hasLink"
      icon
      :size="size"
      :variant="variant"
      color="primary"
      :href="itemLink"
      target="_blank"
      rel="noreferrer"
      :title="t('assess.tooltip.open_source')"
      @click.stop
    >
      <v-icon :size="iconSize">{{ ICONS.OPEN_SOURCE }}</v-icon>
    </v-btn>

    <!-- Create Report (Single Item Only) -->
    <v-btn
      v-if="showCreateReport && canCreateReport"
      icon
      :size="size"
      :variant="variant"
      :title="t('assess.tooltip.analyze_item')"
      @click.stop="$emit('action', 'create-report')"
    >
      <v-icon :size="iconSize">{{ ICONS.ANALYZE }}</v-icon>
    </v-btn>

    <!-- Ungroup (Aggregate Only) -->
    <v-btn
      v-if="showUngroup && canModify"
      icon
      :size="size"
      :variant="variant"
      :title="t('assess.tooltip.ungroup_item')"
      @click.stop="$emit('action', 'ungroup')"
    >
      <v-icon :size="iconSize">{{ ICONS.UNGROUP }}</v-icon>
    </v-btn>

    <!-- Like -->
    <v-btn
      v-if="canModify"
      icon
      :size="size"
      :variant="item.me_like ? 'plain' : variant"
      :color="item.me_like ? COLORS.ACTIVE : COLORS.PRIMARY"
      :title="t('assess.tooltip.like_item')"
      @click.stop="$emit('action', 'like')"
    >
      <v-icon :size="iconSize">
        {{ showCounts && item.likes ? ICONS.LIKE : ICONS.LIKE_OUTLINE }}
      </v-icon>
    </v-btn>
    <v-btn
      v-if="showCounts && canModify && item.likes"
      text
      :size="size"
      disabled
      style="min-width: 16px; pointer-events: none"
    >
      {{ item.likes }}
    </v-btn>

    <!-- Dislike -->
    <v-btn
      v-if="canModify"
      icon
      :size="size"
      :variant="item.me_dislike ? 'plain' : variant"
      :color="item.me_dislike ? COLORS.ACTIVE : COLORS.PRIMARY"
      :title="t('assess.tooltip.dislike_item')"
      @click.stop="$emit('action', 'dislike')"
    >
      <v-icon :size="iconSize">
        {{ showCounts && item.dislikes ? ICONS.UNLIKE : ICONS.UNLIKE_OUTLINE }}
      </v-icon>
    </v-btn>
    <v-btn
      v-if="showCounts && canModify && item.dislikes"
      text
      :size="size"
      disabled
      style="min-width: 16px; pointer-events: none"
    >
      {{ item.dislikes }}
    </v-btn>

    <!-- Important -->
    <v-btn
      v-if="canModify"
      icon
      :size="size"
      :variant="item.important ? 'plain' : variant"
      :color="item.important ? COLORS.ACTIVE : COLORS.PRIMARY"
      :title="t('assess.tooltip.important_item')"
      @click.stop="$emit('action', 'important')"
    >
      <v-icon :size="iconSize">
        {{ item.important ? ICONS.IMPORTANT : ICONS.IMPORTANT_OUTLINE }}
      </v-icon>
    </v-btn>

    <!-- Read/Unread -->
    <v-btn
      v-if="canModify"
      icon
      :size="size"
      :variant="item.read ? 'text' : 'plain'"
      :color="item.read ? COLORS.ACTIVE : COLORS.PRIMARY"
      :title="t('assess.tooltip.read_item')"
      @click.stop="$emit('action', 'read')"
    >
      <v-icon :size="iconSize">
        {{ item.read ? ICONS.READ : ICONS.READ_OUTLINE }}
      </v-icon>
    </v-btn>

    <!-- Delete -->
    <ActionButton
      v-if="canDelete"
      action="delete"
      :size="size"
      :variant="variant"
      :title="t('assess.tooltip.delete_item')"
      @click.stop="showDeleteDialog = true"
    />

    <!-- Delete Confirmation Dialog -->
    <ConfirmationDialog
      v-model="showDeleteDialog"
      :message="t('assess.delete_confirmation')"
      max-width="600px"
      @confirm="$emit('action', 'delete')"
    />
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAuth } from '@/composables/useAuth'
import { PERMISSIONS } from '@/services/auth/permissions'
import { ICONS, COLORS } from '@/config/ui-constants'
import ActionButton from '@/components/common/buttons/ActionButton.vue'
import ConfirmationDialog from '@/components/common/dialogs/ConfirmationDialog.vue'

const props = defineProps({
  item: {
    type: Object,
    required: true
  },
  size: {
    type: String,
    default: 'small'
  },
  variant: {
    type: String,
    default: 'text'
  },
  iconSize: {
    type: String,
    default: 'small'
  },
  showCreateReport: {
    type: Boolean,
    default: false
  },
  showUngroup: {
    type: Boolean,
    default: false
  },
  showCounts: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['action'])

const { t } = useI18n()
const { checkPermission } = useAuth()

const showDeleteDialog = ref(false)

const itemLink = computed(() => {
  // Support both news_items array (aggregate) and direct link property
  if (props.item.news_items?.length > 0) {
    return props.item.news_items[0].news_item_data?.link || ''
  }
  return props.item.link || ''
})

const hasLink = computed(() => {
  return !!itemLink.value
})

const canModify = computed(() => {
  return checkPermission(PERMISSIONS.ASSESS_UPDATE)
})

const canDelete = computed(() => {
  return checkPermission(PERMISSIONS.ASSESS_DELETE)
})

const canCreateReport = computed(() => {
  return checkPermission(PERMISSIONS.ANALYZE_CREATE)
})
</script>

<style scoped>
.assess-item-actions {
  display: flex;
  align-items: center;
  gap: 4px;
}
</style>
