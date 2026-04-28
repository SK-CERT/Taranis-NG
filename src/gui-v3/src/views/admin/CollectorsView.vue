<template>
  <v-container fluid class="pa-0">
    <v-tabs v-model="activeTab" bg-color="transparent" color="primary">
      <v-tab value="nodes">Collectors Nodes</v-tab>
      <v-tab value="sources">OSINT Sources</v-tab>
      <v-tab value="groups">OSINT Source Groups</v-tab>
    </v-tabs>

    <v-window v-model="activeTab">
      <v-window-item value="nodes">
        <CollectorsNodesView v-if="activeTab === 'nodes'" />
      </v-window-item>

      <v-window-item value="sources">
        <OSINTSourcesView v-if="activeTab === 'sources'" />
      </v-window-item>

      <v-window-item value="groups">
        <OSINTSourceGroupsView v-if="activeTab === 'groups'" />
      </v-window-item>
    </v-window>
  </v-container>
</template>

<script setup>
import { ref } from 'vue'
import CollectorsNodesView from './CollectorsNodesView.vue'
import OSINTSourcesView from './OSINTSourcesView.vue'
import OSINTSourceGroupsView from './OSINTSourceGroupsView.vue'

const activeTab = ref('nodes')
</script>
