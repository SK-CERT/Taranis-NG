/**
 * Shared SAML/OIDC/OAuth2/LDAP provider config shape.
 *
 * Extracted from NewAuthProvider.vue so each per-kind field component can type
 * the shared `config` object it receives as a prop (and mutates in place, which
 * is permitted because `vue/no-mutating-props` is off in this project and the
 * object is the same reactive reference the parent owns).
 */
export type ProviderConfig = {
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
    discovery_url?: string
    discovery_params?: string
    federation_metadata_url?: string
    federation_metadata_cert?: string
    federation_metadata_refresh_hours?: number
    sp_display_name?: string
    sp_description?: string
    sp_information_url?: string
    sp_organization_name?: string
    sp_organization_url?: string
    sp_contact_email?: string
    sp_contact_surname?: string
    sp_contact_name?: string
}
