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
                value="presets"
                :title="t('bots.presets.tab_description')"
            >
                <v-icon
                    :icon="ICONS.ROBOT"
                    start
                />
                {{ t('nav_menu.bot_presets') }}
            </v-tab>
            <v-tab
                value="nodes"
                :title="t('bots.nodes.tab_description')"
            >
                <v-icon
                    :icon="ICONS.SERVER_NETWORK"
                    start
                />
                {{ t('nav_menu.bots_nodes') }}
            </v-tab>
        </v-tabs>

        <v-window v-model="activeTab">
            <v-window-item value="presets">
                <BotPresetsView v-if="activeTab === 'presets'" />
            </v-window-item>

            <v-window-item value="nodes">
                <BotsNodesView v-if="activeTab === 'nodes'" />
            </v-window-item>
        </v-window>
    </v-container>
</template>

<script setup lang="ts">
    import { useI18n } from 'vue-i18n'
    import { useTabQuery } from '@/composables/useTabQuery'
    import { ICONS } from '@/config/ui-constants'
    import BotPresetsView from './BotPresetsView.vue'
    import BotsNodesView from './BotsNodesView.vue'

    const { t } = useI18n()
    const activeTab = useTabQuery(['presets', 'nodes'], 'presets')
</script>
