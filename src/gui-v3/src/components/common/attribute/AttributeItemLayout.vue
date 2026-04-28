<template>
  <v-row justify="center" class="attribute-item-layout pt-2">
    <v-row no-gutters>
      <slot name="header">
        <v-row justify="center">
          <!-- SORT -->
          <v-chip-group
            v-if="values.length > 1"
            active-class="success"
            color=""
            class="pr-4"
          >
            <v-chip
              size="small"
              class="px-0 mr-1"
              :title="t('report_item.tooltip.sort_time')"
              @click="sort(false)"
            >
              <v-icon class="px-2" size="small">{{ ICONS.CLOCK }}</v-icon>
            </v-chip>
            <v-chip
              size="small"
              class="px-0 mr-1"
              :title="t('report_item.tooltip.sort_user')"
              @click="sort(true, authStore.user?.name)"
            >
              <v-icon class="px-2" size="small">{{ ICONS.ACCOUNT }}</v-icon>
            </v-chip>
          </v-chip-group>
        </v-row>
      </slot>
    </v-row>
    <v-row class="ml-0 mr-4">
      <slot name="content" />
    </v-row>
    <v-row class="ml-3 mr-5">
      <slot name="footer" class="pr-0">
        <v-btn
          v-if="addButton"
          variant="flat"
          size="small"
          block
          class="mt-2"
          :title="t('report_item.tooltip.add_value')"
          @click="handleAdd"
        >
          <v-icon>{{ ICONS.PLUS }}</v-icon>
        </v-btn>
      </slot>
    </v-row>
  </v-row>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '@/stores/auth'
import { ICONS } from '@/config/ui-constants'

const props = defineProps({
  addButton: {
    type: Boolean,
    default: false
  },
  values: {
    type: Array,
    required: true
  }
})

const emit = defineEmits(['add-value'])

const { t } = useI18n()
const authStore = useAuthStore()

const handleAdd = () => {
  emit('add-value')
}

const sort = (sortByUser, userName) => {
  props.values.sort((a, b) => {
    if (sortByUser && userName) {
      if (userName === a.user?.name && userName !== b.user?.name) {
        return -1
      } else if (userName !== a.user?.name && userName === b.user?.name) {
        return 1
      }
    }
    if (a.id < b.id) return -1
    if (a.id > b.id) return 1
    return 0
  })
}
</script>

<style scoped>
.attribute-item-layout {
  padding-left: 8px;
}

.attribute-item-layout :deep(.v-chip-group) {
  gap: 4px;
}
</style>
