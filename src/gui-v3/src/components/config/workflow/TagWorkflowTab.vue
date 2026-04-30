<template>
  <v-container>
    <v-card class="pa-6">
      <v-card-title class="text-h5">
        {{ t('workflow.tag_workflow') }}
      </v-card-title>
      <v-card-text>
        <v-alert type="info" variant="outlined">
          {{ t('workflow.tag_workflow_coming_soon') }}
        </v-alert>
        <p class="mt-4">
          {{ t('workflow.tag_workflow_description') }}
        </p>
      </v-card-text>
    </v-card>
  </v-container>
</template>

<script setup>
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
</script>
