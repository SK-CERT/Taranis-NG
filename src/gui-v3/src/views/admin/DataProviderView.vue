<template>
  <v-container fluid class="pa-0">
    <v-tabs v-model="activeTab" bg-color="transparent" color="primary">
      <v-tab value="data-providers">{{ t('nav_menu.data_providers') }}</v-tab>
      <v-tab value="ai-providers">{{ t('nav_menu.ai_providers') }}</v-tab>
    </v-tabs>

    <v-window v-model="activeTab">
      <v-window-item value="data-providers">
        <DataProvidersTab v-if="activeTab === 'data-providers'" />
      </v-window-item>
      <v-window-item value="ai-providers">
        <AiProvidersTab v-if="activeTab === 'ai-providers'" />
      </v-window-item>
    </v-window>
  </v-container>
</template>

<script setup>
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import DataProvidersTab from '@/components/config/data-providers/DataProvidersTab.vue'
import AiProvidersTab from '@/components/config/ai-providers/AiProvidersTab.vue'

const { t } = useI18n()
const activeTab = ref('data-providers')
</script>
