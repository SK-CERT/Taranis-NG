<template>
    <v-container fluid>
        <v-tabs v-model="activeTab" background-color="transparent" color="primary">
            <v-tab>{{ $t('workflow.states_tab') }}</v-tab>
            <v-tab>{{ $t('workflow.state_workflow_tab') }}</v-tab>
            <v-tab>{{ $t('workflow.tags_tab') }}</v-tab>
            <v-tab>{{ $t('workflow.tag_workflow_tab') }}</v-tab>
        </v-tabs>

        <v-tabs-items v-model="activeTab">
            <v-tab-item>
                <StatesTab />
            </v-tab-item>

            <v-tab-item>
                <StateWorkflowTab />
            </v-tab-item>

            <v-tab-item>
                <TagsTab />
            </v-tab-item>

            <v-tab-item>
                <TagWorkflowTab />
            </v-tab-item>
        </v-tabs-items>
    </v-container>
</template>

<script>
import StatesTab from "@/components/config/workflow/StatesTab.vue";
import StateWorkflowTab from "@/components/config/workflow/StateWorkflowTab.vue";
import TagsTab from "@/components/config/workflow/TagsTab.vue";
import TagWorkflowTab from "@/components/config/workflow/TagWorkflowTab.vue";

export default {
    name: "WorkflowView",
    components: {
        StatesTab,
        StateWorkflowTab,
        TagsTab,
        TagWorkflowTab
    },
    data() {
        return {
            activeTab: 0
        };
    }
}
</script>
