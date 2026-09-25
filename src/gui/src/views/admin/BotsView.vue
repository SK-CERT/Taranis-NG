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
    import BotPresetsView from './BotPresetsView.vue'
    import BotsNodesView from './BotsNodesView.vue'

    const { t } = useI18n()
    const tabs = [
        {
            value: 'presets',
            title: 'nav_menu.bot_presets',
            description: 'bots.presets.tab_description',
            icon: ICONS.ROBOT,
            component: BotPresetsView,
            permission: 'CONFIG_BOT_PRESET_ACCESS'
        },
        {
            value: 'nodes',
            title: 'nav_menu.bots_nodes',
            description: 'bots.nodes.tab_description',
            icon: ICONS.SERVER_NETWORK,
            component: BotsNodesView,
            permission: 'CONFIG_BOTS_NODE_ACCESS'
        }
    ] as const

    const { availableTabs, activeTab } = usePermissionTabs(tabs)
</script>
