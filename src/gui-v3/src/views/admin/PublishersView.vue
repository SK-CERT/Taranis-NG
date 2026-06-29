<template>
    <v-container fluid class="pa-0">
        <v-tabs v-model="activeTab" bg-color="transparent" color="primary">
            <v-tab value="presets" :title="t('publishers.presets.tab_description')">
                <v-icon :icon="ICONS.FILE_STAR_OUTLINE" start />
                Publisher Presets
            </v-tab>
            <v-tab value="nodes" :title="t('publishers.nodes.tab_description')">
                <v-icon :icon="ICONS.SERVER_NETWORK" start />
                Publishers Nodes
            </v-tab>
        </v-tabs>

        <v-window v-model="activeTab">
            <v-window-item value="nodes">
                <PublishersNodesView v-if="activeTab === 'nodes'" />
            </v-window-item>

            <v-window-item value="presets">
                <PublisherPresetsView v-if="activeTab === 'presets'" />
            </v-window-item>
        </v-window>
    </v-container>
</template>

<script setup lang="ts">
    import { useI18n } from 'vue-i18n'
    import { useTabQuery } from '@/composables/useTabQuery'
    import { ICONS } from '@/config/ui-constants'
    import PublishersNodesView from './PublishersNodesView.vue'
    import PublisherPresetsView from './PublisherPresetsView.vue'

    const { t } = useI18n()
    const activeTab = useTabQuery(['presets', 'nodes'], 'presets')
</script>
