<template>
    <v-container>
        <v-card class="pa-6">
            <v-card-title class="text-h5">
                {{ $t('workflow.tags') }}
            </v-card-title>
            <v-card-text>
                <v-alert type="info" outlined>
                    {{ $t('workflow.tags_coming_soon') }}
                </v-alert>
                <p class="mt-4">
                    {{ $t('workflow.tags_description') }}
                </p>
            </v-card-text>
        </v-card>
    </v-container>
</template>

<script>
export default {
    name: "TagsTab",
    data() {
        return {
            // Placeholder for future tags functionality
        };
    }
}
</script>
