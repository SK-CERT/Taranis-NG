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
    import DataProvidersTab from '@/components/config/data-providers/DataProvidersTab.vue'
    import AiProvidersTab from '@/components/config/data-providers/AiProvidersTab.vue'

    const { t } = useI18n()
    const tabs = [
        {
            value: 'data-providers',
            title: 'nav_menu.data_providers',
            description: 'data_providers.data.tab_description',
            icon: ICONS.CLOUD_ARROW_DOWN,
            component: DataProvidersTab,
            permission: 'CONFIG_DATA_PROVIDER_ACCESS'
        },
        {
            value: 'ai-providers',
            title: 'nav_menu.ai_providers',
            description: 'data_providers.ai.tab_description',
            icon: ICONS.CREATION,
            component: AiProvidersTab,
            permission: 'CONFIG_AI_ACCESS'
        }
    ] as const

    const { availableTabs, activeTab } = usePermissionTabs(tabs)
</script>
