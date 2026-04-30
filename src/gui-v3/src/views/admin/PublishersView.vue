<template>
  <v-container fluid class="pa-0">
    <v-tabs v-model="activeTab" bg-color="transparent" color="primary">
      <v-tab value="nodes">Publishers Nodes</v-tab>
      <v-tab value="presets">Publisher Presets</v-tab>
    </v-tabs>

    <v-window v-model="activeTab">
      <v-window-item value="nodes">
        <PublishersNodesView v-if="activeTab === 'nodes'" />
      </v-window-item>

      <v-window-item value="presets">
        <PublisherPresetsView v-if="activeTab === 'presets'" />
      </v-window-item>
    </v-window>
  </v-container>
</template>

<script setup>
import { ref } from 'vue'
import PublishersNodesView from './PublishersNodesView.vue'
import PublisherPresetsView from './PublisherPresetsView.vue'

const activeTab = ref('nodes')
</script>
