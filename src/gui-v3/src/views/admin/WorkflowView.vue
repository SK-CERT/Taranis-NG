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
                value="states"
                :title="t('workflow.states.tab_description')"
            >
                <v-icon
                    :icon="ICONS.STATE_MACHINE"
                    start
                />
                {{ t('workflow.states_tab') }}
            </v-tab>
            <v-tab
                value="state-workflow"
                :title="t('workflow.state_workflow.tab_description')"
            >
                <v-icon
                    :icon="ICONS.SITEMAP"
                    start
                />
                {{ t('workflow.state_workflow_tab') }}
            </v-tab>
            <v-tab
                value="tags"
                :title="t('workflow.tags.tab_description')"
            >
                <v-icon
                    :icon="ICONS.TAG_MULTIPLE"
                    start
                />
                {{ t('workflow.tags_tab') }}
            </v-tab>
            <v-tab
                value="tag-workflow"
                :title="t('workflow.tag_workflow.tab_description')"
            >
                <v-icon
                    :icon="ICONS.TAG_ARROW_RIGHT"
                    start
                />
                {{ t('workflow.tag_workflow_tab') }}
            </v-tab>
        </v-tabs>

        <v-window v-model="activeTab">
            <v-window-item value="states">
                <StatesTab v-if="activeTab === 'states'" />
            </v-window-item>

            <v-window-item value="state-workflow">
                <StateWorkflowTab v-if="activeTab === 'state-workflow'" />
            </v-window-item>

            <v-window-item value="tags">
                <TagsTab v-if="activeTab === 'tags'" />
            </v-window-item>

            <v-window-item value="tag-workflow">
                <TagWorkflowTab v-if="activeTab === 'tag-workflow'" />
            </v-window-item>
        </v-window>
    </v-container>
</template>

<script setup lang="ts">
    import { useI18n } from 'vue-i18n'
    import { useTabQuery } from '@/composables/useTabQuery'
    import { ICONS } from '@/config/ui-constants'
    import StatesTab from '@/components/config/workflow/StatesTab.vue'
    import StateWorkflowTab from '@/components/config/workflow/StateWorkflowTab.vue'
    import TagsTab from '@/components/config/workflow/TagsTab.vue'
    import TagWorkflowTab from '@/components/config/workflow/TagWorkflowTab.vue'

    const { t } = useI18n()
    const activeTab = useTabQuery(['states', 'state-workflow', 'tags', 'tag-workflow'], 'states')
</script>
