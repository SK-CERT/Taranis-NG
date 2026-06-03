<template>
    <v-container fluid class="pa-0">
        <v-tabs v-model="activeTab" bg-color="transparent" color="primary">
            <v-tab value="users"> External Users </v-tab>
        </v-tabs>

        <v-window v-model="activeTab">
            <v-window-item value="users">
                <ExternalUsersView v-if="activeTab === 'users'" />
            </v-window-item>
        </v-window>
    </v-container>
</template>

<script setup lang="ts">
    import { ref } from 'vue'
    import ExternalUsersView from './ExternalUsersView.vue'

    const activeTab = ref<'users'>('users')
</script>
