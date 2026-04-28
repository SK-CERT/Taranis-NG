<template>
  <v-list density="compact" class="pa-0">
    <!-- Section icon -->
    <v-list-item class="justify-center pa-2">
      <v-icon :color="iconColor" size="large">mdi-send</v-icon>
    </v-list-item>
  </v-list>
</template>

<script setup>
import { computed } from 'vue'
import { useTheme } from 'vuetify'

const { global: themeGlobal } = useTheme()

const isDark = computed(() => themeGlobal.name.value === 'dark')
const iconColor = computed(() => isDark.value ? '#ffffff' : 'rgba(0, 0, 0, 0.54)')
</script>

<style scoped>
.v-list-item {
  min-height: auto;
}
</style>
