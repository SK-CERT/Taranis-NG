import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mountWithPlugins } from '../helpers/mount-helpers'
import NewAuthProvider from '@/components/config/auth-providers/NewAuthProvider.vue'
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
    it('offers every provider kind, including SAML 2.0 but not passkeys', async () => {
        const wrapper = await mountDialog()
        const kinds = wrapper.vm.kindOptions.map((option) => option.value)
        // passkeys are credentials owned by users, configured in the Security tab
        expect(kinds).toEqual(['local', 'oidc', 'oauth2', 'saml', 'ldap'])
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

        await wrapper.vm.generateKeypair()

        expect(generateSamlKeypair).toHaveBeenCalledWith('taranis-ng')
        // the private key travels in the write-only secret field, the certificate in the config
        expect(wrapper.vm.secretInput).toContain('BEGIN PRIVATE KEY')
        expect(wrapper.vm.config.sp_certificate).toContain('BEGIN CERTIFICATE')
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
