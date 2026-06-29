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
                value="types"
                :title="t('reports.types.tab_description')"
            >
                <v-icon
                    :icon="ICONS.FILE_TABLE"
                    start
                />
                {{ t('nav_menu.report_types') }}
            </v-tab>
            <v-tab
                value="attributes"
                :title="t('reports.attributes.tab_description')"
            >
                <v-icon
                    :icon="ICONS.APPLICATION_VARIABLE_OUTLINE"
                    start
                />
                {{ t('nav_menu.attributes') }}
            </v-tab>
        </v-tabs>

        <v-window v-model="activeTab">
            <v-window-item value="types">
                <ReportTypesView v-if="activeTab === 'types'" />
            </v-window-item>
            <v-window-item value="attributes">
                <AttributesTab v-if="activeTab === 'attributes'" />
            </v-window-item>
        </v-window>
    </v-container>
</template>

<script setup lang="ts">
    import { useI18n } from 'vue-i18n'
    import { useTabQuery } from '@/composables/useTabQuery'
    import { ICONS } from '@/config/ui-constants'
    import ReportTypesView from './ReportTypesView.vue'
    import AttributesTab from '@/components/config/reports/AttributesTab.vue'

    const { t } = useI18n()
    const activeTab = useTabQuery(['types', 'attributes'], 'types')
</script>
