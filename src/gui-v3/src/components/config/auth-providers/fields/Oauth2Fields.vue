<template>
    <v-row>
        <v-col
            cols="12"
            md="4"
        >
            <v-text-field
                v-model="config.authorize_url"
                :label="t('auth_provider.authorize_url')"
                variant="outlined"
                density="comfortable"
                :rules="[(v) => !!v || t('error.required')]"
                :disabled="saving"
            />
        </v-col>
        <v-col
            cols="12"
            md="4"
        >
            <v-text-field
                v-model="config.token_url"
                :label="t('auth_provider.token_url')"
                variant="outlined"
                density="comfortable"
                :rules="[(v) => !!v || t('error.required')]"
                :disabled="saving"
            />
        </v-col>
        <v-col
            cols="12"
            md="4"
        >
            <v-text-field
                v-model="config.userinfo_url"
                :label="t('auth_provider.userinfo_url')"
                variant="outlined"
                density="comfortable"
                :rules="[(v) => !!v || t('error.required')]"
                :disabled="saving"
            />
        </v-col>
    </v-row>
</template>

<script setup lang="ts">
    /**
     * Oauth2Fields - the authorize/token/userinfo and client-id fields specific
     * to the OAuth2 kind. Mutates the caller's `config` object in place.
     */
    import { useI18n } from 'vue-i18n'
    import type { ProviderConfig } from '../types'

    defineProps<{
        /** Shared reactive provider config (mutated in place). */
        config: ProviderConfig
        /** Disables every field while a save is in flight. */
        saving: boolean
    }>()

    const { t } = useI18n()
</script>
