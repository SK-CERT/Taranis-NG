<template>
  <v-hover v-slot="{ isHovering, props }">
    <v-card
      v-bind="props"
      :elevation="isHovering ? 12 : 2"
      :class="['asset-card', statusClass]"
      @click="handleCardClick"
    >
      <v-card-text>
        <v-row align="center" no-gutters>
          <v-col cols="auto" class="pr-4">
            <v-icon size="x-large" color="primary">
              {{ asset.tag || 'mdi-server' }}
            </v-icon>
          </v-col>

          <v-col>
            <div class="text-caption text-grey">{{ $t('card_item.title') }}</div>
            <div class="text-h6">{{ asset.title }}</div>

            <div class="text-caption text-grey mt-2">{{ $t('card_item.description') }}</div>
            <div class="text-body-2">{{ asset.subtitle || asset.description }}</div>
          </v-col>

          <v-col v-if="canDelete" cols="auto" class="delete-btn">
            <ActionButton
              action="delete"
              @click.stop="showDeleteDialog = true"
            />
          </v-col>
        </v-row>
      </v-card-text>

      <v-card-actions class="pt-0">
        <v-chip
          v-if="asset.vulnerabilities_count > 0"
          color="error"
          size="small"
          variant="flat"
        >
          <v-icon start size="small">mdi-shield-alert</v-icon>
          {{ $t('asset.vulnerabilities_count') }}{{ asset.vulnerabilities_count }}
        </v-chip>
        <v-chip
          v-else
          color="success"
          size="small"
          variant="flat"
        >
          <v-icon start size="small">mdi-shield-check</v-icon>
          {{ $t('asset.no_vulnerabilities') }}
        </v-chip>
      </v-card-actions>
    </v-card>
  </v-hover>

  <v-dialog v-model="showDeleteDialog" max-width="500">
    <v-card>
      <v-card-title>
        {{ $t('common.messagebox.delete') }}
      </v-card-title>
      <v-card-text>
        {{ asset.title }}
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn variant="text" @click="showDeleteDialog = false">
          {{ $t('common.cancel') }}
        </v-btn>
        <v-btn color="error" variant="flat" @click="handleDelete">
          {{ $t('common.delete') }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useAuth } from '@/composables/useAuth'
import ActionButton from '@/components/common/buttons/ActionButton.vue'

const props = defineProps({
  asset: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['delete-asset', 'click'])

const { checkPermission } = useAuth()
const showDeleteDialog = ref(false)

const statusClass = computed(() => {
  return props.asset.vulnerabilities_count > 0 ? 'status-alert' : 'status-normal'
})

const canDelete = computed(() => {
  return checkPermission('MY_ASSETS_CREATE')
})

function handleCardClick() {
  // Dispatch event to open asset detail dialog
  window.dispatchEvent(
    new CustomEvent('show-asset-edit', {
      detail: {
        id: props.asset.id,
        title: props.asset.title,
        description: props.asset.subtitle || props.asset.description,
        modify: true,
        access: true
      }
    })
  )
  emit('click', props.asset)
}

function handleDelete() {
  showDeleteDialog.value = false
  emit('delete-asset', props.asset)
}
</script>

<style scoped>
.asset-card {
  cursor: pointer;
  transition: all 0.3s;
}

.asset-card.status-alert {
  border-left: 4px solid rgb(var(--v-theme-error));
}

.asset-card.status-normal {
  border-left: 4px solid rgb(var(--v-theme-success));
}

.delete-btn {
  opacity: 0;
  transition: opacity 0.2s;
}

.asset-card:hover .delete-btn {
  opacity: 1;
}
</style>
