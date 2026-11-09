<template>
    <v-container
        fluid
        class="pa-0"
    >
        <v-tabs
            v-model="activeTab"
            class="config-tabs"
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
    // The nodes with their webs, and the report templates the webs render products with.
    // The Routing & TLS tab that briefly lived here moved to Application Settings - it
    // configures the whole instance (TLS floor, default certificate, HSTS policy), not the
    // public webs alone. Host-scoped settings (per-web HSTS, per-web resolver) are in each
    // web's own dialog.
    import { useI18n } from 'vue-i18n'
    import { usePermissionTabs } from '@/composables/usePermissionTabs'
    import { ICONS } from '@/config/ui-constants'
    import PublicWebNodesTab from '@/components/config/public-web/PublicWebNodesTab.vue'
    import PublicWebTemplatesTab from '@/components/config/public-web/PublicWebTemplatesTab.vue'

    const { t } = useI18n()
    const tabs = [
        {
            value: 'nodes',
            title: 'public_web.tabs.nodes',
            description: 'public_web.tabs.nodes_description',
            icon: ICONS.SERVER_NETWORK,
            component: PublicWebNodesTab,
            permission: 'CONFIG_PUBLIC_WEB_NODE_ACCESS'
        },
        {
            value: 'templates',
            title: 'public_web.tabs.templates',
            description: 'public_web.tabs.templates_description',
            icon: ICONS.FILE_CODE_OUTLINE,
            component: PublicWebTemplatesTab,
            permission: 'CONFIG_PUBLIC_WEB_NODE_ACCESS'
        }
    ] as const

    const { availableTabs, activeTab } = usePermissionTabs(tabs)
</script>
