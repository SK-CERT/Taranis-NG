<template>
  <v-select
    :model-value="modelValue"
    :items="availableStates"
    :item-title="getStateTitle"
    item-value="id"
    :label="label"
    density="compact"
    variant="outlined"
    hide-details
    :style="{ maxWidth: maxWidth }"
    :disabled="disabled"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <template #item="{ item, props }">
      <v-list-item v-bind="props">
        <template v-if="item" #prepend>
          <v-icon :color="item.color">{{ item.icon }}</v-icon>
        </template>
      </v-list-item>
    </template>
    <template #selection="{ item }">
      <template v-if="item">
        <v-icon :color="item.color" class="mr-2">{{ item.icon }}</v-icon>
        <span>{{ getStateTitle(item) }}</span>
      </template>
    </template>
  </v-select>
</template>

<script setup>
import { useI18n } from 'vue-i18n'

const { t, te } = useI18n()

defineProps({
  modelValue: {
    type: [String, Number],
    default: null
  },
  availableStates: {
    type: Array,
    default: () => []
  },
  label: {
    type: String,
    default: 'State'
  },
  maxWidth: {
    type: String,
    default: '260px'
  },
  disabled: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:modelValue'])

const getStateTitle = (item) => {
  if (!item) return ''
  const key = 'workflow.states.' + item.display_name
  return te(key) ? t(key) : item.display_name
}
</script>
