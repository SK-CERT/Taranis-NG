<template>
    <v-row>
        <v-col cols="12">
            <v-text-field
                v-model="config.issuer_url"
                :label="t('auth_provider.issuer_url')"
                variant="outlined"
                density="comfortable"
                :hint="t('auth_provider.issuer_url_hint')"
                persistent-hint
                :rules="[(v) => !!v || t('error.required')]"
                :disabled="saving"
            />
        </v-col>
    </v-row>
</template>

<script setup lang="ts">
    /**
     * OidcFields - the issuer and client-id fields specific to the OIDC kind.
     * Mutates the caller's `config` object in place (see OauthSharedFields.vue).
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
