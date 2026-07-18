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
                            <!-- The built-in local provider is a singleton with a fixed
                                 identity: its name is locked and shown translated, while the
                                 stored value (localItem.name) is left untouched so it is
                                 re-sent unchanged on save. Every other kind is freely named. -->
                            <v-text-field
                                :model-value="isLocalProvider ? t('auth_provider.local_name') : localItem.name"
                                :label="t('auth_provider.name')"
                                variant="outlined"
                                density="comfortable"
                                :rules="isLocalProvider ? [] : [(v) => !!v || t('error.required')]"
                                :disabled="saving || isLocalProvider"
                                :hint="isLocalProvider ? t('auth_provider.local_name_hint') : undefined"
                                :persistent-hint="isLocalProvider"
                                @update:model-value="(v) => (localItem.name = v)"
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

                    <!-- Stable URL identifier. Auto-filled from the name for a new provider
                         until the admin edits it; it is what appears in the IdP-facing URLs. -->
                    <v-row
                        v-if="['oidc', 'oauth2', 'saml'].includes(localItem.kind)"
                        class="mt-n3 mb-2"
                    >
                        <v-col
                            cols="12"
                            md="6"
                        >
                            <v-text-field
                                v-model="localItem.slug"
                                :label="t('auth_provider.slug')"
                                variant="outlined"
                                density="comfortable"
                                :hint="t('auth_provider.slug_hint')"
                                persistent-hint
                                :rules="slugRules"
                                :disabled="saving"
                                @update:model-value="slugManuallyEdited = true"
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
                                class="mb-4"
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
                        <v-col
                            cols="12"
                            class="mt-n6"
                        >
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
                        <OidcFields
                            :config="config"
                            :saving="saving"
                        />
                        <OauthSharedFields
                            v-model="secretInput"
                            :config="config"
                            :saving="saving"
                            :has-secret="hasSecret"
                            :is-edit="isEdit"
                            :redirect-uri="oauthRedirectUri"
                            scopes-placeholder="openid profile email"
                        />
                    </template>

                    <!-- OAuth2 fields -->
                    <template v-if="localItem.kind === 'oauth2'">
                        <v-divider class="mb-4" />
                        <Oauth2Fields
                            :config="config"
                            :saving="saving"
                        />
                        <OauthSharedFields
                            v-model="secretInput"
                            :config="config"
                            :saving="saving"
                            :has-secret="hasSecret"
                        />
                    </template>

                    <!-- SAML 2.0 fields -->
                    <template v-if="localItem.kind === 'saml'">
                        <SamlFields
                            v-model:federation="samlUseFederation"
                            v-model:metadata="metadataInput"
                            v-model:secret="secretInput"
                            :config="config"
                            :saving="saving"
                            :has-secret="hasSecret"
                            :is-edit="isEdit"
                            :importing="importing"
                            :verifying-federation="verifyingFederation"
                            :generating-keypair="generatingKeypair"
                            :metadata-message="metadataMessage"
                            :metadata-error="metadataError"
                            :federation-message="federationMessage"
                            :federation-error="federationError"
                            :suggested-entity-id="suggestedEntityId"
                            :saml-metadata-url="samlMetadataUrl"
                            :saml-acs-url="samlAcsUrl"
                            :saml-disco-url="samlDiscoUrl"
                            @load-metadata="loadMetadata"
                            @verify-federation="verifyFederation"
                            @generate-keypair="generateKeypair"
                        >
                            <template #roles>
                                <EntitySelectTable
                                    v-model="selectedRoles"
                                    :title="t('auth_provider.default_roles')"
                                    :items="roles"
                                    :headers="roleHeaders"
                                    :disabled="saving || !isAutoCreate"
                                />
                            </template>
                        </SamlFields>
                    </template>

                    <!-- LDAP fields -->
                    <template v-if="localItem.kind === 'ldap'">
                        <v-divider class="mb-4" />
                        <LdapFields
                            v-model="secretInput"
                            :config="config"
                            :saving="saving"
                            :has-secret="hasSecret"
                        />
                    </template>

                    <!-- Default roles for auto-created users (only meaningful when auto-creation is on).
                         Rendered inline for non-SAML external kinds; SAML shows it in its
                         own "Default roles" tab inside SamlFields (see the #roles slot above). -->
                    <template v-if="isExternalKind && localItem.kind !== 'saml'">
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
    import OidcFields from './fields/OidcFields.vue'
    import Oauth2Fields from './fields/Oauth2Fields.vue'
    import OauthSharedFields from './fields/OauthSharedFields.vue'
    import SamlFields from './fields/SamlFields.vue'
    import LdapFields from './fields/LdapFields.vue'
    import { useUnsavedChanges } from '@/composables/useUnsavedChanges'
    import { useAuth } from '@/composables/useAuth'
    import type { ProviderConfig } from './types'
    import {
        createNewAuthProvider,
        updateAuthProvider,
        getAllOrganizations,
        getAllRoles,
        importSamlMetadata,
        generateSamlKeypair,
        verifySamlFederation
    } from '@/api/config'

    type AuthProviderItem = {
        id: string | number | null
        name: string
        slug?: string
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
    // The built-in local accounts provider is a singleton and cannot be renamed.
    const isLocalProvider = computed(() => localItem.value.kind === 'local')

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

    // Federation mode: connect to a whole federation and let the user pick their IdP at a
    // discovery service, instead of targeting one IdP. Derived from a configured discovery_url.
    const samlUseFederation = ref(false)
    const verifyingFederation = ref(false)
    const federationMessage = ref('')
    const federationError = ref(false)

    // Fetch and signature-verify the federation metadata so the admin can confirm the URL and
    // trust anchor before saving; nothing is stored, only the resolvable IdP count is reported.
    const verifyFederation = async (): Promise<void> => {
        verifyingFederation.value = true
        federationMessage.value = ''
        federationError.value = false
        try {
            const response = (await verifySamlFederation({
                federation_metadata_url: config.value.federation_metadata_url || '',
                federation_metadata_cert: config.value.federation_metadata_cert || ''
            })) as { data: { entity_count: number; valid_until: string | null } }
            federationMessage.value = t('auth_provider.federation_verify_result', { count: response.data.entity_count })
        } catch (error) {
            const data = (error as { response?: { data?: { error?: string } } })?.response?.data
            federationMessage.value = data?.error || t('auth_provider.federation_verify_error')
            federationError.value = true
        } finally {
            verifyingFederation.value = false
        }
    }

    // The URLs an identity provider needs when registering this SP. They carry the
    // provider slug (not the database id) so they stay stable across recreation and
    // between environments. The backend derives the ACS the same way (or from
    // acs_url_override), so mirror that here.
    const samlAcsUrl = computed(() => {
        const override = (config.value.acs_url_override || '').trim()
        return override || `${window.location.origin}/api/v1/auth/saml/${localItem.value.slug}/acs`
    })
    const samlMetadataUrl = computed(() => `${window.location.origin}/api/v1/auth/saml/${localItem.value.slug}/metadata`)
    const samlDiscoUrl = computed(() => `${window.location.origin}/api/v1/auth/saml/${localItem.value.slug}/disco`)
    // OAuth/OIDC callback URL to register at the provider - slug-based, so it is stable too.
    const oauthRedirectUri = computed(
        () =>
            (config.value.redirect_uri_override || '').trim() ||
            `${window.location.origin}/api/v1/auth/oauth/${localItem.value.slug}/callback`
    )

    // Slug: a URL-safe stable identifier auto-generated from the name for a new provider
    // until the admin edits it (an existing provider's slug is left untouched).
    const slugManuallyEdited = ref(false)
    const slugify = (value: string): string =>
        (value || '')
            .trim()
            .toLowerCase()
            .replace(/[^a-z0-9]+/g, '-')
            .replace(/^-+|-+$/g, '')
    const slugRules = [
        (v: string) => !!(v && v.trim()) || t('error.required'),
        (v: string) => /^[a-z0-9]([a-z0-9-]*[a-z0-9])?$/.test(v || '') || t('auth_provider.slug_invalid')
    ]
    watch(
        () => localItem.value.name,
        (name) => {
            if (!isEdit.value && !slugManuallyEdited.value) {
                localItem.value.slug = slugify(name)
            }
        }
    )

    // The suggested SP entity ID is the SP's own metadata URL — it is the canonical
    // identifier for a SAML service provider (the metadata URL itself is stable across
    // environments, since it carries the provider slug rather than the database id).
    const suggestedEntityId = computed(() => samlMetadataUrl.value)
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
                samlUseFederation.value = !!incoming.config?.discovery_url
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
        samlUseFederation.value = false
        federationMessage.value = ''
        federationError.value = false
        slugManuallyEdited.value = false
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
            // Shared by both modes; the mode-specific keys are added below so the
            // persisted config unambiguously reflects the chosen mode (the backend
            // treats a present discovery_url as federation mode).
            const shared: Array<keyof ProviderConfig> = [
                'sp_entity_id',
                'acs_url_override',
                'sp_certificate',
                'external_id_attr',
                'username_attr',
                'name_attr',
                'email_attr',
                'nameid_format',
                'sp_display_name',
                'sp_description',
                'sp_information_url',
                'sp_organization_name',
                'sp_organization_url',
                'sp_contact_email',
                'sp_contact_surname',
                'sp_contact_name'
            ]
            if (samlUseFederation.value) {
                return pick([
                    ...shared,
                    'discovery_url',
                    'discovery_params',
                    'federation_metadata_url',
                    'federation_metadata_cert',
                    'federation_metadata_refresh_hours'
                ])
            }
            return pick([...shared, 'idp_sso_url', 'idp_entity_id', 'idp_certificate'])
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
                slug: (localItem.value.slug || '').trim() || null,
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
