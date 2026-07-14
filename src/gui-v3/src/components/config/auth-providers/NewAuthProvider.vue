<template>
    <v-dialog
        v-model="dialog"
        max-width="900"
        persistent
        scrollable
        @keydown.esc="requestClose"
    >
        <template #activator="{ props: activatorProps }">
            <AddNewButton
                :show="canCreate"
                v-bind="activatorProps"
            />
        </template>

        <v-card>
            <DialogToolbar
                :title="isEdit ? t('auth_provider.edit') : t('auth_provider.add_new')"
                :saving="saving"
                @cancel="requestClose"
                @save="saveAndClose"
            />

            <v-card-text>
                <v-form
                    ref="formRef"
                    @submit.prevent="saveAndClose"
                >
                    <v-row>
                        <v-col
                            cols="12"
                            md="6"
                        >
                            <v-text-field
                                v-model="localItem.name"
                                :label="t('auth_provider.name')"
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
                            <v-select
                                v-model="localItem.kind"
                                :items="kindOptions"
                                :label="t('auth_provider.kind')"
                                variant="outlined"
                                density="comfortable"
                                :disabled="saving || isEdit"
                                :rules="[(v) => !!v || t('error.required')]"
                            />
                        </v-col>
                        <v-col
                            cols="12"
                            md="2"
                        >
                            <v-switch
                                v-model="localItem.enabled"
                                :label="t('auth_provider.enabled')"
                                color="primary"
                                :disabled="saving"
                            />
                        </v-col>
                    </v-row>

                    <!-- Provisioning (external kinds only) -->
                    <template v-if="isExternalKind">
                        <v-divider class="mb-4" />
                        <v-row>
                            <v-col
                                cols="12"
                                md="4"
                            >
                                <v-select
                                    v-model="localItem.provisioning_mode"
                                    :items="provisioningOptions"
                                    :label="t('auth_provider.provisioning_mode')"
                                    variant="outlined"
                                    density="comfortable"
                                    :hint="t('auth_provider.provisioning_mode_hint')"
                                    persistent-hint
                                    :disabled="saving"
                                />
                            </v-col>
                            <v-col
                                cols="12"
                                md="4"
                            >
                                <v-text-field
                                    v-model="localItem.allowed_domains"
                                    :label="t('auth_provider.allowed_domains')"
                                    variant="outlined"
                                    density="comfortable"
                                    :hint="t('auth_provider.allowed_domains_hint')"
                                    persistent-hint
                                    :disabled="saving || !isAutoCreate"
                                />
                            </v-col>
                            <v-col
                                cols="12"
                                md="4"
                            >
                                <v-select
                                    v-model="organizationId"
                                    :items="organizations"
                                    item-title="name"
                                    item-value="id"
                                    :label="t('auth_provider.organization')"
                                    variant="outlined"
                                    density="comfortable"
                                    clearable
                                    :hint="t('auth_provider.organization_hint')"
                                    persistent-hint
                                    :disabled="saving"
                                />
                            </v-col>
                        </v-row>
                    </template>

                    <!-- MFA requirement (form-based kinds) -->
                    <v-row v-if="localItem.kind === 'local' || localItem.kind === 'ldap'">
                        <v-col cols="12">
                            <v-switch
                                v-model="localItem.require_mfa"
                                :label="t('auth_provider.require_mfa')"
                                color="primary"
                                :hint="t('auth_provider.require_mfa_hint')"
                                persistent-hint
                                :disabled="saving"
                            />
                        </v-col>
                    </v-row>

                    <!-- OIDC fields -->
                    <template v-if="localItem.kind === 'oidc'">
                        <v-divider class="mb-4" />
                        <v-row>
                            <v-col
                                cols="12"
                                md="8"
                            >
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
                            <v-col
                                cols="12"
                                md="4"
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
                        </v-row>
                    </template>

                    <!-- OAuth2 fields -->
                    <template v-if="localItem.kind === 'oauth2'">
                        <v-divider class="mb-4" />
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
                            <v-col
                                cols="12"
                                md="4"
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
                        </v-row>
                    </template>

                    <!-- Shared OIDC/OAuth2 claim mapping + secret -->
                    <template v-if="localItem.kind === 'oidc' || localItem.kind === 'oauth2'">
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
                                    :placeholder="localItem.kind === 'oidc' ? 'openid profile email' : ''"
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
                                    v-model="secretInput"
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

                    <!-- SAML 2.0 fields -->
                    <template v-if="localItem.kind === 'saml'">
                        <v-divider class="mb-4" />

                        <!-- The three fields below all live in the IdP's metadata; read them
                             out of it rather than making the admin copy them by hand. -->
                        <v-row>
                            <v-col cols="12">
                                <v-textarea
                                    v-model="metadataInput"
                                    :label="t('auth_provider.idp_metadata')"
                                    variant="outlined"
                                    density="comfortable"
                                    rows="2"
                                    auto-grow
                                    :hint="t('auth_provider.idp_metadata_hint')"
                                    persistent-hint
                                    :disabled="saving || importing"
                                >
                                    <template #append>
                                        <v-btn
                                            color="primary"
                                            variant="flat"
                                            :loading="importing"
                                            :disabled="!metadataInput.trim() || saving"
                                            @click="loadMetadata"
                                        >
                                            {{ t('auth_provider.idp_metadata_load') }}
                                        </v-btn>
                                    </template>
                                </v-textarea>
                            </v-col>
                            <v-col
                                v-if="metadataMessage"
                                cols="12"
                                class="pt-0"
                            >
                                <v-alert
                                    :type="metadataError ? 'error' : 'success'"
                                    density="compact"
                                    variant="tonal"
                                >
                                    {{ metadataMessage }}
                                </v-alert>
                            </v-col>
                        </v-row>

                        <v-row>
                            <v-col
                                cols="12"
                                md="6"
                            >
                                <v-text-field
                                    v-model="config.idp_sso_url"
                                    :label="t('auth_provider.idp_sso_url')"
                                    variant="outlined"
                                    density="comfortable"
                                    placeholder="https://idp.example.org/sso/redirect"
                                    :hint="t('auth_provider.idp_sso_url_hint')"
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
                                    v-model="config.idp_entity_id"
                                    :label="t('auth_provider.idp_entity_id')"
                                    variant="outlined"
                                    density="comfortable"
                                    placeholder="https://idp.example.org/metadata"
                                    :hint="t('auth_provider.idp_entity_id_hint')"
                                    persistent-hint
                                    :rules="[(v) => !!v || t('error.required')]"
                                    :disabled="saving"
                                />
                            </v-col>
                            <v-col cols="12">
                                <v-textarea
                                    v-model="config.idp_certificate"
                                    :label="t('auth_provider.idp_certificate')"
                                    variant="outlined"
                                    density="comfortable"
                                    rows="3"
                                    :hint="t('auth_provider.idp_certificate_hint')"
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
                                    v-model="config.sp_entity_id"
                                    :label="t('auth_provider.sp_entity_id')"
                                    variant="outlined"
                                    density="comfortable"
                                    placeholder="taranis-ng"
                                    :hint="t('auth_provider.sp_entity_id_hint')"
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
                                    v-model="config.acs_url_override"
                                    :label="t('auth_provider.acs_url_override')"
                                    variant="outlined"
                                    density="comfortable"
                                    :hint="t('auth_provider.acs_url_hint')"
                                    persistent-hint
                                    :disabled="saving"
                                />
                            </v-col>
                            <v-col cols="12">
                                <v-text-field
                                    v-model="config.external_id_attr"
                                    :label="t('auth_provider.external_id_attr')"
                                    variant="outlined"
                                    density="comfortable"
                                    :hint="t('auth_provider.external_id_attr_hint')"
                                    persistent-hint
                                    :disabled="saving"
                                />
                            </v-col>
                            <v-col
                                cols="12"
                                md="4"
                            >
                                <v-text-field
                                    v-model="config.username_attr"
                                    :label="t('auth_provider.username_attr')"
                                    variant="outlined"
                                    density="comfortable"
                                    :hint="t('auth_provider.saml_username_attr_hint')"
                                    persistent-hint
                                    :disabled="saving"
                                />
                            </v-col>
                            <v-col
                                cols="12"
                                md="4"
                            >
                                <v-text-field
                                    v-model="config.name_attr"
                                    :label="t('auth_provider.name_attr')"
                                    variant="outlined"
                                    density="comfortable"
                                    :hint="t('auth_provider.saml_attr_hint')"
                                    persistent-hint
                                    :disabled="saving"
                                />
                            </v-col>
                            <v-col
                                cols="12"
                                md="4"
                            >
                                <v-text-field
                                    v-model="config.email_attr"
                                    :label="t('auth_provider.email_attr')"
                                    variant="outlined"
                                    density="comfortable"
                                    :hint="t('auth_provider.saml_attr_hint')"
                                    persistent-hint
                                    :disabled="saving"
                                />
                            </v-col>
                        </v-row>

                        <!-- Service provider keypair: the certificate an identity provider
                             encrypts the assertion to, and a registration form asks for. -->
                        <v-divider class="my-4" />
                        <div class="d-flex align-center mb-2">
                            <span class="text-subtitle-2">{{ t('auth_provider.sp_keypair') }}</span>
                            <v-chip
                                v-if="hasSecret && !secretInput"
                                size="x-small"
                                color="success"
                                variant="tonal"
                                class="ml-2"
                            >
                                {{ t('auth_provider.sp_keypair_stored') }}
                            </v-chip>
                            <v-spacer />
                            <v-btn
                                color="primary"
                                variant="flat"
                                size="small"
                                prepend-icon="mdi-key-plus"
                                :loading="generatingKeypair"
                                :disabled="saving"
                                @click="generateKeypair"
                            >
                                {{ t('auth_provider.sp_keypair_generate') }}
                            </v-btn>
                        </div>

                        <v-row>
                            <v-col cols="12">
                                <v-textarea
                                    v-model="secretInput"
                                    :label="t('auth_provider.sp_private_key')"
                                    variant="outlined"
                                    density="comfortable"
                                    rows="2"
                                    :hint="hasSecret ? t('auth_provider.secret_keep_hint') : t('auth_provider.sp_private_key_hint')"
                                    persistent-hint
                                    :disabled="saving"
                                />
                            </v-col>
                            <v-col cols="12">
                                <v-textarea
                                    v-model="config.sp_certificate"
                                    :label="t('auth_provider.sp_certificate')"
                                    variant="outlined"
                                    density="comfortable"
                                    rows="3"
                                    :hint="t('auth_provider.sp_certificate_hint')"
                                    persistent-hint
                                    :disabled="saving"
                                />
                            </v-col>
                        </v-row>

                        <!-- The URLs to hand to the identity provider. Both contain the
                             provider id, so they only exist once the provider is saved. -->
                        <v-alert
                            v-if="isEdit"
                            type="info"
                            variant="tonal"
                            density="compact"
                            class="mt-2"
                        >
                            <div class="text-subtitle-2 mb-1">{{ t('auth_provider.saml_idp_urls') }}</div>
                            <div class="text-body-2">
                                <strong>{{ t('auth_provider.saml_metadata_url') }}:</strong>
                                <code class="ml-1">{{ samlMetadataUrl }}</code>
                            </div>
                            <div class="text-body-2">
                                <strong>{{ t('auth_provider.saml_acs_url') }}:</strong>
                                <code class="ml-1">{{ samlAcsUrl }}</code>
                            </div>
                        </v-alert>
                    </template>

                    <!-- LDAP fields -->
                    <template v-if="localItem.kind === 'ldap'">
                        <v-divider class="mb-4" />
                        <v-row>
                            <v-col
                                cols="12"
                                md="8"
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
                            >
                                <v-switch
                                    v-model="config.use_tls"
                                    :label="t('auth_provider.use_tls')"
                                    color="primary"
                                    :disabled="saving"
                                />
                            </v-col>
                            <v-col cols="12">
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
                            <v-col cols="12">
                                <v-text-field
                                    v-model="config.user_dn_template"
                                    :label="t('auth_provider.user_dn_template')"
                                    variant="outlined"
                                    density="comfortable"
                                    placeholder="uid={username},ou=people,dc=example,dc=org"
                                    :hint="t('auth_provider.user_dn_template_hint')"
                                    persistent-hint
                                    :disabled="saving"
                                />
                            </v-col>
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
                                    :disabled="saving"
                                />
                            </v-col>
                            <v-col
                                cols="12"
                                md="6"
                            >
                                <v-text-field
                                    v-model="secretInput"
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
                                md="4"
                            >
                                <v-text-field
                                    v-model="config.search_base"
                                    :label="t('auth_provider.search_base')"
                                    variant="outlined"
                                    density="comfortable"
                                    :disabled="saving"
                                />
                            </v-col>
                            <v-col
                                cols="12"
                                md="4"
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
                            <v-col
                                cols="12"
                                md="2"
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
                                md="2"
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

                    <!-- Default roles for auto-created users (only meaningful when auto-creation is on) -->
                    <template v-if="isExternalKind">
                        <v-divider class="my-4" />
                        <EntitySelectTable
                            v-model="selectedRoles"
                            :title="t('auth_provider.default_roles')"
                            :items="roles"
                            :headers="roleHeaders"
                            :disabled="saving || !isAutoCreate"
                        />
                    </template>

                    <v-alert
                        v-if="showValidationError"
                        type="error"
                        density="compact"
                        class="mb-3 mt-4"
                    >
                        {{ t('error.validation') }}
                    </v-alert>

                    <v-alert
                        v-if="showError"
                        type="error"
                        density="compact"
                        class="mb-3 mt-4"
                    >
                        {{ t('auth_provider.error') }}
                    </v-alert>
                </v-form>
            </v-card-text>
        </v-card>

        <UnsavedChangesDialog
            v-model="confirmVisible"
            @continue="continueEditing"
            @save="saveAndClose"
            @discard="discardAndClose"
        />
    </v-dialog>
