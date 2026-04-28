<template>
  <v-btn
    v-if="show"
    :prepend-icon="ICONS.PLUS"
    color="primary"
    variant="flat"
    class="add-new-button"
    v-bind="sanitizedAttrs"
    @click="onButtonClick"
  >
    {{ translatedLabel }}
  </v-btn>
</template>

<script setup>
import { computed } from 'vue'
import { useAttrs } from 'vue'
import { useI18n } from 'vue-i18n'
import { ICONS } from '@/config/ui-constants'

const props = defineProps({
  label: {
    type: String,
    default: 'common.add_btn'
  },
  show: {
    type: Boolean,
    default: true
  }
})

const { t } = useI18n()
const attrs = useAttrs()

const translatedLabel = computed(() => t(props.label))

// Remove onClick and color from attrs to avoid conflicts
// Only pass through safe attributes like 'id', 'class', etc
const sanitizedAttrs = computed(() => {
  const { onClick, color, ...rest } = attrs
  return rest
})

// Handle click - forward to the dialog activator handler if present
const onButtonClick = (event) => {
  if (attrs.onClick) {
    attrs.onClick(event)
  }
}
</script>

<style scoped>
.add-new-button {
  color: white !important;
}
</style>
