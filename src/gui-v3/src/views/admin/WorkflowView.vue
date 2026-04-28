<template>
  <v-container fluid class="pa-0">
    <v-tabs v-model="activeTab" bg-color="transparent" color="primary">
      <v-tab value="states">{{ t('workflow.states_tab') }}</v-tab>
      <v-tab value="state-workflow">{{ t('workflow.state_workflow_tab') }}</v-tab>
      <v-tab value="tags">{{ t('workflow.tags_tab') }}</v-tab>
      <v-tab value="tag-workflow">{{ t('workflow.tag_workflow_tab') }}</v-tab>
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

<script setup>
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import StatesTab from '@/components/config/workflow/StatesTab.vue'
import StateWorkflowTab from '@/components/config/workflow/StateWorkflowTab.vue'
import TagsTab from '@/components/config/workflow/TagsTab.vue'
import TagWorkflowTab from '@/components/config/workflow/TagWorkflowTab.vue'

const { t } = useI18n()
const activeTab = ref('states')
</script>
