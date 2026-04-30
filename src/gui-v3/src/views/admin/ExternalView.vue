<template>
  <v-container fluid class="pa-0">
    <v-tabs v-model="activeTab" bg-color="transparent" color="primary">
      <v-tab value="users">External Users</v-tab>
      <v-tab value="groups">Asset Groups</v-tab>
      <v-tab value="templates">Notification Templates</v-tab>
    </v-tabs>

    <v-window v-model="activeTab">
      <v-window-item value="users">
        <ExternalUsersView v-if="activeTab === 'users'" />
      </v-window-item>

      <v-window-item value="groups">
        <AssetGroupsView v-if="activeTab === 'groups'" />
      </v-window-item>

      <v-window-item value="templates">
        <NotificationTemplatesView v-if="activeTab === 'templates'" />
      </v-window-item>
    </v-window>
  </v-container>
</template>

<script setup>
import { ref } from 'vue'
import ExternalUsersView from './ExternalUsersView.vue'
import AssetGroupsView from './AssetGroupsView.vue'
import NotificationTemplatesView from './NotificationTemplatesView.vue'

const activeTab = ref('users')
</script>
