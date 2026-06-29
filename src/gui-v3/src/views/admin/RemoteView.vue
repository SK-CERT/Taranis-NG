<template>
    <v-container fluid class="pa-0">
        <v-tabs v-model="activeTab" bg-color="transparent" color="primary">
            <v-tab value="access" :title="t('remote.access.tab_description')">
                <v-icon :icon="ICONS.REMOTE_DESKTOP" start />
                Remote Access
            </v-tab>
            <v-tab value="nodes" :title="t('remote.nodes.tab_description')">
                <v-icon :icon="ICONS.SHARE_VARIANT" start />
                Remote Nodes
            </v-tab>
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

<script setup lang="ts">
    import { useI18n } from 'vue-i18n'
    import { useTabQuery } from '@/composables/useTabQuery'
    import { ICONS } from '@/config/ui-constants'
    import RemoteAccessesView from './RemoteAccessesView.vue'
    import RemoteNodesView from './RemoteNodesView.vue'

    const { t } = useI18n()
    const activeTab = useTabQuery(['access', 'nodes'], 'access')
</script>
