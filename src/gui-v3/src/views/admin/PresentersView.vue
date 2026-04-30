<template>
  <v-container fluid class="pa-0">
    <v-tabs v-model="activeTab" bg-color="transparent" color="primary">
      <v-tab value="nodes">Presenters Nodes</v-tab>
      <v-tab value="types">Product Types</v-tab>
    </v-tabs>

    <v-window v-model="activeTab">
      <v-window-item value="nodes">
        <PresentersNodesView v-if="activeTab === 'nodes'" />
      </v-window-item>

      <v-window-item value="types">
        <ProductTypesView v-if="activeTab === 'types'" />
      </v-window-item>
    </v-window>
  </v-container>
</template>

<script setup>
import { ref } from 'vue'
import PresentersNodesView from './PresentersNodesView.vue'
import ProductTypesView from './ProductTypesView.vue'

const activeTab = ref('nodes')
</script>
