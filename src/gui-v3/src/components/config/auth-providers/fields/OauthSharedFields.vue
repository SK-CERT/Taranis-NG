<template>
    <v-row>
        <v-col
            v-if="redirectUri"
            cols="12"
        >
            <v-alert
                type="info"
                variant="tonal"
                density="compact"
                data-test="oauth-callback-uri"
            >
                <div class="d-flex flex-wrap align-center ga-2">
                    <div class="flex-grow-1">
                        <div class="text-subtitle-2">{{ t('auth_provider.callback_uri') }}</div>
                        <code
                            dir="ltr"
                            data-test="oauth-callback-uri-value"
                            >{{ redirectUri }}</code
                        >
                    </div>
                    <v-btn
                        variant="text"
                        size="small"
                        prepend-icon="mdi-content-copy"
                        :aria-label="t('auth_provider.copy_callback_uri')"
                        data-test="copy-oauth-callback-uri"
                        @click="copyRedirectUri"
                    >
                        {{ t('auth_provider.copy_callback_uri') }}
                    </v-btn>
                </div>
            </v-alert>
        </v-col>
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
                dir="ltr"
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
                v-model="pkceMethod"
                :label="t('auth_provider.pkce_method')"
                variant="outlined"
                density="comfortable"
                :hint="t('auth_provider.pkce_method_hint')"
                persistent-hint
                :items="pkceMethodOptions"
                :disabled="saving"
            />
            <v-alert
                v-if="pkceMethod === 'plain'"
                type="warning"
                variant="tonal"
                density="compact"
                class="mt-2"
                data-test="pkce-plain-warning"
            >
                {{ t('auth_provider.pkce_plain_warning') }}
            </v-alert>
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
        /** Derived callback URI to register with either an OIDC or OAuth2 provider. */
        redirectUri?: string
    }>()

    const secretModel = defineModel<string>({ default: '' })
    const { t } = useI18n()

    const pkceMethod = computed({
        get: () => {
            const configured = props.config.pkce_method
            return configured === 'none' || configured === 'plain' || configured === 'S256' ? configured : 'S256'
        },
        set: (value: string) => {
            props.config.pkce_method = value
        }
    })

    const pkceMethodOptions = computed(() => [
        { title: t('auth_provider.pkce_method_none'), value: 'none' },
        { title: t('auth_provider.pkce_method_s256'), value: 'S256' },
        { title: t('auth_provider.pkce_method_plain'), value: 'plain' }
    ])

    const copyRedirectUri = async (): Promise<void> => {
        if (!props.redirectUri) {
            return
        }
        try {
            await navigator.clipboard.writeText(props.redirectUri)
            window.dispatchEvent(new CustomEvent('notification', { detail: { type: 'success', loc: 'auth_provider.callback_uri_copied' } }))
        } catch (error) {
            console.error('Could not copy the OAuth callback URI:', error)
        }
    }
</script>
