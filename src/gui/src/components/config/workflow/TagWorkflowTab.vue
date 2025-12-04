<template>
    <v-container>
        <v-card class="pa-6">
            <v-card-title class="text-h5">
                {{ $t('workflow.tag_workflow') }}
            </v-card-title>
            <v-card-text>
                <v-alert type="info" outlined>
                    {{ $t('workflow.tag_workflow_coming_soon') }}
                </v-alert>
                <p class="mt-4">
                    {{ $t('workflow.tag_workflow_description') }}
                </p>
            </v-card-text>
        </v-card>
    </v-container>
</template>

<script>
export default {
    name: "TagWorkflowTab",
    data() {
        return {
            // Placeholder for future tag workflow functionality
        };
    }
}
</script>
