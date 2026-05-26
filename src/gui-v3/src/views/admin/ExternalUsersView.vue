<template>
    <v-container fluid>
        <v-card>
            <v-card-title>
                <v-icon left>
                    {{ ICONS.WRENCH }}
                </v-icon>
                {{ viewName }}
            </v-card-title>
            <v-card-text>
                <v-alert type="info" variant="tonal">This view is under migration from Vue 2 to Vue 3.</v-alert>
            </v-card-text>
        </v-card>
    </v-container>
</template>

<script setup lang="ts">
    import { computed } from 'vue'
    import { useRoute } from 'vue-router'
    import { ICONS } from '@/config/ui-constants'

    const route = useRoute()
    const viewName = computed(() => String(route.name || 'View'))
</script>
