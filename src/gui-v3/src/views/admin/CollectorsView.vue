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
                value="sources"
                :title="t('collectors.sources.tab_description')"
            >
                <v-icon
                    :icon="ICONS.ANIMATION_OUTLINE"
                    start
                />
                {{ t('nav_menu.osint_sources') }}
            </v-tab>
            <v-tab
                value="groups"
                :title="t('collectors.groups.tab_description')"
            >
                <v-icon
                    :icon="ICONS.FOLDER_MULTIPLE"
                    start
                />
                {{ t('nav_menu.osint_source_groups') }}
            </v-tab>
            <v-tab
                value="nodes"
                :title="t('collectors.nodes.tab_description')"
            >
                <v-icon
                    :icon="ICONS.SERVER_NETWORK"
                    start
                />
                {{ t('nav_menu.collectors_nodes') }}
            </v-tab>
        </v-tabs>

        <v-window v-model="activeTab">
            <v-window-item value="sources">
                <OSINTSourcesView v-if="activeTab === 'sources'" />
            </v-window-item>

            <v-window-item value="groups">
                <OSINTSourceGroupsView v-if="activeTab === 'groups'" />
            </v-window-item>

            <v-window-item value="nodes">
                <CollectorsNodesView v-if="activeTab === 'nodes'" />
            </v-window-item>
        </v-window>
    </v-container>
</template>

<script setup lang="ts">
    import { useI18n } from 'vue-i18n'
    import { useTabQuery } from '@/composables/useTabQuery'
    import { ICONS } from '@/config/ui-constants'
    import CollectorsNodesView from './CollectorsNodesView.vue'
    import OSINTSourcesView from './OSINTSourcesView.vue'
    import OSINTSourceGroupsView from './OSINTSourceGroupsView.vue'

    const { t } = useI18n()
    const activeTab = useTabQuery(['sources', 'groups', 'nodes'], 'sources')
</script>
