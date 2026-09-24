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
                ref="internalIssuerFieldRef"
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
    <v-row>
        <v-col cols="12">
            <v-checkbox
                v-model="allowInsecureInternalTransport"
                :label="t('auth_provider.allow_insecure_internal_transport')"
                :hint="t('auth_provider.allow_insecure_internal_transport_hint')"
                persistent-hint
                color="primary"
                density="comfortable"
                :disabled="saving || !hasInternalIssuer"
            />
        </v-col>
    </v-row>
</template>

<script setup lang="ts">
    /**
     * OidcFields - the issuer and client-id fields specific to the OIDC kind.
     * Mutates the caller's `config` object in place (see OauthSharedFields.vue).
     */
    import { computed, ref, watch } from 'vue'
    import { useI18n } from 'vue-i18n'
    import type { ProviderConfig } from '../types'

    const props = defineProps<{
        /** Shared reactive provider config (mutated in place). */
        config: ProviderConfig
        /** Disables every field while a save is in flight. */
        saving: boolean
    }>()

    const { t } = useI18n()

    const hasInternalIssuer = computed(() => Boolean(props.config.internal_issuer_url?.trim?.()))

    const allowInsecureInternalTransport = computed({
        get: () => props.config.allow_insecure_internal_transport ?? false,
        set: (value: boolean) => {
            props.config.allow_insecure_internal_transport = value
        }
    })

    // The opt-in only has an effect while an internal issuer is set; when the
    // URL is cleared, drop the flag too so a later re-added URL cannot silently
    // resurrect the insecure transport the admin had switched off.
    watch(hasInternalIssuer, (present) => {
        if (!present && props.config.allow_insecure_internal_transport) {
            props.config.allow_insecure_internal_transport = false
        }
    })

    // `internalIssuerRule` reads the opt-in, but Vuetify only re-runs a field's
    // rules when the field's own value or focus changes - never when the rules'
    // dependencies do. Without this the "must use https" error stays on screen
    // after the admin ticks the box that permits exactly that.
    const internalIssuerFieldRef = ref<{ validate: () => unknown } | null>(null)
    watch(allowInsecureInternalTransport, () => {
        void internalIssuerFieldRef.value?.validate()
    })

    function internalIssuerRule(value: string): true | string {
        if (!value || !value.trim()) return true
        if (value.trim().toLowerCase().startsWith('http://') && !props.config.allow_insecure_internal_transport) {
            return t('auth_provider.internal_issuer_url_requires_https')
        }
        return true
    }
</script>
