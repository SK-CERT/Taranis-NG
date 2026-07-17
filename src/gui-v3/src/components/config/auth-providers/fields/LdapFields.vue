<template>
    <v-row>
        <v-col
            cols="12"
            md="8"
            class="mb-n6"
        >
            <v-text-field
                v-model="config.server_url"
                :label="t('auth_provider.server_url')"
                variant="outlined"
                density="comfortable"
                placeholder="ldaps://ldap.example.org"
                :rules="[(v) => !!v || t('error.required')]"
                :disabled="saving"
            />
        </v-col>
        <v-col
            cols="12"
            md="4"
            class="mb-n6"
        >
            <v-switch
                v-model="config.use_tls"
                :label="t('auth_provider.use_tls')"
                color="primary"
                :disabled="saving"
            />
        </v-col>
        <v-col
            cols="12"
            class="mb-n4"
        >
            <v-textarea
                v-model="config.ca_cert"
                :label="t('auth_provider.ca_cert')"
                variant="outlined"
                density="comfortable"
                rows="3"
                :hint="t('auth_provider.ca_cert_hint')"
                persistent-hint
                :disabled="saving"
            />
        </v-col>

        <!-- Bind mode switch: Direct bind (bind as the user) vs Search & bind (service account).
             The backend derives the path from which field is set, checking user_dn_template
             first, so switching clears the other mode's fields to avoid ambiguity. -->
        <v-col cols="12">
            <v-switch
                v-model="bindMode"
                color="primary"
                hide-details
                :disabled="saving"
                :false-value="'direct'"
                :true-value="'search'"
                class="mb-n4"
            >
                <template #label>
                    <span class="text-body-2">
                        {{ bindMode === 'direct' ? t('auth_provider.ldap_bind_mode_direct') : t('auth_provider.ldap_bind_mode_search') }}
                    </span>
                    <v-icon
                        size="x-small"
                        class="ml-1"
                        :title="t('auth_provider.ldap_bind_mode_hint')"
                    >
                        {{ ICONS.INFORMATION_OUTLINE }}
                    </v-icon>
                </template>
            </v-switch>
        </v-col>

        <!-- Direct bind: bind as the user with a DN built from the template. No bind password. -->
        <v-col cols="12">
            <v-text-field
                v-if="bindMode === 'direct'"
                v-model="config.user_dn_template"
                :label="t('auth_provider.user_dn_template')"
                variant="outlined"
                density="comfortable"
                placeholder="ou=people,dc=example,dc=org"
                :hint="t('auth_provider.user_dn_template_hint')"
                persistent-hint
                :rules="[(v) => !!v || t('error.required')]"
                :disabled="saving"
            />
        </v-col>

        <!-- Search & bind: a service account binds, searches for the user, then rebinds
             as the discovered DN. The bind password travels in the provider secret column. -->
        <template v-if="bindMode === 'search'">
            <v-col
                cols="12"
                md="6"
            >
                <v-text-field
                    v-model="config.bind_dn"
                    :label="t('auth_provider.bind_dn')"
                    variant="outlined"
                    density="comfortable"
                    :hint="t('auth_provider.bind_dn_hint')"
                    persistent-hint
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
                    :label="t('auth_provider.bind_password')"
                    variant="outlined"
                    density="comfortable"
                    type="password"
                    autocomplete="new-password"
                    :hint="hasSecret ? t('auth_provider.secret_keep_hint') : t('auth_provider.secret_hint')"
                    persistent-hint
                    :disabled="saving"
                />
            </v-col>
            <v-col
                cols="12"
                md="6"
            >
                <v-text-field
                    v-model="config.search_base"
                    :label="t('auth_provider.search_base')"
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
                    v-model="config.search_filter"
                    :label="t('auth_provider.search_filter')"
                    variant="outlined"
                    density="comfortable"
                    placeholder="(uid={username})"
                    :disabled="saving"
                />
            </v-col>
        </template>

        <!-- Attribute mapping shared by both modes. -->
        <v-col
            cols="12"
            md="6"
        >
            <v-text-field
                v-model="config.username_attr"
                :label="t('auth_provider.username_attr')"
                variant="outlined"
                density="comfortable"
                placeholder="uid"
                :disabled="saving"
            />
        </v-col>
        <v-col
            cols="12"
            md="6"
        >
            <v-text-field
                v-model="config.name_attr"
                :label="t('auth_provider.name_attr')"
                variant="outlined"
                density="comfortable"
                placeholder="cn"
                :disabled="saving"
            />
        </v-col>
    </v-row>
