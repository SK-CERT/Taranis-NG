<template>
  <v-snackbar
    v-model="show"
    :color="color"
    :timeout="timeout === 0 ? -1 : timeout"
    location="top right"
    transition="slide-y-transition"
  >
    <div class="d-flex align-center">
      <v-icon :icon="icon" class="mr-3" />
      <span>{{ message }}</span>
    </div>

    <template #actions>
      <v-btn variant="text" :icon="ICONS.CLOSE" @click="show = false" />
    </template>
  </v-snackbar>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { ICONS } from '@/config/ui-constants'

const { t } = useI18n()

const show = ref(false)
const type = ref('info')
const message = ref('')
const timeout = ref(3000)
const currentId = ref(null)

const color = computed(() => {
  const colors = {
    success: 'success',
    error: 'error',
    warning: 'warning',
    info: 'info'
  }
  return colors[type.value] || 'info'
})

const icon = computed(() => {
  const icons = {
    success: ICONS.CHECK_CIRCLE,
    error: ICONS.ALERT_CIRCLE,
    warning: ICONS.ALERT,
    info: ICONS.INFORMATION
  }
  return icons[type.value] || ICONS.INFORMATION
})

const handleNotification = (event) => {
  const { detail } = event
  if (!detail) return

  // If notification has an ID and it's different from current, dismiss first
  if (detail.id && detail.id !== currentId.value && show.value) {
    show.value = false
    // Wait a tick for the dismiss animation, then show new one
    setTimeout(() => showNotification(detail), 100)
  } else {
    showNotification(detail)
  }
}

const showNotification = (detail) => {
  type.value = detail.type || 'info'
  currentId.value = detail.id || null

  // Handle translation key or direct message
  if (detail.loc) {
    message.value = t(detail.loc, detail.params || {})
  } else if (detail.message) {
    message.value = detail.message
  } else {
    message.value = t('common.notification_default')
  }

  // Custom timeout if provided
  if (detail.timeout !== undefined) {
    timeout.value = detail.timeout
  } else {
    timeout.value = type.value === 'error' ? 5000 : 3000
  }

  show.value = true
}

onMounted(() => {
  window.addEventListener('notification', handleNotification)
})

onUnmounted(() => {
  window.removeEventListener('notification', handleNotification)
})
</script>

<style scoped>
/* Additional styling if needed */
</style>
