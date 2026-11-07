<template>
    <v-container fluid>
        <v-card>
            <v-card-text>
                <p class="text-body-2 text-medium-emphasis mb-4">{{ t('api_keys.tab_description') }}</p>
                <ApiKeysPanel mode="admin" />
            </v-card-text>
        </v-card>
    </v-container>
</template>

<script setup lang="ts">
    import { useI18n } from 'vue-i18n'
    import ApiKeysPanel from '@/components/common/api-keys/ApiKeysPanel.vue'

    const { t } = useI18n()
</script>
