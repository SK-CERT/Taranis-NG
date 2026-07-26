<template>
    <v-container>
        <v-card class="pa-6">
            <v-card-text>
                <v-alert
                    type="info"
                    variant="outlined"
                >
                    {{ t('common.coming_soon') }}
                </v-alert>
            </v-card-text>
        </v-card>
    </v-container>
</template>

<script setup lang="ts">
    import { useI18n } from 'vue-i18n'

    const { t } = useI18n()
</script>
