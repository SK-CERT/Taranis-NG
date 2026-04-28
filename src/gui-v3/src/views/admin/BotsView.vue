<template>
  <v-container fluid class="pa-0">
    <v-tabs v-model="activeTab" bg-color="transparent" color="primary">
      <v-tab value="presets">{{ t('nav_menu.bot_presets') }}</v-tab>
      <v-tab value="nodes">{{ t('nav_menu.bots_nodes') }}</v-tab>
    </v-tabs>

    <v-window v-model="activeTab">
      <v-window-item value="presets">
        <BotPresetsView v-if="activeTab === 'presets'" />
      </v-window-item>

      <v-window-item value="nodes">
        <BotsNodesView v-if="activeTab === 'nodes'" />
      </v-window-item>
    </v-window>
  </v-container>
</template>

<script setup>
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import BotPresetsView from './BotPresetsView.vue'
import BotsNodesView from './BotsNodesView.vue'

const { t } = useI18n()
const activeTab = ref('presets')
</script>
