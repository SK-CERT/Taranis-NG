<template>
    <v-divider class="mb-4" />

    <v-tabs
        v-model="activeTab"
        density="compact"
        bg-color="transparent"
    >
        <v-tab value="general">{{ t('auth_provider.saml_tab_general') }}</v-tab>
        <v-tab value="service">{{ t('auth_provider.saml_tab_service_information') }}</v-tab>
        <v-tab value="keypair">{{ t('auth_provider.saml_tab_sp_keypair') }}</v-tab>
        <v-tab value="roles">{{ t('auth_provider.default_roles') }}</v-tab>
    </v-tabs>

    <v-window
        v-model="activeTab"
        class="mt-2"
    >
        <!-- General: the federation toggle, the single-IdP or federation block, the SP identity
             and attribute mapping, and the URLs to hand to the identity provider. -->
        <v-window-item value="general">
            <!-- Target a single identity provider, or connect to a whole federation:
                 the user then picks their IdP at a discovery service (WAYF). -->
            <v-switch
                v-model="federationModel"
                color="primary"
                density="comfortable"
                hide-details
                :disabled="saving"
                class="mb-2 ml-4"
            >
                <template #label>
                    <span class="text-body-2">{{ t('auth_provider.saml_use_federation') }}</span>
                    <v-icon
                        size="x-small"
                        class="ml-1"
                        :title="t('auth_provider.saml_use_federation_hint')"
                    >
                        {{ ICONS.INFORMATION_OUTLINE }}
                    </v-icon>
                </template>
            </v-switch>

            <template v-if="!federationModel">
                <!-- The three fields below all live in the IdP's metadata; read them
                     out of it rather than making the admin copy them by hand. -->
                <v-row>
                    <v-col cols="12">
                        <v-textarea
                            v-model="metadataModel"
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
                                    :disabled="!metadataModel.trim() || saving"
                                    @click="$emit('load-metadata')"
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
                </v-row>
            </template>

            <!-- Federation mode: the discovery service to send users to, and the
                 signed federation metadata (with its trust anchor) the chosen IdP
                 is resolved from. -->
            <template v-else>
                <v-row>
                    <v-col
                        cols="12"
                        md="6"
                    >
                        <v-text-field
                            v-model="config.discovery_url"
                            :label="t('auth_provider.discovery_url')"
                            variant="outlined"
                            density="comfortable"
                            placeholder="https://discovery.example.org/wayf"
                            :hint="t('auth_provider.discovery_url_hint')"
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
                            v-model="config.federation_metadata_url"
                            :label="t('auth_provider.federation_metadata_url')"
                            variant="outlined"
                            density="comfortable"
                            placeholder="https://metadata.example.org"
                            :hint="t('auth_provider.federation_metadata_url_hint')"
                            persistent-hint
                            :rules="[(v) => !!v || t('error.required')]"
                            :disabled="saving"
                        />
                    </v-col>
                    <v-col cols="12">
                        <v-textarea
                            v-model="config.federation_metadata_cert"
                            :label="t('auth_provider.federation_metadata_cert')"
                            variant="outlined"
                            density="comfortable"
                            rows="3"
                            :hint="t('auth_provider.federation_metadata_cert_hint')"
                            persistent-hint
                            :rules="[(v) => !!v || t('error.required')]"
                            :disabled="saving"
                        />
                    </v-col>
                    <v-col cols="12">
                        <v-text-field
                            v-model="config.discovery_params"
                            :label="t('auth_provider.discovery_params')"
                            variant="outlined"
                            density="comfortable"
                            placeholder="filter=..."
                            :hint="t('auth_provider.discovery_params_hint')"
                            persistent-hint
                            :disabled="saving"
                        />
                    </v-col>
                    <v-col
                        cols="12"
                        class="d-flex align-center"
                    >
                        <v-btn
                            color="primary"
                            variant="flat"
                            size="small"
                            prepend-icon="mdi-shield-check"
                            :loading="verifyingFederation"
                            :disabled="saving || !config.federation_metadata_url || !config.federation_metadata_cert"
                            @click="$emit('verify-federation')"
                        >
                            {{ t('auth_provider.federation_verify') }}
                        </v-btn>
                    </v-col>
                    <v-col
                        v-if="federationMessage"
                        cols="12"
                        class="pt-0"
                    >
                        <v-alert
                            :type="federationError ? 'error' : 'success'"
                            density="compact"
                            variant="tonal"
                        >
                            {{ federationMessage }}
                        </v-alert>
                    </v-col>
                </v-row>
            </template>

            <!-- Shared by both modes: our SP identity and the attribute mapping. -->
            <v-row>
                <v-col
                    cols="12"
                    md="6"
                >
                    <SuggestField
                        v-model="config.sp_entity_id"
                        :suggested="suggestedEntityId"
                        :label="t('auth_provider.sp_entity_id')"
                        :hint="t('auth_provider.sp_entity_id_hint')"
                        :tooltip-label="t('auth_provider.sp_entity_id_use_suggested')"
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
                <div
                    v-if="federationModel"
                    class="text-body-2"
                >
                    <strong>{{ t('auth_provider.saml_disco_url') }}:</strong>
                    <code class="ml-1">{{ samlDiscoUrl }}</code>
                </div>
            </v-alert>
        </v-window-item>

        <!-- Service information published in the SP metadata. Federations
             (eduGAIN, InCommon, DFN-AAI, ...) require these to accept the
             registration. -->
        <v-window-item value="service">
            <div class="text-caption text-medium-emphasis mb-2">{{ t('auth_provider.sp_metadata_info_hint') }}</div>
            <v-row>
                <v-col
                    cols="12"
                    md="6"
                >
                    <v-text-field
                        v-model="config.sp_display_name"
                        :label="t('auth_provider.sp_display_name')"
                        variant="outlined"
                        density="comfortable"
                        :hint="t('auth_provider.sp_display_name_hint')"
                        persistent-hint
                        :disabled="saving"
                    />
                </v-col>
                <v-col
                    cols="12"
                    md="6"
                >
                    <v-text-field
                        v-model="config.sp_information_url"
                        :label="t('auth_provider.sp_information_url')"
                        variant="outlined"
                        density="comfortable"
                        placeholder="https://taranis.example.org/"
                        :hint="t('auth_provider.sp_information_url_hint')"
                        persistent-hint
                        :disabled="saving"
                    />
                </v-col>
                <v-col cols="12">
                    <v-text-field
                        v-model="config.sp_description"
                        :label="t('auth_provider.sp_description')"
                        variant="outlined"
                        density="comfortable"
                        :hint="t('auth_provider.sp_description_hint')"
                        persistent-hint
                        :disabled="saving"
                    />
                </v-col>
                <v-col
                    cols="12"
                    md="6"
                >
                    <v-text-field
                        v-model="config.sp_organization_name"
                        :label="t('auth_provider.sp_organization_name')"
                        variant="outlined"
                        density="comfortable"
                        :hint="t('auth_provider.sp_organization_name_hint')"
                        persistent-hint
                        :disabled="saving"
                    />
                </v-col>
                <v-col
                    cols="12"
                    md="6"
                >
                    <v-text-field
                        v-model="config.sp_organization_url"
                        :label="t('auth_provider.sp_organization_url')"
                        variant="outlined"
                        density="comfortable"
                        placeholder="https://example.org/"
                        :hint="t('auth_provider.sp_organization_url_hint')"
                        persistent-hint
                        :disabled="saving"
                    />
                </v-col>
                <v-col
                    cols="12"
                    md="6"
                >
                    <v-text-field
                        v-model="config.sp_contact_email"
                        :label="t('auth_provider.sp_contact_email')"
                        variant="outlined"
                        density="comfortable"
                        placeholder="cert@example.org"
                        :hint="t('auth_provider.sp_contact_email_hint')"
                        persistent-hint
                        :disabled="saving"
                    />
                </v-col>
                <v-col
                    cols="12"
                    md="6"
                >
                    <v-text-field
                        v-model="config.sp_contact_name"
                        :label="t('auth_provider.sp_contact_name')"
                        variant="outlined"
                        density="comfortable"
                        :hint="t('auth_provider.sp_contact_name_hint')"
                        persistent-hint
                        :disabled="saving"
                    />
                </v-col>
                <v-col
                    cols="12"
                    md="6"
                >
                    <v-text-field
                        v-model="config.sp_contact_surname"
                        :label="t('auth_provider.sp_contact_surname')"
                        variant="outlined"
                        density="comfortable"
                        :hint="t('auth_provider.sp_contact_surname_hint')"
                        persistent-hint
                        :disabled="saving"
                    />
                </v-col>
            </v-row>
        </v-window-item>

        <!-- Service provider keypair: the certificate an identity provider
             encrypts the assertion to, and a registration form asks for. -->
        <v-window-item value="keypair">
            <div class="d-flex align-center mb-2">
                <span class="text-subtitle-2">{{ t('auth_provider.sp_keypair') }}</span>
                <v-chip
                    v-if="hasSecret && !secretModel"
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
                    @click="$emit('generate-keypair')"
                >
                    {{ t('auth_provider.sp_keypair_generate') }}
                </v-btn>
            </div>

            <v-row>
                <v-col cols="12">
                    <v-textarea
                        v-model="secretModel"
                        :label="t('auth_provider.sp_private_key')"
                        variant="outlined"
                        density="comfortable"
                        rows="5"
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
                        rows="5"
                        :hint="t('auth_provider.sp_certificate_hint')"
                        persistent-hint
                        :disabled="saving"
                    />
                </v-col>
            </v-row>
        </v-window-item>

        <!-- Default roles for auto-created users. Rendered by the parent through the
             `roles` slot, so the EntitySelectTable and its permission/autosave
             gating stay owned by the parent (NewAuthProvider owns selectedRoles). -->
        <v-window-item value="roles">
            <slot name="roles" />
        </v-window-item>
    </v-window>
