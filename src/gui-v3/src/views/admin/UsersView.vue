<template>
  <v-container fluid class="pa-0">
    <v-tabs v-model="activeTab" bg-color="transparent" color="primary">
      <v-tab value="users">{{ t('nav_menu.users') }}</v-tab>
    </v-tabs>

    <v-window v-model="activeTab">
      <v-window-item value="users">
        <UsersTab v-if="activeTab === 'users'" />
      </v-window-item>
    </v-window>
  </v-container>
</template>

<script setup>
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import UsersTab from '@/components/config/users/UsersTab.vue'

const { t } = useI18n()
const activeTab = ref('users')
</script>
