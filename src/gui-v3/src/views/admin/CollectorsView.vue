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
    import OSINTSourcesView from './OSINTSourcesView.vue'
    import OSINTSourceGroupsView from './OSINTSourceGroupsView.vue'

    const { t } = useI18n()
    const tabs = [
        {
            value: 'sources',
            title: 'nav_menu.osint_sources',
            description: 'collectors.sources.tab_description',
            icon: ICONS.ANIMATION_OUTLINE,
            component: OSINTSourcesView,
            permission: 'CONFIG_OSINT_SOURCE_ACCESS'
        },
        {
            value: 'groups',
            title: 'nav_menu.osint_source_groups',
            description: 'collectors.groups.tab_description',
            icon: ICONS.FOLDER_MULTIPLE,
            component: OSINTSourceGroupsView,
            permission: 'CONFIG_OSINT_SOURCE_GROUP_ACCESS'
        }
    ] as const

    const { availableTabs, activeTab } = usePermissionTabs(tabs)
</script>
