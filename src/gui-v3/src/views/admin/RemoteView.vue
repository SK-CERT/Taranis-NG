<template>
    <v-container
        fluid
        class="pa-0"
    >
        <v-tabs
            v-model="activeTab"
            bg-color="transparent"
            color="primary"
        >
            <v-tab
                v-for="tab in availableTabs"
                :key="tab.value"
                :value="tab.value"
                :title="t(tab.description)"
            >
                <v-icon
                    :icon="tab.icon"
                    start
                />
                {{ t(tab.title) }}
            </v-tab>
        </v-tabs>

        <v-window v-model="activeTab">
            <v-window-item
                v-for="tab in availableTabs"
                :key="tab.value"
                :value="tab.value"
            >
                <component
                    :is="tab.component"
                    v-if="activeTab === tab.value"
                />
            </v-window-item>
        </v-window>
    </v-container>
</template>

<script setup lang="ts">
    import { useI18n } from 'vue-i18n'
    import { usePermissionTabs } from '@/composables/usePermissionTabs'
    import { ICONS } from '@/config/ui-constants'
    import RemoteAccessesView from './RemoteAccessesView.vue'
    import RemoteNodesView from './RemoteNodesView.vue'

    const { t } = useI18n()
    const tabs = [
        {
            value: 'access',
            title: 'nav_menu.remote_access',
            description: 'remote.access.tab_description',
            icon: ICONS.REMOTE_DESKTOP,
            component: RemoteAccessesView,
            permission: 'CONFIG_REMOTE_ACCESS_ACCESS'
        },
        {
            value: 'nodes',
            title: 'nav_menu.remote_nodes',
            description: 'remote.nodes.tab_description',
            icon: ICONS.SHARE_VARIANT,
            component: RemoteNodesView,
            permission: 'CONFIG_REMOTE_NODE_ACCESS'
        }
    ] as const

    const { availableTabs, activeTab } = usePermissionTabs(tabs)
</script>
