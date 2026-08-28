<template>
    <v-row>
        <v-col cols="12">
            <v-text-field
                v-model="config.issuer_url"
                dir="ltr"
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
    <v-row>
        <v-col cols="12">
            <v-text-field
                v-model="config.internal_issuer_url"
                dir="ltr"
                :label="t('auth_provider.internal_issuer_url')"
                variant="outlined"
                density="comfortable"
                :hint="t('auth_provider.internal_issuer_url_hint')"
                persistent-hint
                :rules="[internalIssuerRule]"
                :disabled="saving"
            />
        </v-col>
    </v-row>
    <v-row v-if="config.internal_issuer_url">
        <v-col cols="12">
            <v-checkbox
                v-model="allowInsecureInternalTransport"
                :label="t('auth_provider.allow_insecure_internal_transport')"
                :hint="t('auth_provider.allow_insecure_internal_transport_hint')"
                persistent-hint
                color="primary"
                density="comfortable"
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
    import { computed } from 'vue'
    import { useI18n } from 'vue-i18n'
    import type { ProviderConfig } from '../types'

    const props = defineProps<{
        /** Shared reactive provider config (mutated in place). */
        config: ProviderConfig
        /** Disables every field while a save is in flight. */
        saving: boolean
    }>()

    const { t } = useI18n()

    const allowInsecureInternalTransport = computed({
        get: () => props.config.allow_insecure_internal_transport ?? false,
        set: (value: boolean) => {
            props.config.allow_insecure_internal_transport = value
        }
    })

    function internalIssuerRule(value: string): true | string {
        if (!value || !value.trim()) return true
        if (value.trim().toLowerCase().startsWith('http://') && !props.config.allow_insecure_internal_transport) {
            return t('auth_provider.internal_issuer_url_requires_https')
        }
        return true
    }
</script>
