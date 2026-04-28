<template>
  <v-container fluid class="pa-0">
    <v-tabs v-model="activeTab" bg-color="transparent" color="primary">
      <v-tab value="roles">{{ t('nav_menu.roles') }}</v-tab>
    </v-tabs>

    <v-window v-model="activeTab">
      <v-window-item value="roles">
        <RolesTab v-if="activeTab === 'roles'" />
      </v-window-item>
    </v-window>
  </v-container>
</template>

<script setup>
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import RolesTab from '@/components/config/roles/RolesTab.vue'

const { t } = useI18n()
const activeTab = ref('roles')
</script>