</template>

<script setup lang="ts">
    import { ref, computed, watch, onMounted } from 'vue'
    import { useI18n } from 'vue-i18n'
    import AddNewButton from '@/components/common/buttons/AddNewButton.vue'
    import DialogToolbar from '@/components/common/dialogs/DialogToolbar.vue'
    import UnsavedChangesDialog from '@/components/common/dialogs/UnsavedChangesDialog.vue'
    import EntitySelectTable from '@/components/common/EntitySelectTable.vue'
    import { useUnsavedChanges } from '@/composables/useUnsavedChanges'
    import { useAuth } from '@/composables/useAuth'
    import {
        createNewAuthProvider,
        updateAuthProvider,
        getAllOrganizations,
        getAllRoles,
        importSamlMetadata,
        generateSamlKeypair
    } from '@/api/config'

    type ProviderConfig = {
        issuer_url?: string
        client_id?: string
        scopes?: string
        username_claim?: string
        name_claim?: string
        email_claim?: string
        redirect_uri_override?: string
        logout_url?: string
        pkce_method?: string
        authorize_url?: string
        token_url?: string
        userinfo_url?: string
        server_url?: string
        use_tls?: boolean
        ca_cert?: string
        user_dn_template?: string
        bind_dn?: string
        search_base?: string
        search_filter?: string
        username_attr?: string
        name_attr?: string
        email_attr?: string
        external_id_attr?: string
        nameid_format?: string
        idp_sso_url?: string
        idp_entity_id?: string
        idp_certificate?: string
        sp_entity_id?: string
        sp_certificate?: string
        acs_url_override?: string
    }

    type AuthProviderItem = {
        id: string | number | null
        name: string
        kind: string
        enabled: boolean
        provisioning_mode: string
        allowed_domains: string
        require_mfa: boolean
        organization?: { id: number; name?: string } | null
        default_roles?: Array<{ id: number; name?: string }>
        config?: ProviderConfig
        has_secret?: boolean
        [key: string]: unknown
    }

    type SelectableEntity = {
        id: string | number
        name?: string
        description?: string
        [key: string]: unknown
    }

    type ListResponse = {
        data?: {
            items?: SelectableEntity[]
        }
    }

    type FormValidationResult = {
        valid: boolean
    }

    const props = withDefaults(
        defineProps<{
            modelValue?: boolean
            editItem?: Record<string, unknown> | null
        }>(),
        {
            modelValue: false,
            editItem: null
        }
    )

    const emit = defineEmits<{
        (e: 'update:modelValue', value: boolean): void
        (e: 'saved'): void
    }>()

    const { t } = useI18n()
    const { checkPermission } = useAuth()

    const dialog = ref(false)
    const formRef = ref<any>(null)
    const saving = ref(false)
    const showValidationError = ref(false)
    const showError = ref(false)

    const organizations = ref<SelectableEntity[]>([])
    const roles = ref<SelectableEntity[]>([])

    const defaultItem: AuthProviderItem = {
        id: null,
        name: '',
        kind: 'oidc',
        enabled: true,
        provisioning_mode: 'manual',
        allowed_domains: '',
        require_mfa: false
    }

    const localItem = ref<AuthProviderItem>({ ...defaultItem })
    const config = ref<ProviderConfig>({})
    const organizationId = ref<number | null>(null)
    const selectedRoles = ref<Array<string | number>>([])
    const secretInput = ref('')

    const isEdit = computed(() => !!localItem.value.id)
    const canCreate = computed(() => checkPermission('CONFIG_AUTH_PROVIDER_CREATE'))
    const hasSecret = computed(() => !!localItem.value.has_secret)
    const isExternalKind = computed(() => ['oidc', 'oauth2', 'saml', 'ldap'].includes(localItem.value.kind))

    // Reading the IdP metadata fills in the three fields it contains, so nobody has to
    // copy an entityID, an SSO endpoint and a base64 certificate out of an XML document.
    const metadataInput = ref('')
    const importing = ref(false)
    const metadataMessage = ref('')
    const metadataError = ref(false)

    const loadMetadata = async (): Promise<void> => {
        const value = metadataInput.value.trim()
        if (!value) {
            return
        }
        importing.value = true
        metadataMessage.value = ''
        metadataError.value = false
        try {
            // a document starts with '<'; anything else is treated as a URL to fetch
            const payload = value.startsWith('<') ? { xml: value } : { url: value }
            const response = (await importSamlMetadata(payload)) as {
                data: { idp_entity_id: string; idp_sso_url: string; idp_certificate: string; certificate_count: number }
            }
            config.value.idp_entity_id = response.data.idp_entity_id
            config.value.idp_sso_url = response.data.idp_sso_url
            config.value.idp_certificate = response.data.idp_certificate
            metadataMessage.value = t('auth_provider.idp_metadata_loaded', { count: response.data.certificate_count })
        } catch (error) {
            const data = (error as { response?: { data?: { error?: string } } })?.response?.data
            metadataMessage.value = data?.error || t('auth_provider.idp_metadata_error')
            metadataError.value = true
        } finally {
            importing.value = false
        }
    }

    // The identity provider encrypts the assertion to this certificate, so the keypair is
    // generated server-side; the private key rides along in the write-only `secret` field.
    const generatingKeypair = ref(false)

    const generateKeypair = async (): Promise<void> => {
        generatingKeypair.value = true
        try {
            const response = (await generateSamlKeypair(config.value.sp_entity_id || '')) as {
                data: { private_key: string; certificate: string }
            }
            secretInput.value = response.data.private_key
            config.value.sp_certificate = response.data.certificate
            window.dispatchEvent(new CustomEvent('notification', { detail: { type: 'success', loc: 'auth_provider.sp_keypair_generated' } }))
        } catch (error) {
            console.error('Error generating the SAML keypair:', error)
            window.dispatchEvent(new CustomEvent('notification', { detail: { type: 'error', loc: 'common.error_saving' } }))
        } finally {
            generatingKeypair.value = false
        }
    }

    // The URLs an identity provider needs when registering this SP. The backend derives
    // the ACS from the request (or from acs_url_override), so mirror that here.
    const samlAcsUrl = computed(() => {
        const override = (config.value.acs_url_override || '').trim()
        return override || `${window.location.origin}/api/v1/auth/saml/${localItem.value.id}/acs`
    })
    const samlMetadataUrl = computed(() => `${window.location.origin}/api/v1/auth/saml/${localItem.value.id}/metadata`)
    // Auto-creation settings (domain filter, default roles) only apply when unknown users get accounts
    const isAutoCreate = computed(() => localItem.value.provisioning_mode !== 'manual')

    const kindOptions = computed(() => [
        { title: t('auth_provider.kinds.local'), value: 'local' },
        { title: t('auth_provider.kinds.oidc'), value: 'oidc' },
        { title: t('auth_provider.kinds.oauth2'), value: 'oauth2' },
        { title: t('auth_provider.kinds.saml'), value: 'saml' },
        { title: t('auth_provider.kinds.ldap'), value: 'ldap' }
    ])

    const provisioningOptions = computed(() => [
        { title: t('auth_provider.provisioning.manual'), value: 'manual' },
        { title: t('auth_provider.provisioning.approval'), value: 'approval' },
        { title: t('auth_provider.provisioning.automatic'), value: 'automatic' }
    ])

    const pkceMethodOptions = computed(() => [
        { title: t('auth_provider.pkce_method_none'), value: 'none' },
        { title: t('auth_provider.pkce_method_s256'), value: 'S256' },
        { title: t('auth_provider.pkce_method_plain'), value: 'plain' }
    ])

    const roleHeaders = [
        { title: t('auth_provider.role_name'), key: 'name' },
        { title: t('auth_provider.role_description'), key: 'description' }
    ]

    watch(
        () => props.editItem,
        (newVal) => {
            if (newVal) {
                const incoming = JSON.parse(JSON.stringify(newVal)) as Partial<AuthProviderItem>
                localItem.value = { ...defaultItem, ...incoming }
                config.value = { ...(incoming.config || {}) }
                organizationId.value = incoming.organization?.id ?? null
                selectedRoles.value = (incoming.default_roles || []).map((role) => role.id)
                secretInput.value = ''
                dialog.value = true
            }
        },
        { immediate: true, deep: true }
    )

    watch(dialog, (newVal) => {
        if (!newVal) {
            resetForm()
        } else {
            capture()
        }
        emit('update:modelValue', newVal)
    })

    const resetForm = (): void => {
        localItem.value = { ...defaultItem }
        config.value = {}
        metadataInput.value = ''
        metadataMessage.value = ''
        metadataError.value = false
        organizationId.value = null
        selectedRoles.value = []
        secretInput.value = ''
        showValidationError.value = false
        showError.value = false
        if (formRef.value) {
            formRef.value.resetValidation()
        }
    }

    const closeDialog = (): void => {
        dialog.value = false
    }

    const buildConfig = (): ProviderConfig => {
        const kind = localItem.value.kind
        const source = config.value
        const pick = (keys: Array<keyof ProviderConfig>): ProviderConfig => {
            const result: Record<string, unknown> = {}
            for (const key of keys) {
                const value = source[key]
                if (value !== undefined && value !== null && value !== '') {
                    result[key] = value
                }
            }
            return result as ProviderConfig
        }
        if (kind === 'oidc') {
            return pick([
                'issuer_url',
                'client_id',
                'scopes',
                'username_claim',
                'name_claim',
                'email_claim',
                'redirect_uri_override',
                'logout_url',
                'pkce_method'
            ])
        }
        if (kind === 'oauth2') {
            return pick([
                'authorize_url',
                'token_url',
                'userinfo_url',
                'client_id',
                'scopes',
                'username_claim',
                'name_claim',
                'email_claim',
                'redirect_uri_override',
                'pkce_method'
            ])
        }
        if (kind === 'ldap') {
            const ldapConfig = pick([
                'server_url',
                'ca_cert',
                'user_dn_template',
                'bind_dn',
                'search_base',
                'search_filter',
                'username_attr',
                'name_attr'
            ])
            ldapConfig.use_tls = !!source.use_tls
            return ldapConfig
        }
        if (kind === 'saml') {
            return pick([
                'idp_sso_url',
                'idp_entity_id',
                'idp_certificate',
                'sp_entity_id',
                'acs_url_override',
                'sp_certificate',
                'external_id_attr',
                'username_attr',
                'name_attr',
                'email_attr',
                'nameid_format'
            ])
        }
        return {}
    }

    const persist = async (): Promise<boolean> => {
        showValidationError.value = false
        showError.value = false

        if (!formRef.value?.validate) {
            return false
        }
        const { valid } = (await formRef.value.validate()) as FormValidationResult
        if (!valid) {
            showValidationError.value = true
            return false
        }

        saving.value = true
        try {
            const payload = {
                id: isEdit.value ? localItem.value.id : -1,
                name: localItem.value.name,
                kind: localItem.value.kind,
                enabled: localItem.value.enabled,
                provisioning_mode: localItem.value.provisioning_mode,
                allowed_domains: localItem.value.allowed_domains || '',
                require_mfa: localItem.value.require_mfa,
                organization: organizationId.value ? { id: organizationId.value } : null,
                default_roles: selectedRoles.value.map((id) => ({ id })),
                config: buildConfig(),
                secret: secretInput.value || null
            }
            if (isEdit.value) {
                await updateAuthProvider(payload)
                window.dispatchEvent(new CustomEvent('notification', { detail: { type: 'success', loc: 'common.updated_successfully' } }))
            } else {
                await createNewAuthProvider(payload)
                window.dispatchEvent(new CustomEvent('notification', { detail: { type: 'success', loc: 'common.created_successfully' } }))
            }
            emit('saved')
            return true
        } catch (error) {
            window.dispatchEvent(new CustomEvent('notification', { detail: { type: 'error', loc: 'common.error_saving' } }))
            showError.value = true
            return false
        } finally {
            saving.value = false
        }
    }

    onMounted(async () => {
        try {
            const [orgsResponse, rolesResponse] = await Promise.all([getAllOrganizations({ search: '' }), getAllRoles({ search: '' })])
            organizations.value = (orgsResponse as ListResponse).data?.items || []
            roles.value = (rolesResponse as ListResponse).data?.items || []
        } catch (error) {
            console.error('Error loading organizations/roles:', error)
        }
    })

    const { confirmVisible, capture, requestClose, continueEditing, saveAndClose, discardAndClose } = useUnsavedChanges({
        getState: () => ({ item: localItem.value, config: config.value, org: organizationId.value, roles: selectedRoles.value }),
        save: persist,
        close: closeDialog
    })
</script>
