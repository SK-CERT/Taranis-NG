<template>
  <v-container fluid class="pa-0">
    <v-tabs v-model="activeTab" bg-color="transparent" color="primary">
      <v-tab value="access">Remote Access</v-tab>
      <v-tab value="nodes">Remote Nodes</v-tab>
    </v-tabs>

    <v-window v-model="activeTab">
      <v-window-item value="access">
        <RemoteAccessesView v-if="activeTab === 'access'" />
      </v-window-item>

      <v-window-item value="nodes">
        <RemoteNodesView v-if="activeTab === 'nodes'" />
      </v-window-item>
    </v-window>
  </v-container>
</template>

<script setup>
import { ref } from 'vue'
import RemoteAccessesView from './RemoteAccessesView.vue'
import RemoteNodesView from './RemoteNodesView.vue'

const activeTab = ref('access')
</script>
