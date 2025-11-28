<template>
    <v-container fluid>
        <v-tabs v-model="activeTab" background-color="transparent" color="primary">
            <v-tab>{{ $t('workflow.states_tab') }}</v-tab>
            <v-tab>{{ $t('workflow.state_workflow_tab') }}</v-tab>
            <v-tab>{{ $t('workflow.tags_tab') }}</v-tab>
            <v-tab>{{ $t('workflow.tag_workflow_tab') }}</v-tab>
        </v-tabs>

        <v-tabs-items v-model="activeTab">
            <!-- activeTab = 0 -> mounts/demounts tab -> fetch always new data on tab switch -->
            <v-tab-item>
                <StatesTab v-if="activeTab === 0" />
            </v-tab-item>

            <v-tab-item>
                <StateWorkflowTab v-if="activeTab === 1" />
            </v-tab-item>

            <v-tab-item>
                <TagsTab v-if="activeTab === 2" />
            </v-tab-item>

            <v-tab-item>
                <TagWorkflowTab v-if="activeTab === 3" />
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
