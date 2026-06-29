<template>
    <v-container fluid class="pa-0">
        <v-tabs v-model="activeTab" bg-color="transparent" color="primary">
            <v-tab value="types" :title="t('presenters.types.tab_description')">
                <v-icon :icon="ICONS.FILE_DOCUMENT_OUTLINE" start />
                Product Types
            </v-tab>
            <v-tab value="nodes" :title="t('presenters.nodes.tab_description')">
                <v-icon :icon="ICONS.SERVER_NETWORK" start />
                Presenters Nodes
            </v-tab>
        </v-tabs>

        <v-window v-model="activeTab">
            <v-window-item value="nodes">
                <PresentersNodesView v-if="activeTab === 'nodes'" />
            </v-window-item>

            <v-window-item value="types">
                <ProductTypesView v-if="activeTab === 'types'" />
            </v-window-item>
        </v-window>
    </v-container>
</template>

<script setup lang="ts">
    import { useI18n } from 'vue-i18n'
    import { useTabQuery } from '@/composables/useTabQuery'
    import { ICONS } from '@/config/ui-constants'
    import PresentersNodesView from './PresentersNodesView.vue'
    import ProductTypesView from './ProductTypesView.vue'

    const { t } = useI18n()
    const activeTab = useTabQuery(['nodes', 'types'], 'types')
</script>
