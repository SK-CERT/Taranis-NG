<template>
    <v-container fluid class="pa-0">
        <v-tabs v-model="activeTab" bg-color="transparent" color="primary">
            <v-tab value="users" :title="t('external_user.tab_description')">
                <v-icon :icon="ICONS.ACCOUNT_GROUP" start />
                External Users
            </v-tab>
        </v-tabs>

        <v-window v-model="activeTab">
            <v-window-item value="users">
                <ExternalUsersView v-if="activeTab === 'users'" />
            </v-window-item>
        </v-window>
    </v-container>
</template>

<script setup lang="ts">
    import { useI18n } from 'vue-i18n'
    import { useTabQuery } from '@/composables/useTabQuery'
    import { ICONS } from '@/config/ui-constants'
    import ExternalUsersView from './ExternalUsersView.vue'

    const { t } = useI18n()
    const activeTab = useTabQuery(['users'], 'users')
</script>
