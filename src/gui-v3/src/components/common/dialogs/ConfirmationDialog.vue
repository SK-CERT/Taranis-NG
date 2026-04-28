<template>
  <v-dialog v-model="isOpen" :max-width="maxWidth">
    <v-card>
      <v-card-title class="d-flex align-center">
        <v-icon color="error" class="mr-2">{{ ICONS.ALERT_CIRCLE }}</v-icon>
        {{ t(titleKey) }}
      </v-card-title>
      <v-card-text>
        <slot>{{ message }}</slot>
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn variant="text" @click="isOpen = false">
          {{ t('common.cancel') }}
        </v-btn>
        <v-btn color="error" variant="text" @click="confirmDelete">
          {{ t(confirmLabelKey) }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { ICONS } from '@/config/ui-constants'

const props = defineProps({
  modelValue: Boolean,
  message: String,
  titleKey: {
    type: String,
    default: 'common.messagebox.delete'
  },
  confirmLabelKey: {
    type: String,
    default: 'common.delete'
  },
  maxWidth: {
    type: String,
    default: '600px'
  }
})

const emit = defineEmits(['update:modelValue', 'confirm'])

const { t } = useI18n()
const titleKey = props.titleKey
const confirmLabelKey = props.confirmLabelKey

const isOpen = ref(false)

watch(
  () => props.modelValue,
  (newVal) => {
    isOpen.value = newVal
  }
)

watch(isOpen, (newVal) => {
  emit('update:modelValue', newVal)
})

const confirmDelete = () => {
  emit('confirm')
  isOpen.value = false
}
</script>

<style scoped></style>