</template>

<script setup lang="ts">
    /**
     * LdapFields - the LDAP connection, binding and attribute-mapping fields.
     *
     * A switch selects the bind mode, matching the two paths the backend's
     * LDAPAuthenticator.verify() takes at runtime:
     *
     *   Direct bind   - the user is authenticated by binding as a DN built from
     *                   `user_dn_template` with the user's own password. No bind
     *                   password is used.
     *   Search & bind - a service account (bind_dn + the stored bind password)
     *                   binds, searches `search_base`/`search_filter` for the
     *                   user, then rebinds as the discovered DN to verify it.
     *
     * The backend derives the path from which field is set, checking
     * `user_dn_template` first, so switching mode clears the *other* mode's
     * fields to keep the choice unambiguous (otherwise a populated
     * user_dn_template would silently shadow search & bind).
     *
     * The `config` object is mutated in place (the project disables
     * `vue/no-mutating-props`). The bind-password textarea is two-way bound via
     * defineModel (it is the provider `secret` column, not a config key). The
     * bind mode itself is UI-only — it is a local ref seeded ONCE from the loaded
     * config (so an existing provider reopens on the mode it uses), and nothing
     * about it is persisted as an explicit field.
     */
    import { ref, watch } from 'vue'
    import { useI18n } from 'vue-i18n'
    import { ICONS } from '@/config/ui-constants'
    import type { ProviderConfig } from '../types'

    /** The two bind modes, named to mirror the backend paths in ldap_authenticator.py. */
    type LdapBindMode = 'direct' | 'search'

    const props = defineProps<{
        /** Shared reactive provider config (mutated in place). */
        config: ProviderConfig
        /** Disables every field while a save is in flight. */
        saving: boolean
        /** Whether a bind password is already stored (changes the hint text). */
        hasSecret?: boolean
    }>()

    const secretModel = defineModel<string>({ default: '' })
    const { t } = useI18n()

    /**
     * The bind mode. A real local ref (not derived from config field presence)
     * so the switch can show an empty search form before the user has typed
     * anything into it. It is seeded ONCE from the loaded config so an existing
     * LDAP provider reopens on whichever mode it actually uses — direct bind if
     * user_dn_template is set (the backend checks it first), search & bind if
     * bind_dn + search_base are set, otherwise direct (the migration seed's mode).
     *
     * A watch clears the *other* mode's fields on change so the runtime branch
     * on `user_dn_template` can't pick the wrong path from leftover values —
     * user_dn_template is checked first, so a stale template would silently
     * shadow search & bind.
     */
    const initialMode: LdapBindMode = props.config.user_dn_template
        ? 'direct'
        : props.config.bind_dn && props.config.search_base
          ? 'search'
          : 'direct'
    const bindMode = ref<LdapBindMode>(initialMode)

    watch(bindMode, (mode, prev) => {
        if (mode === prev) {
            return
        }
        if (mode === 'direct') {
            // Leaving search & bind: drop its fields so user_dn_template is
            // the unambiguous selector the backend reads first.
            delete props.config.bind_dn
            delete props.config.search_base
            delete props.config.search_filter
        } else {
            // Leaving direct bind: drop user_dn_template so the backend
            // falls through to the bind_dn + search_base branch.
            delete props.config.user_dn_template
        }
    })
</script>
