import { describe, it, expect, beforeEach, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { mountWithPlugins } from '../helpers/mount-helpers'
import NewAuthProvider from '@/components/config/auth-providers/NewAuthProvider.vue'
import OauthSharedFields from '@/components/config/auth-providers/fields/OauthSharedFields.vue'
import LdapFields from '@/components/config/auth-providers/fields/LdapFields.vue'
import SamlFields from '@/components/config/auth-providers/fields/SamlFields.vue'
import EntitySelectTable from '@/components/common/EntitySelectTable.vue'
import ConfirmationDialog from '@/components/common/dialogs/ConfirmationDialog.vue'
import { createNewAuthProvider, updateAuthProvider, importSamlMetadata, generateSamlKeypair } from '@/api/config'

vi.mock('@/api/config', () => ({
    createNewAuthProvider: vi.fn().mockResolvedValue({ data: {} }),
    updateAuthProvider: vi.fn().mockResolvedValue({ data: {} }),
    importSamlMetadata: vi.fn(),
    generateSamlKeypair: vi.fn(),
    getAllOrganizations: vi.fn().mockResolvedValue({ data: { items: [{ id: 1, name: 'CERT' }] } }),
    getAllRoles: vi.fn().mockResolvedValue({ data: { items: [{ id: 5, name: 'User', description: 'Basic role' }] } })
}))

// Grant every permission so the dialog's create/edit controls are enabled.
vi.mock('@/composables/useAuth', () => ({
    useAuth: () => ({ checkPermission: () => true })
}))

/** Mount the dialog and wait for its onMounted option loading to settle. */
async function mountDialog(props = {}) {
    const wrapper = mountWithPlugins(NewAuthProvider, { props })
    await new Promise((resolve) => setTimeout(resolve, 0))
    await wrapper.vm.$nextTick()
    return wrapper
}

/** Drive the dialog into edit mode with the given provider row. */
async function openEdit(wrapper, provider) {
    await wrapper.setProps({ editItem: provider })
    await wrapper.vm.$nextTick()
    return wrapper
}

const OIDC_PROVIDER = {
    id: 2,
    name: 'Corp SSO',
    kind: 'oidc',
    enabled: true,
    provisioning_mode: 'approval',
    allowed_domains: 'example.org',
    require_mfa: false,
    organization: { id: 1, name: 'CERT' },
    default_roles: [{ id: 5, name: 'User' }],
    has_secret: true,
    config: { issuer_url: 'https://idp.example.org', client_id: 'taranis', pkce_method: 'S256' }
}

const SAML_PROVIDER = {
    id: 3,
    name: 'Corp SAML',
    slug: 'corp-saml',
    kind: 'saml',
    enabled: true,
    provisioning_mode: 'automatic',
    allowed_domains: '',
    require_mfa: false,
    organization: null,
    default_roles: [],
    has_secret: false,
    config: {
        idp_sso_url: 'https://idp.example.org/sso/redirect',
        idp_entity_id: 'https://idp.example.org/metadata',
        idp_certificate: '-----BEGIN CERTIFICATE-----\nMIIC\n-----END CERTIFICATE-----',
        sp_entity_id: 'taranis-ng',
        username_attr: 'urn:oid:1.3.6.1.4.1.5923.1.1.1.6',
        external_id_attr: 'urn:oid:1.3.6.1.4.1.5923.1.1.1.13'
    }
}

describe('NewAuthProvider dialog', () => {
    beforeEach(() => {
        vi.clearAllMocks()
    })

    // ── Kinds ─────────────────────────────────────
    it('offers external provider kinds for creation, but not local accounts or passkeys', async () => {
        const wrapper = await mountDialog()
        const kinds = wrapper.vm.kindOptions.map((option) => option.value)
        // Local accounts are migration-owned; passkeys are credentials owned by users.
        expect(kinds).toEqual(['oidc', 'oauth2', 'saml', 'ldap'])
    })

    it('treats oidc, oauth2, saml and ldap as external kinds (provisioning applies)', async () => {
        const wrapper = await mountDialog()
        for (const kind of ['oidc', 'oauth2', 'saml', 'ldap']) {
            wrapper.vm.localItem.kind = kind
            await wrapper.vm.$nextTick()
            expect(wrapper.vm.isExternalKind, `${kind} should be external`).toBe(true)
        }
        wrapper.vm.localItem.kind = 'local'
        await wrapper.vm.$nextTick()
        expect(wrapper.vm.isExternalKind, 'local should not be external').toBe(false)
    })

    it('keeps newly configured external providers disabled until explicitly enabled', async () => {
        const wrapper = await mountDialog()

        expect(wrapper.vm.localItem.kind).toBe('oidc')
        expect(wrapper.vm.localItem.enabled).toBe(false)
        expect(wrapper.vm.providerEnabledHint).toContain('cannot choose this login method')
    })

    it('retains local only while editing the seeded row and preserves its stored name', async () => {
        const wrapper = await mountDialog()
        await openEdit(wrapper, {
            id: 1,
            name: 'Local accounts',
            kind: 'local',
            enabled: true,
            provisioning_mode: 'manual',
            allowed_domains: '',
            require_mfa: false
        })

        expect(wrapper.vm.kindOptions.map((option) => option.value)).toContain('local')
        wrapper.vm.formRef = { validate: () => Promise.resolve({ valid: true }) }
        await wrapper.vm.persist()
        expect(updateAuthProvider.mock.calls[0][0].name).toBe('Local accounts')
    })

    it('clears a typed secret when a new provider changes kind', async () => {
        const wrapper = await mountDialog()
        wrapper.vm.secretInput = 'oidc-client-secret'
        wrapper.vm.localItem.kind = 'ldap'
        await wrapper.vm.$nextTick()

        expect(wrapper.vm.secretInput).toBe('')
        expect(wrapper.vm.config.use_tls).toBe(true)
    })

    it('preserves an existing LDAP provider whose TLS setting is off', async () => {
        const wrapper = await mountDialog()
        await openEdit(wrapper, {
            ...SAML_PROVIDER,
            id: 4,
            kind: 'ldap',
            config: { server_url: 'ldap://ldap.example.org', use_tls: false, user_dn_template: 'uid={username},dc=x' }
        })

        expect(wrapper.vm.config.use_tls).toBe(false)
    })

    it('treats a newly entered write-only secret as dirty without exposing an existing one', async () => {
        const wrapper = await mountDialog()
        wrapper.vm.dialog = true
        await wrapper.vm.$nextTick()

        wrapper.vm.secretInput = 'never-put-this-in-the-snapshot'
        wrapper.vm.requestClose()

        expect(wrapper.vm.confirmVisible).toBe(true)
    })

    it('offers PKCE plain only as a visibly warned legacy compatibility mode', () => {
        const config = { pkce_method: 'plain' }
        const wrapper = mountWithPlugins(OauthSharedFields, { props: { config, saving: false } })

        expect(wrapper.vm.pkceMethodOptions.map((option) => option.value)).toEqual(['none', 'S256', 'plain'])
        expect(wrapper.vm.pkceMethod).toBe('plain')
        expect(wrapper.find('[data-test="pkce-plain-warning"]').text()).toContain('verifier is exposed')
    })

    it('preserves an explicitly selected PKCE plain value in the provider config', async () => {
        const wrapper = await mountDialog()
        await openEdit(wrapper, {
            ...OIDC_PROVIDER,
            config: { ...OIDC_PROVIDER.config, pkce_method: 'plain' }
        })

        expect(wrapper.vm.buildConfig().pkce_method).toBe('plain')
    })

    it('requires explicit confirmation before saving PKCE plain', async () => {
        const wrapper = await mountDialog()
        await openEdit(wrapper, {
            ...OIDC_PROVIDER,
            config: { ...OIDC_PROVIDER.config, pkce_method: 'plain' }
        })
        wrapper.vm.formRef = { validate: () => Promise.resolve({ valid: true }) }

        expect(await wrapper.vm.persist()).toBe(false)
        expect(wrapper.vm.plainPkceDialog).toBe(true)
        expect(updateAuthProvider).not.toHaveBeenCalled()

        const confirmation = wrapper
            .findAllComponents(ConfirmationDialog)
            .find((dialog) => dialog.props('titleKey') === 'auth_provider.pkce_plain_confirm_title')
        expect(confirmation).toBeDefined()
        confirmation.vm.$emit('confirm')
        await flushPromises()

        expect(updateAuthProvider).toHaveBeenCalledWith(
            expect.objectContaining({ config: expect.objectContaining({ pkce_method: 'plain' }) })
        )
        expect(wrapper.vm.dialog).toBe(false)
    })

    it('defaults a new OAuth provider to S256 without an insecure warning', async () => {
        const wrapper = await mountDialog()
        wrapper.vm.dialog = true
        await wrapper.vm.$nextTick()

        expect(wrapper.vm.config.pkce_method).toBe('S256')
        expect(wrapper.find('[data-test="auth-provider-insecure-warning"]').exists()).toBe(false)
    })

    it('truthfully treats an existing provider without a PKCE setting as insecure none', async () => {
        const wrapper = await mountDialog()
        await openEdit(wrapper, {
            ...OIDC_PROVIDER,
            config: { issuer_url: 'https://idp.example.org', client_id: 'taranis' }
        })

        expect(wrapper.vm.config.pkce_method).toBe('none')
        expect(wrapper.vm.insecureConfigurationWarnings).toContain('PKCE is disabled. Use S256 unless the provider does not support PKCE.')
    })

    it('uses a theme-aware top warning when LDAP TLS is disabled', async () => {
        const wrapper = await mountDialog()
        await openEdit(wrapper, {
            ...SAML_PROVIDER,
            id: 4,
            kind: 'ldap',
            config: { server_url: 'ldap://ldap.example.org', use_tls: false, user_dn_template: 'uid={username},dc=x' }
        })

        expect(wrapper.vm.insecureConfigurationWarnings[0]).toContain('LDAP traffic is not protected by TLS')
        const warning = document.body.querySelector('[data-test="auth-provider-insecure-warning"]')
        expect(warning).not.toBeNull()
        expect(warning?.classList).toContain('v-alert--variant-tonal')
        expect(warning?.textContent).toContain('LDAP traffic is not protected by TLS')
    })

    it('warns about unencrypted authentication endpoints', async () => {
        const wrapper = await mountDialog()
        await openEdit(wrapper, {
            ...OIDC_PROVIDER,
            config: { issuer_url: 'http://localhost:8080/realms/taranis', client_id: 'taranis', pkce_method: 'S256' }
        })

        expect(wrapper.vm.insecureConfigurationWarnings).toContain(
            'At least one authentication endpoint uses unencrypted HTTP. HTTP is intended only for loopback development services.'
        )
    })

    // ── Auto-create gating ────────────────────────
    it('enables the default-roles picker only for the auto-create provisioning modes', async () => {
        const wrapper = await mountDialog()
        await openEdit(wrapper, { ...SAML_PROVIDER, provisioning_mode: 'manual' })
        expect(wrapper.vm.isAutoCreate).toBe(false)

        wrapper.vm.localItem.provisioning_mode = 'approval'
        await wrapper.vm.$nextTick()
        expect(wrapper.vm.isAutoCreate).toBe(true)

        wrapper.vm.localItem.provisioning_mode = 'automatic'
        await wrapper.vm.$nextTick()
        expect(wrapper.vm.isAutoCreate).toBe(true)
    })

    it.each(['oidc', 'oauth2', 'saml', 'ldap'])('shows Default roles in the same parent-level section for %s', async (kind) => {
        const wrapper = await mountDialog()
        await openEdit(wrapper, { ...OIDC_PROVIDER, id: `${kind}-id`, kind, provisioning_mode: 'approval' })

        expect(wrapper.findComponent(EntitySelectTable).exists()).toBe(true)
        if (kind === 'saml') {
            expect(wrapper.findComponent(SamlFields).text()).not.toContain('Default roles')
        }
    })

    it('explains the selected MFA requirement state', async () => {
        const wrapper = await mountDialog()
        wrapper.vm.localItem.kind = 'ldap'
        wrapper.vm.localItem.require_mfa = false
        await wrapper.vm.$nextTick()
        expect(wrapper.vm.mfaRequirementHint).toContain('adds no MFA requirement')

        wrapper.vm.localItem.require_mfa = true
        await wrapper.vm.$nextTick()
        expect(wrapper.vm.mfaRequirementHint).toContain('must use TOTP or a passkey')
    })

    it('hides provisioning-only controls and drops dormant values in manual mode', async () => {
        const wrapper = await mountDialog()
        await openEdit(wrapper, {
            ...OIDC_PROVIDER,
            provisioning_mode: 'manual',
            allowed_domains: 'stale.example',
            organization: { id: 1, name: 'CERT' },
            default_roles: [{ id: 5, name: 'User' }]
        })

        expect(wrapper.findComponent(EntitySelectTable).exists()).toBe(false)
        wrapper.vm.formRef = { validate: () => Promise.resolve({ valid: true }) }
        await wrapper.vm.persist()

        const payload = updateAuthProvider.mock.calls[0][0]
        expect(payload.allowed_domains).toBe('')
        expect(payload.organization).toBeNull()
        expect(payload.default_roles).toEqual([])
    })

    // ── Edit mode hydration ───────────────────────
    it('hydrates the form from an existing provider and opens the dialog', async () => {
        const wrapper = await mountDialog()
        await openEdit(wrapper, OIDC_PROVIDER)

        expect(wrapper.vm.dialog).toBe(true)
        expect(wrapper.vm.isEdit).toBe(true)
        expect(wrapper.vm.localItem.name).toBe('Corp SSO')
        expect(wrapper.vm.organizationId).toBe(1)
        expect(wrapper.vm.selectedRoles).toEqual([5])
        expect(wrapper.vm.config.issuer_url).toBe('https://idp.example.org')
        // the stored secret is never sent to the browser, only the has_secret flag
        expect(wrapper.vm.hasSecret).toBe(true)
        expect(wrapper.vm.secretInput).toBe('')
    })

    it('emits update:modelValue on close so the parent can clear editItem (re-edit fix)', async () => {
        const wrapper = await mountDialog()
        await openEdit(wrapper, OIDC_PROVIDER)
        expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual([true])

        wrapper.vm.dialog = false
        await wrapper.vm.$nextTick()

        expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual([false])
    })

    // ── Payload shaping ───────────────────────────
    it('sends only SAML config keys for a saml provider, including the stable identifier', async () => {
        const wrapper = await mountDialog()
        await openEdit(wrapper, SAML_PROVIDER)

        const config = wrapper.vm.buildConfig()

        expect(config).toEqual({
            idp_sso_url: 'https://idp.example.org/sso/redirect',
            idp_entity_id: 'https://idp.example.org/metadata',
            idp_certificate: '-----BEGIN CERTIFICATE-----\nMIIC\n-----END CERTIFICATE-----',
            sp_entity_id: 'taranis-ng',
            username_attr: 'urn:oid:1.3.6.1.4.1.5923.1.1.1.6',
            // keys the account across logins - without it a transient NameID locks the user out
            external_id_attr: 'urn:oid:1.3.6.1.4.1.5923.1.1.1.13'
        })
        // no leakage of other kinds' fields
        expect(config).not.toHaveProperty('issuer_url')
        expect(config).not.toHaveProperty('server_url')
    })

    it('shows the metadata and ACS URLs to hand to the identity provider once saved', async () => {
        const wrapper = await mountDialog()
        await openEdit(wrapper, SAML_PROVIDER)

        // both carry the provider slug (stable across recreation), so they only exist in edit mode
        expect(wrapper.vm.samlMetadataUrl).toBe(`${window.location.origin}/api/v1/auth/saml/corp-saml/metadata`)
        expect(wrapper.vm.samlAcsUrl).toBe(`${window.location.origin}/api/v1/auth/saml/corp-saml/acs`)
        // v-dialog teleports its content to the body, so assert on the rendered overlay
        expect(document.body.textContent).toContain('/api/v1/auth/saml/corp-saml/metadata')
        expect(document.body.textContent).toContain('/api/v1/auth/saml/corp-saml/acs')
    })

    it('prefers a configured ACS override over the derived URL', async () => {
        const wrapper = await mountDialog()
        await openEdit(wrapper, {
            ...SAML_PROVIDER,
            config: { ...SAML_PROVIDER.config, acs_url_override: 'https://proxy.example.org/api/v1/auth/saml/3/acs' }
        })

        expect(wrapper.vm.samlAcsUrl).toBe('https://proxy.example.org/api/v1/auth/saml/3/acs')
    })

    it('sends only OIDC config keys (including PKCE) for an oidc provider', async () => {
        const wrapper = await mountDialog()
        await openEdit(wrapper, OIDC_PROVIDER)

        const config = wrapper.vm.buildConfig()

        expect(config).toEqual({ issuer_url: 'https://idp.example.org', client_id: 'taranis', pkce_method: 'S256' })
        expect(config).not.toHaveProperty('idp_sso_url')
    })

    it('always sends use_tls for LDAP (a false switch must not be dropped)', async () => {
        const wrapper = await mountDialog()
        await openEdit(wrapper, {
            ...SAML_PROVIDER,
            id: 4,
            kind: 'ldap',
            config: { server_url: 'ldaps://ldap.example.org', use_tls: false, user_dn_template: 'uid={username},dc=x' }
        })

        const config = wrapper.vm.buildConfig()

        expect(config.use_tls).toBe(false)
        expect(config.server_url).toBe('ldaps://ldap.example.org')
    })

    it('does not send a hidden CA certificate when TLS is disabled', async () => {
        const wrapper = await mountDialog()
        await openEdit(wrapper, {
            ...SAML_PROVIDER,
            id: 4,
            kind: 'ldap',
            config: {
                server_url: 'ldap://ldap.example.org',
                use_tls: false,
                ca_cert: '-----BEGIN CERTIFICATE-----\nSTALE\n-----END CERTIFICATE-----',
                user_dn_template: 'uid={username},dc=x'
            }
        })

        expect(wrapper.vm.buildConfig()).not.toHaveProperty('ca_cert')
    })

    // ── Persisting ────────────────────────────────
    it('creates with the -1 id sentinel and a null secret when none was typed', async () => {
        const wrapper = await mountDialog()
        wrapper.vm.dialog = true
        wrapper.vm.localItem.name = 'New SAML'
        wrapper.vm.localItem.kind = 'saml'
        wrapper.vm.config.idp_sso_url = 'https://idp.example.org/sso'
        // bypass the v-form validation harness, which needs a real DOM form
        wrapper.vm.formRef = { validate: () => Promise.resolve({ valid: true }) }

        await wrapper.vm.persist()

        expect(createNewAuthProvider).toHaveBeenCalledTimes(1)
        const payload = createNewAuthProvider.mock.calls[0][0]
        expect(payload.id).toBe(-1)
        expect(payload.kind).toBe('saml')
        expect(payload.secret).toBeNull()
        expect(payload.config.idp_sso_url).toBe('https://idp.example.org/sso')
        expect(wrapper.emitted('saved')).toHaveLength(1)
    })

    it('updates in place and sends a typed secret', async () => {
        const wrapper = await mountDialog()
        await openEdit(wrapper, OIDC_PROVIDER)
        wrapper.vm.secretInput = 'new-client-secret'
        wrapper.vm.formRef = { validate: () => Promise.resolve({ valid: true }) }

        await wrapper.vm.persist()

        expect(updateAuthProvider).toHaveBeenCalledTimes(1)
        const payload = updateAuthProvider.mock.calls[0][0]
        expect(payload.id).toBe(2)
        expect(payload.secret).toBe('new-client-secret')
        expect(payload.organization).toEqual({ id: 1 })
        expect(payload.default_roles).toEqual([{ id: 5 }])
    })

    it('omits an unchanged stored secret while editing', async () => {
        const wrapper = await mountDialog()
        await openEdit(wrapper, OIDC_PROVIDER)
        wrapper.vm.formRef = { validate: () => Promise.resolve({ valid: true }) }

        await wrapper.vm.persist()

        expect(updateAuthProvider.mock.calls[0][0].secret).toBeNull()
    })

    it.each(['oidc', 'oauth2'])('shows and copies the derived callback URI for %s', async (kind) => {
        const writeText = vi.fn().mockResolvedValue(undefined)
        Object.defineProperty(navigator, 'clipboard', { value: { writeText }, configurable: true })
        const wrapper = await mountDialog()
        await openEdit(wrapper, { ...OIDC_PROVIDER, kind, slug: `corp-${kind}` })

        const fields = wrapper.findComponent(OauthSharedFields)
        expect(fields.props('redirectUri')).toBe(`${window.location.origin}/api/v1/auth/oauth/corp-${kind}/callback`)
        expect(fields.find('[data-test="copy-oauth-callback-uri"]').exists()).toBe(true)

        await fields.vm.copyRedirectUri()
        expect(writeText).toHaveBeenCalledWith(fields.props('redirectUri'))
    })

    // ── IdP metadata import ───────────────────────
    it('fills the IdP fields from pasted metadata XML', async () => {
        const wrapper = await mountDialog()
        await openEdit(wrapper, SAML_PROVIDER)
        importSamlMetadata.mockResolvedValue({
            data: {
                idp_entity_id: 'https://idp.example.org/idp/shibboleth',
                idp_sso_url: 'https://idp.example.org/sso/redirect',
                idp_certificate: '-----BEGIN CERTIFICATE-----\nAAA\n-----END CERTIFICATE-----\n',
                certificate_count: 2
            }
        })

        wrapper.vm.metadataInput = '<md:EntityDescriptor entityID="https://idp.example.org/idp/shibboleth"/>'
        await wrapper.vm.loadMetadata()

        // a document is sent as xml, not as a URL to fetch
        expect(importSamlMetadata).toHaveBeenCalledWith({ xml: wrapper.vm.metadataInput })
        expect(wrapper.vm.config.idp_entity_id).toBe('https://idp.example.org/idp/shibboleth')
        expect(wrapper.vm.config.idp_sso_url).toBe('https://idp.example.org/sso/redirect')
        expect(wrapper.vm.config.idp_certificate).toContain('BEGIN CERTIFICATE')
        expect(wrapper.vm.metadataError).toBe(false)
        expect(wrapper.vm.metadataMessage).toContain('2')
    })

    it('sends a metadata URL for the backend to fetch', async () => {
        const wrapper = await mountDialog()
        await openEdit(wrapper, SAML_PROVIDER)
        importSamlMetadata.mockResolvedValue({
            data: { idp_entity_id: 'e', idp_sso_url: 's', idp_certificate: 'c', certificate_count: 1 }
        })

        wrapper.vm.metadataInput = 'https://idp.example.org/idp/shibboleth/metadata'
        await wrapper.vm.loadMetadata()

        expect(importSamlMetadata).toHaveBeenCalledWith({ url: 'https://idp.example.org/idp/shibboleth/metadata' })
    })

    it('shows the backend message when the metadata cannot be read', async () => {
        const wrapper = await mountDialog()
        await openEdit(wrapper, SAML_PROVIDER)
        const error = new Error('bad request')
        error.response = { data: { error: 'The metadata contains no signing certificate' } }
        importSamlMetadata.mockRejectedValue(error)

        wrapper.vm.metadataInput = '<md:EntityDescriptor/>'
        await wrapper.vm.loadMetadata()

        expect(wrapper.vm.metadataError).toBe(true)
        expect(wrapper.vm.metadataMessage).toBe('The metadata contains no signing certificate')
        // the existing configuration is left alone on failure
        expect(wrapper.vm.config.idp_sso_url).toBe('https://idp.example.org/sso/redirect')
    })

    // ── SP keypair (encryption certificate) ───────
    it('generates the SP keypair and fills the private key and certificate', async () => {
        const wrapper = await mountDialog()
        await openEdit(wrapper, SAML_PROVIDER)
        generateSamlKeypair.mockResolvedValue({
            data: {
                private_key: '-----BEGIN PRIVATE KEY-----\nKKK\n-----END PRIVATE KEY-----\n',
                certificate: '-----BEGIN CERTIFICATE-----\nCCC\n-----END CERTIFICATE-----\n'
            }
        })

        wrapper.vm.requestGenerateKeypair()
        await flushPromises()

        expect(generateSamlKeypair).toHaveBeenCalledWith('taranis-ng')
        // the private key travels in the write-only secret field, the certificate in the config
        expect(wrapper.vm.secretInput).toContain('BEGIN PRIVATE KEY')
        expect(wrapper.vm.config.sp_certificate).toContain('BEGIN CERTIFICATE')
    })

    it('asks before replacing stored or entered key material and cancel preserves it', async () => {
        const wrapper = await mountDialog()
        await openEdit(wrapper, {
            ...SAML_PROVIDER,
            has_secret: true,
            config: { ...SAML_PROVIDER.config, sp_certificate: '-----BEGIN CERTIFICATE-----\nOLD\n-----END CERTIFICATE-----' }
        })
        wrapper.vm.secretInput = '-----BEGIN PRIVATE KEY-----\nOLD\n-----END PRIVATE KEY-----'

        wrapper.vm.requestGenerateKeypair()
        await wrapper.vm.$nextTick()

        const confirmation = wrapper.findComponent(ConfirmationDialog)
        expect(wrapper.vm.replaceKeypairDialog).toBe(true)
        expect(confirmation.props('titleKey')).toBe('auth_provider.sp_keypair_replace_title')
        expect(confirmation.props('confirmLabelKey')).toBe('auth_provider.sp_keypair_replace_confirm')
        expect(generateSamlKeypair).not.toHaveBeenCalled()

        confirmation.vm.$emit('update:modelValue', false)
        await wrapper.vm.$nextTick()

        expect(wrapper.vm.secretInput).toContain('\nOLD\n')
        expect(wrapper.vm.config.sp_certificate).toContain('\nOLD\n')
        expect(generateSamlKeypair).not.toHaveBeenCalled()
    })

    it.each([
        ['a stored private key', true, ''],
        ['a newly entered private key', false, '-----BEGIN PRIVATE KEY-----\nTYPED\n-----END PRIVATE KEY-----']
    ])('asks before replacing %s even when no certificate is present', async (_label, hasSecret, enteredSecret) => {
        const wrapper = await mountDialog()
        await openEdit(wrapper, { ...SAML_PROVIDER, has_secret: hasSecret })
        wrapper.vm.secretInput = enteredSecret

        wrapper.vm.requestGenerateKeypair()
        await wrapper.vm.$nextTick()

        expect(wrapper.vm.replaceKeypairDialog).toBe(true)
        expect(generateSamlKeypair).not.toHaveBeenCalled()
    })

    it('asks when only an existing certificate is present, then replaces both values after confirmation', async () => {
        const wrapper = await mountDialog()
        await openEdit(wrapper, {
            ...SAML_PROVIDER,
            config: { ...SAML_PROVIDER.config, sp_certificate: '-----BEGIN CERTIFICATE-----\nOLD\n-----END CERTIFICATE-----' }
        })
        generateSamlKeypair.mockResolvedValue({
            data: {
                private_key: '-----BEGIN PRIVATE KEY-----\nNEW\n-----END PRIVATE KEY-----\n',
                certificate: '-----BEGIN CERTIFICATE-----\nNEW\n-----END CERTIFICATE-----\n'
            }
        })

        wrapper.vm.requestGenerateKeypair()
        expect(generateSamlKeypair).not.toHaveBeenCalled()

        wrapper.findComponent(ConfirmationDialog).vm.$emit('confirm')
        await flushPromises()

        expect(generateSamlKeypair).toHaveBeenCalledTimes(1)
        expect(wrapper.vm.secretInput).toContain('\nNEW\n')
        expect(wrapper.vm.config.sp_certificate).toContain('\nNEW\n')
    })

    it('does not start a second keypair request while generation is in flight', async () => {
        let finishRequest
        generateSamlKeypair.mockImplementation(
            () =>
                new Promise((resolve) => {
                    finishRequest = resolve
                })
        )
        const wrapper = await mountDialog()
        await openEdit(wrapper, { ...SAML_PROVIDER, has_secret: true })

        wrapper.vm.confirmReplaceKeypair()
        wrapper.vm.confirmReplaceKeypair()

        expect(wrapper.vm.generatingKeypair).toBe(true)
        expect(generateSamlKeypair).toHaveBeenCalledTimes(1)

        finishRequest({ data: { private_key: 'NEW PRIVATE', certificate: 'NEW CERTIFICATE' } })
        await flushPromises()
        expect(wrapper.vm.generatingKeypair).toBe(false)
    })

    it('persists the certificate in the config and the private key as the secret', async () => {
        const wrapper = await mountDialog()
        await openEdit(wrapper, {
            ...SAML_PROVIDER,
            config: { ...SAML_PROVIDER.config, sp_certificate: '-----BEGIN CERTIFICATE-----\nCCC\n-----END CERTIFICATE-----' }
        })
        wrapper.vm.secretInput = '-----BEGIN PRIVATE KEY-----\nKKK\n-----END PRIVATE KEY-----'
        wrapper.vm.formRef = { validate: () => Promise.resolve({ valid: true }) }

        await wrapper.vm.persist()

        const payload = updateAuthProvider.mock.calls[0][0]
        expect(payload.config.sp_certificate).toContain('BEGIN CERTIFICATE')
        expect(payload.secret).toContain('BEGIN PRIVATE KEY')
    })

    it('never renders a stored private key back into the form', async () => {
        const wrapper = await mountDialog()
        await openEdit(wrapper, { ...SAML_PROVIDER, has_secret: true })

        // the backend only reports that a key exists; the key itself is never sent to the browser
        expect(wrapper.vm.hasSecret).toBe(true)
        expect(wrapper.vm.secretInput).toBe('')
    })

    it('surfaces a validation error and does not call the API when the form is invalid', async () => {
        const wrapper = await mountDialog()
        wrapper.vm.dialog = true
        wrapper.vm.formRef = { validate: () => Promise.resolve({ valid: false }) }

        const saved = await wrapper.vm.persist()

        expect(saved).toBe(false)
        expect(createNewAuthProvider).not.toHaveBeenCalled()
        expect(wrapper.vm.showValidationError).toBe(true)
    })
})

describe('LDAP provider fields', () => {
    it('shows the optional CA input only while TLS is selected', async () => {
        const config = { use_tls: false }
        const wrapper = mountWithPlugins(LdapFields, { props: { config, saving: false } })

        expect(wrapper.find('[data-test="ldap-ca-certificate"]').exists()).toBe(false)

        wrapper.vm.useTls = true
        await wrapper.vm.$nextTick()

        const caField = wrapper.findComponent({ name: 'VTextarea' })
        expect(caField.exists()).toBe(true)
        expect(caField.props('label')).toContain('optional')
    })

    it('keeps both bind modes visible and wires Direct bind help to a real tooltip', async () => {
        const wrapper = mountWithPlugins(LdapFields, { props: { config: {}, saving: false } })

        expect(wrapper.find('[data-test="ldap-bind-direct"]').exists()).toBe(true)
        expect(wrapper.find('[data-test="ldap-bind-search"]').exists()).toBe(true)
        expect(wrapper.find('[data-test="ldap-direct-bind-help"]').exists()).toBe(true)
        expect(wrapper.findComponent({ name: 'VTooltip' }).props('text')).toContain("Build the user's DN")
        expect(wrapper.find('[data-test="ldap-bind-mode"] .v-selection-control-group').attributes('aria-describedby')).toBe(
            'ldap-bind-mode-help'
        )
        expect(wrapper.find('[data-test="ldap-bind-mode-help"]').classes()).toContain('auth-provider-help')

        wrapper.vm.bindMode = 'search'
        await wrapper.vm.$nextTick()
        expect(wrapper.find('[data-test="ldap-bind-mode-help"]').text()).toContain('service account')
    })

    it('clears a newly typed bind password when the LDAP bind mode changes', async () => {
        const wrapper = mountWithPlugins(LdapFields, {
            props: { modelValue: 'typed-bind-password', config: { user_dn_template: 'uid={username},dc=x' }, saving: false }
        })

        wrapper.vm.bindMode = 'search'
        await wrapper.vm.$nextTick()

        expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual([''])
    })
})

describe('SAML provider fields', () => {
    it('shows single-IdP and federation as mutually exclusive radio choices', async () => {
        const wrapper = mountWithPlugins(SamlFields, { props: { config: {}, saving: false } })

        expect(wrapper.find('[data-test="saml-mode-single"]').exists()).toBe(true)
        expect(wrapper.find('[data-test="saml-mode-federation"]').exists()).toBe(true)
        expect(wrapper.vm.federationModel).toBe(false)
        expect(wrapper.find('[data-test="saml-connection-mode-help"]').text()).toContain('one identity provider')

        wrapper.vm.federationModel = true
        await wrapper.vm.$nextTick()
        expect(wrapper.find('[data-test="saml-connection-mode-help"]').text()).toContain('whole federation')
    })

    it('disables keypair generation while a generation request is in flight', async () => {
        const wrapper = mountWithPlugins(SamlFields, {
            props: { config: {}, saving: false, generatingKeypair: true }
        })
        wrapper.vm.activeTab = 'keypair'
        await wrapper.vm.$nextTick()

        const button = wrapper.find('[data-test="saml-generate-keypair"]')
        expect(button.attributes('disabled')).toBeDefined()
    })
})
