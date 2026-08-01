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
                value="data-providers"
                :title="t('data_providers.data.tab_description')"
            >
                <v-icon
                    :icon="ICONS.CLOUD_ARROW_DOWN"
                    start
                />
                {{ t('nav_menu.data_providers') }}
            </v-tab>
            <v-tab
                value="ai-providers"
                :title="t('data_providers.ai.tab_description')"
            >
                <v-icon
                    :icon="ICONS.CREATION"
                    start
                />
                {{ t('nav_menu.ai_providers') }}
            </v-tab>
        </v-tabs>

        <v-window v-model="activeTab">
            <v-window-item value="data-providers">
                <DataProvidersTab v-if="activeTab === 'data-providers'" />
            </v-window-item>
            <v-window-item value="ai-providers">
                <AiProvidersTab v-if="activeTab === 'ai-providers'" />
            </v-window-item>
        </v-window>
    </v-container>
</template>

<script setup lang="ts">
    import { useI18n } from 'vue-i18n'
    import { useTabQuery } from '@/composables/useTabQuery'
    import { ICONS } from '@/config/ui-constants'
    import DataProvidersTab from '@/components/config/data-providers/DataProvidersTab.vue'
    import AiProvidersTab from '@/components/config/data-providers/AiProvidersTab.vue'

    const { t } = useI18n()
    const activeTab = useTabQuery(['data-providers', 'ai-providers'], 'data-providers')
</script>
