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
    import ReportTypesView from './ReportTypesView.vue'
    import AttributesTab from '@/components/config/reports/AttributesTab.vue'

    const { t } = useI18n()
    const tabs = [
        {
            value: 'types',
            title: 'nav_menu.report_types',
            description: 'reports.types.tab_description',
            icon: ICONS.FILE_TABLE,
            component: ReportTypesView,
            permission: 'CONFIG_REPORT_TYPE_ACCESS'
        },
        {
            value: 'attributes',
            title: 'nav_menu.attributes',
            description: 'reports.attributes.tab_description',
            icon: ICONS.APPLICATION_VARIABLE_OUTLINE,
            component: AttributesTab,
            permission: 'CONFIG_ATTRIBUTE_ACCESS'
        }
    ] as const

    const { availableTabs, activeTab } = usePermissionTabs(tabs)
</script>
