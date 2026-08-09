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
    </v-tabs>

    <v-window
        v-model="activeTab"
        class="mt-2"
    >
        <!-- General: the federation toggle, the single-IdP or federation block, the SP identity
             and attribute mapping, and the URLs to hand to the identity provider. -->
        <v-window-item value="general">
            <!-- Both mutually exclusive connection modes remain visible. -->
            <div class="text-subtitle-2 ms-4">{{ t('auth_provider.saml_connection_mode') }}</div>
            <v-radio-group
                v-model="federationModel"
                inline
                hide-details
                :disabled="saving"
                class="mb-1 ms-4"
                data-test="saml-connection-mode"
            >
                <v-radio
                    :value="false"
                    color="primary"
                    :label="t('auth_provider.saml_single_idp')"
                    data-test="saml-mode-single"
                />
                <v-radio
                    :value="true"
                    color="primary"
                    :label="t('auth_provider.saml_use_federation')"
                    data-test="saml-mode-federation"
                />
            </v-radio-group>
            <div
                class="text-caption text-medium-emphasis mb-3 ms-4"
                data-test="saml-connection-mode-help"
            >
                {{ t(federationModel ? 'auth_provider.saml_use_federation_hint' : 'auth_provider.saml_single_idp_hint') }}
            </div>

            <template v-if="!federationModel">
                <!-- The three fields below all live in the IdP's metadata; read them
                     out of it rather than making the admin copy them by hand. -->
                <v-row>
                    <v-col cols="12">
                        <v-textarea
                            v-model="metadataModel"
                            dir="ltr"
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
                            dir="ltr"
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
                            dir="ltr"
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
                            dir="ltr"
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
                            dir="ltr"
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
                            dir="ltr"
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
                            dir="ltr"
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
                            dir="ltr"
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
                        dir="ltr"
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
                        dir="ltr"
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
                        dir="ltr"
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
                        dir="ltr"
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
                        dir="ltr"
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
                        dir="ltr"
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
                <i18n-t
                    keypath="auth_provider.saml_metadata_url_with_url"
                    tag="div"
                    class="text-body-2"
                >
                    <template #url>
                        <bdi dir="ltr"
                            ><code>{{ samlMetadataUrl }}</code></bdi
                        >
                    </template>
                </i18n-t>
                <i18n-t
                    keypath="auth_provider.saml_acs_url_with_url"
                    tag="div"
                    class="text-body-2"
                >
                    <template #url>
                        <bdi dir="ltr"
                            ><code>{{ samlAcsUrl }}</code></bdi
                        >
                    </template>
                </i18n-t>
                <i18n-t
                    v-if="federationModel"
                    keypath="auth_provider.saml_disco_url_with_url"
                    tag="div"
                    class="text-body-2"
                >
                    <template #url>
                        <bdi dir="ltr"
                            ><code>{{ samlDiscoUrl }}</code></bdi
                        >
                    </template>
                </i18n-t>
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
                        dir="ltr"
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
                        dir="ltr"
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
                    class="ms-2"
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
                    :disabled="saving || generatingKeypair"
                    data-test="saml-generate-keypair"
                    @click="$emit('generate-keypair')"
                >
                    {{ t('auth_provider.sp_keypair_generate') }}
                </v-btn>
            </div>

            <v-row>
                <v-col cols="12">
                    <v-textarea
                        v-model="secretModel"
                        dir="ltr"
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
                        dir="ltr"
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
    </v-window>
</template>

<script setup lang="ts">
    /**
     * SamlFields - the SAML 2.0 provider fields, organized into three tabs:
     *
     *   General             - the federation toggle, the single-IdP or federation
     *                         block, the SP identity & attribute mapping, and the
     *                         URLs to hand to the identity provider.
     *   Service information - the human-readable SP metadata a federation requires
     *                         (display name, description, organization, contact).
     *   SP keypair          - the encryption keypair an identity provider encrypts
     *                         the assertion to.
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
    import type { ProviderConfig } from '../types'

    withDefaults(
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
        }>(),
        {
            suggestedEntityId: ''
        }
    )

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
