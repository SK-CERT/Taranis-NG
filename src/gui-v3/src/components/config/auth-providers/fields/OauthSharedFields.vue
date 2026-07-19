<template>
    <v-row>
        <v-col
            cols="12"
            md="4"
        >
            <v-text-field
                v-model="config.scopes"
                :label="t('auth_provider.scopes')"
                variant="outlined"
                density="comfortable"
                :placeholder="scopesPlaceholder"
                :disabled="saving"
            />
        </v-col>
        <v-col
            cols="12"
            md="4"
        >
            <v-text-field
                v-model="config.username_claim"
                :label="t('auth_provider.username_claim')"
                variant="outlined"
                density="comfortable"
                placeholder="preferred_username"
                :disabled="saving"
            />
        </v-col>
        <v-col
            cols="12"
            md="4"
        >
            <v-text-field
                v-model="config.email_claim"
                :label="t('auth_provider.email_claim')"
                variant="outlined"
                density="comfortable"
                placeholder="email"
                :disabled="saving"
            />
        </v-col>
        <v-col
            cols="12"
            md="6"
        >
            <v-text-field
                v-model="config.redirect_uri_override"
                :label="t('auth_provider.redirect_uri_override')"
                variant="outlined"
                density="comfortable"
                :hint="t('auth_provider.redirect_uri_hint')"
                persistent-hint
                :disabled="saving"
            />
        </v-col>
        <v-col
            cols="12"
            md="6"
        >
            <v-select
                v-model="config.pkce_method"
                :label="t('auth_provider.pkce_method')"
                variant="outlined"
                density="comfortable"
                :hint="t('auth_provider.pkce_method_hint')"
                persistent-hint
                :items="pkceMethodOptions"
                :disabled="saving"
            />
        </v-col>
        <v-col
            cols="12"
            md="6"
        >
            <v-text-field
                v-model="config.client_id"
                :label="t('auth_provider.client_id')"
                variant="outlined"
                density="comfortable"
                :rules="[(v) => !!v || t('error.required')]"
                :disabled="saving"
            />
        </v-col>
        <v-col
            cols="12"
            md="6"
        >
            <v-text-field
                v-model="secretModel"
                :label="t('auth_provider.secret')"
                variant="outlined"
                density="comfortable"
                type="password"
                autocomplete="new-password"
                :hint="hasSecret ? t('auth_provider.secret_keep_hint') : t('auth_provider.secret_hint')"
                persistent-hint
                :disabled="saving"
            />
        </v-col>
    </v-row>
</template>

<script setup lang="ts">
    /**
     * OauthSharedFields - the claim mapping, redirect/PKCE and client-secret
     * fields shared by the OIDC and OAuth2 provider kinds.
     *
     * Mutates the caller's `config` object in place (the project disables
     * `vue/no-mutating-props`, and the object is the same reactive reference the
     * parent owns), so no field-by-field events are needed.
     */
    import { computed } from 'vue'
    import { useI18n } from 'vue-i18n'
    import type { ProviderConfig } from '../types'

    const props = defineProps<{
        /** Shared reactive provider config (mutated in place). */
        config: ProviderConfig
        /** Disables every field while a save is in flight. */
        saving: boolean
        /** Whether a secret is already stored (changes the hint text). */
        hasSecret?: boolean
        /** Placeholder for the scopes field: "openid profile email" for OIDC, empty otherwise. */
        scopesPlaceholder?: string
    }>()

    const secretModel = defineModel<string>({ default: '' })
    const { t } = useI18n()

    const pkceMethodOptions = computed(() => [
        { title: t('auth_provider.pkce_method_none'), value: 'none' },
        { title: t('auth_provider.pkce_method_s256'), value: 'S256' },
        { title: t('auth_provider.pkce_method_plain'), value: 'plain' }
    ])
</script>
