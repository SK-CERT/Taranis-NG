<template>
  <v-container fluid class="pa-0">
    <v-tabs v-model="activeTab" bg-color="transparent" color="primary">
      <v-tab value="organizations">{{ t('nav_menu.organizations') }}</v-tab>
    </v-tabs>

    <v-window v-model="activeTab">
      <v-window-item value="organizations">
        <OrganizationsTab v-if="activeTab === 'organizations'" />
      </v-window-item>
    </v-window>
  </v-container>
</template>

<script setup>
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import OrganizationsTab from '@/components/config/organizations/OrganizationsTab.vue'

const { t } = useI18n()
const activeTab = ref('organizations')
</script>
