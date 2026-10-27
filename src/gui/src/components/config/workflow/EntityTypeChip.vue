<template>
    <v-chip
        label
        :color="color"
    >
        <v-icon start>
            {{ icon }}
        </v-icon>
        {{ t(`workflow.entity_types.${entityType}`) }}
    </v-chip>
</template>

<script setup lang="ts">
    import { computed } from 'vue'
    import { useI18n } from 'vue-i18n'

    /** What a workflow row applies to (reports or products), as the State and Tag Workflow tables show it. */

    const props = defineProps<{ entityType: string }>()

    const { t } = useI18n()

    // Data defaults for user-created entities, deliberately theme-independent.
    const COLORS: Record<string, string> = { report_item: '#2196F3', product: '#4CAF50' }
    const ICONS: Record<string, string> = { report_item: 'mdi-file-document', product: 'mdi-package-variant' }

    const color = computed(() => COLORS[props.entityType] ?? 'grey')
    const icon = computed(() => ICONS[props.entityType] ?? 'mdi-help')
</script>