</template>

<script setup lang="ts">
    /**
     * SamlFields - the SAML 2.0 provider fields, organized into four tabs:
     *
     *   General             - the federation toggle, the single-IdP or federation
     *                         block, the SP identity & attribute mapping, and the
     *                         URLs to hand to the identity provider.
     *   Service information - the human-readable SP metadata a federation requires
     *                         (display name, description, organization, contact).
     *   SP keypair          - the encryption keypair an identity provider encrypts
     *                         the assertion to.
     *   Default roles       - the roles auto-created users get (rendered through
     *                         the `roles` slot by the parent, which owns
     *                         selectedRoles and the permission/autosave gating).
     *
     * The shared `config` object is mutated in place (the project disables
     * `vue/no-mutating-props`, and the object is the same reactive reference
     * the parent owns). The federation toggle, the metadata textarea and the
     * private-key textarea are two-way bound via defineModel. The three
     * actions (load IdP metadata, verify federation, generate keypair) are
     * emitted because their handlers live on the parent and are also called
     * directly by the unit tests.
     */
    import { ref } from 'vue'
    import { useI18n } from 'vue-i18n'
    import SuggestField from '@/components/common/SuggestField.vue'
    import { ICONS } from '@/config/ui-constants'
    import type { ProviderConfig } from '../types'

    defineProps<{
        /** Shared reactive provider config (mutated in place). */
        config: ProviderConfig
        /** Disables every field while a save is in flight. */
        saving: boolean
        /** Whether a private key is already stored (shows the chip / changes hints). */
        hasSecret?: boolean
        /** Whether the provider is being edited (gates the "give these URLs" box). */
        isEdit?: boolean
        /** "Load metadata" button is in flight. */
        importing?: boolean
        /** "Verify federation" button is in flight. */
        verifyingFederation?: boolean
        /** "Generate keypair" button is in flight. */
        generatingKeypair?: boolean
        /** Message shown after importing IdP metadata (display-only). */
        metadataMessage?: string
        /** Whether the metadata-import message is an error (display-only). */
        metadataError?: boolean
        /** Message shown after verifying the federation (display-only). */
        federationMessage?: string
        /** Whether the federation-verify message is an error (display-only). */
        federationError?: boolean
        /** SP entityID suggestion (the SAML endpoint base). */
        suggestedEntityId?: string
        /** Computed metadata URL, shown once the provider is saved. */
        samlMetadataUrl?: string
        /** Computed ACS URL, shown once the provider is saved. */
        samlAcsUrl?: string
        /** Computed discovery-response URL, shown once the provider is saved. */
        samlDiscoUrl?: string
    }>()

    defineEmits<{
        (e: 'load-metadata'): void
        (e: 'verify-federation'): void
        (e: 'generate-keypair'): void
    }>()

    const federationModel = defineModel<boolean>('federation', { default: false })
    const metadataModel = defineModel<string>('metadata', { default: '' })
    const secretModel = defineModel<string>('secret', { default: '' })

    /** Active SAML tab. Defaults to "general" (the first tab). */
    const activeTab = ref('general')

    const { t } = useI18n()
</script>
