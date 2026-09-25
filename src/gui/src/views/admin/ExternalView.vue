<template>
    <v-container
        fluid
        class="pa-0"
    >
        <v-tabs
            v-model="activeTab"
            color="primary"
        >
            <v-tab value="users">{{ t('nav_menu.external_users') }}</v-tab>
            <v-tab value="groups">{{ t('nav_menu.asset_groups') }}</v-tab>
            <v-tab value="templates">{{ t('nav_menu.notification_templates') }}</v-tab>
        </v-tabs>
        <v-window v-model="activeTab">
            <v-window-item value="users"><ExternalUsersView v-if="activeTab === 'users'" /></v-window-item>
            <v-window-item value="groups"><AssetGroupsView v-if="activeTab === 'groups'" /></v-window-item>
            <v-window-item value="templates"><NotificationTemplatesView v-if="activeTab === 'templates'" /></v-window-item>
        </v-window>
    </v-container>
</template>
<script setup lang="ts">
    import { useI18n } from 'vue-i18n'
    import { useTabQuery } from '@/composables/useTabQuery'
    import ExternalUsersView from './ExternalUsersView.vue'
    import AssetGroupsView from './AssetGroupsView.vue'
    import NotificationTemplatesView from './NotificationTemplatesView.vue'
    const { t } = useI18n()
    const activeTab = useTabQuery(['users', 'groups', 'templates'], 'users')
</script>
