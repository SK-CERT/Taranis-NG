import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mountWithPlugins } from '../helpers/mount-helpers'
import SecurityTab from '@/components/config/access-management/SecurityTab.vue'
import SuggestField from '@/components/common/SuggestField.vue'
import { getSecuritySettings, updateSecuritySettings } from '@/api/config'

vi.mock('@/api/config', () => ({
    getSecuritySettings: vi.fn(),
    updateSecuritySettings: vi.fn()
}))

vi.mock('@/composables/useAuth', () => ({
    useAuth: () => ({ checkPermission: () => true })
}))

const SAVED = {
    require_mfa: true,
    passkey_enabled: true,
    passkey_second_factor: true,
    rp_id: 'taranis.example.org',
    rp_name: 'Taranis NG',
    origins: 'https://taranis.example.org',
    updated_by: 'Admin',
    updated_at: '2026-07-12 23:00'
}

/** Mount the tab with the given persisted settings already loaded. */
async function mountTab(
    settings = { require_mfa: false, passkey_enabled: false, passkey_second_factor: true, rp_id: '', rp_name: '', origins: '' }
) {
    getSecuritySettings.mockResolvedValue({ data: settings })
    const wrapper = mountWithPlugins(SecurityTab)
    await new Promise((resolve) => setTimeout(resolve, 0))
    await wrapper.vm.$nextTick()
    return wrapper
}

/** Stub the v-form validation harness, which needs a real DOM form. */
function stubValidation(wrapper, valid = true) {
    wrapper.vm.formRef = { validate: () => Promise.resolve({ valid }) }
}

describe('SecurityTab (passkey relying-party settings)', () => {
    beforeEach(() => {
        vi.clearAllMocks()
    })

    it('loads the persisted settings on mount', async () => {
        const wrapper = await mountTab(SAVED)

        expect(getSecuritySettings).toHaveBeenCalled()
        expect(wrapper.vm.settings.passkey_enabled).toBe(true)
        expect(wrapper.vm.settings.rp_id).toBe('taranis.example.org')
        expect(wrapper.vm.settings.origins).toBe('https://taranis.example.org')
    })

    it('locale-formats the audit timestamp without changing API data and isolates both values', async () => {
        const rawTimestamp = '2026-07-12T21:00:00Z'
        const wrapper = await mountTab({ ...SAVED, updated_by: 'المشرف', updated_at: rawTimestamp })
        wrapper.vm.$i18n.locale = 'ar'
        await wrapper.vm.$nextTick()
        const expectedTimestamp = new Intl.DateTimeFormat('ar', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(rawTimestamp))
        const values = wrapper.findAll('bdi')

        expect(wrapper.vm.settings.updated_at).toBe(rawTimestamp)
        expect(wrapper.vm.updatedAtDisplay).toBe(expectedTimestamp)
        expect(values.filter((value) => value.attributes('dir') === 'auto').map((value) => value.text())).toEqual([
            'المشرف',
            expectedTimestamp
        ])
    })

    it('preserves an invalid audit timestamp as auto-direction display text', async () => {
        const rawTimestamp = 'وقت قديم'
        const wrapper = await mountTab({ ...SAVED, updated_at: rawTimestamp })

        expect(wrapper.vm.updatedAtDisplay).toBe(rawTimestamp)
        expect(wrapper.findAll('bdi[dir="auto"]').map((value) => value.text())).toContain(rawTimestamp)
        expect(wrapper.vm.settings.updated_at).toBe(rawTimestamp)
    })

    it('uses logical inline-end spacing for every heading icon', async () => {
        const wrapper = await mountTab()

        expect(wrapper.findAll('.me-2')).toHaveLength(3)
        expect(wrapper.find('.mr-2').exists()).toBe(false)
    })

    it('normalizes nullable relying-party fields from a freshly migrated database', async () => {
        const wrapper = await mountTab({
            require_mfa: false,
            passkey_enabled: false,
            passkey_second_factor: true,
            rp_id: null,
            rp_name: null,
            origins: null
        })

        expect(wrapper.vm.settings.rp_id).toBe('')
        expect(wrapper.vm.settings.rp_name).toBe('')
        expect(wrapper.vm.settings.origins).toBe('')
        expect(wrapper.vm.suggestedRpId).toBe(window.location.hostname)
        expect(wrapper.text()).toContain('Passkeys (WebAuthn)')
    })

    it('explains that passkeys are user credentials, not an identity provider', async () => {
        const wrapper = await mountTab()
        expect(wrapper.text()).toContain('Passkeys (WebAuthn)')
        expect(wrapper.text()).toContain('credentials owned by users')
    })

    it('warns that WebAuthn needs a secure context', async () => {
        const wrapper = await mountTab()
        expect(wrapper.text()).toContain('secure context')
    })

    it('suggests the current host as the relying-party ID and origin', async () => {
        const wrapper = await mountTab()
        expect(wrapper.vm.suggestedRpId).toBe(window.location.hostname)
        expect(wrapper.vm.suggestedOrigin).toBe(window.location.origin)
    })

    it('suggests a safe relying-party host from configured origins and applies it with the wand', async () => {
        const wrapper = await mountTab({
            require_mfa: false,
            passkey_enabled: false,
            passkey_second_factor: true,
            rp_id: '',
            rp_name: '',
            origins: 'https://login.example.org:8443, https://backup.example.org'
        })
        const field = wrapper.findComponent(SuggestField)

        expect(wrapper.vm.suggestedRpId).toBe('login.example.org')
        expect(field.props('suggested')).toBe('login.example.org')
        field.vm.applySuggested()
        await wrapper.vm.$nextTick()
        expect(wrapper.vm.settings.rp_id).toBe('login.example.org')
    })

    it('changes the global MFA and passkey explanations with their switch state', async () => {
        const wrapper = await mountTab()

        expect(wrapper.vm.requireMfaHint).toContain('no site-wide MFA requirement')
        expect(wrapper.vm.passkeyEnabledHint).toContain('unavailable')

        wrapper.vm.settings.require_mfa = true
        wrapper.vm.settings.passkey_enabled = true
        await wrapper.vm.$nextTick()

        expect(wrapper.vm.requireMfaHint).toContain('Every user must enroll')
        expect(wrapper.vm.passkeyEnabledHint).toContain('the switches below decide where a passkey may be used')
    })

    // ── Validation ────────────────────────────────
    it('requires rp_id and origins only when passkeys are switched on', async () => {
        const wrapper = await mountTab()

        // feature off: an empty draft is acceptable
        expect(wrapper.vm.rpIdRules[0]('')).toBe(true)
        expect(wrapper.vm.originsRules[0]('')).toBe(true)

        wrapper.vm.settings.passkey_enabled = true
        await wrapper.vm.$nextTick()

        expect(wrapper.vm.rpIdRules[0]('')).not.toBe(true)
        expect(wrapper.vm.originsRules[0]('')).not.toBe(true)
        expect(wrapper.vm.rpIdRules[0]('taranis.example.org')).toBe(true)
    })

    it('rejects origins that are not absolute URLs', async () => {
        const wrapper = await mountTab()
        const originRule = wrapper.vm.originsRules[1]

        expect(originRule('https://taranis.example.org')).toBe(true)
        expect(originRule('https://taranis.example.org, http://localhost:4444')).toBe(true)
        // a bare domain, or a URL with a path, is not a valid WebAuthn origin
        expect(originRule('taranis.example.org')).not.toBe(true)
        expect(originRule('https://taranis.example.org/login')).not.toBe(true)
    })

    // ── Saving ────────────────────────────────────
    it('saves the settings and reflects the server response', async () => {
        const wrapper = await mountTab()
        updateSecuritySettings.mockResolvedValue({ data: SAVED })
        stubValidation(wrapper)

        wrapper.vm.settings.passkey_enabled = true
        wrapper.vm.settings.rp_id = 'taranis.example.org'
        wrapper.vm.settings.origins = 'https://taranis.example.org'
        await wrapper.vm.save()

        expect(updateSecuritySettings).toHaveBeenCalledWith(
            expect.objectContaining({
                passkey_enabled: true,
                rp_id: 'taranis.example.org',
                origins: 'https://taranis.example.org'
            })
        )
        expect(wrapper.vm.settings.updated_by).toBe('Admin')
    })

    // ── Site-wide MFA policy ──────────────────────
    // One of four levels that can demand a second factor (site, organization, login
    // method, user); the backend ORs them.
    it('saves the site-wide two-factor requirement', async () => {
        const wrapper = await mountTab()
        updateSecuritySettings.mockResolvedValue({ data: SAVED })
        stubValidation(wrapper)

        wrapper.vm.settings.require_mfa = true
        await wrapper.vm.save()

        expect(updateSecuritySettings).toHaveBeenCalledWith(expect.objectContaining({ require_mfa: true }))
    })

    it('saves the passkey second-factor switch', async () => {
        const wrapper = await mountTab(SAVED)
        updateSecuritySettings.mockResolvedValue({ data: { ...SAVED, passkey_second_factor: false } })
        stubValidation(wrapper)

        wrapper.vm.settings.passkey_second_factor = false
        await wrapper.vm.save()

        expect(updateSecuritySettings).toHaveBeenCalledWith(expect.objectContaining({ passkey_second_factor: false }))
    })

    it('saves the passkey first-factor switch', async () => {
        const wrapper = await mountTab(SAVED)
        updateSecuritySettings.mockResolvedValue({ data: { ...SAVED, passkey_first_factor: false } })
        stubValidation(wrapper)

        // Keeping passkeys on as a second factor while withdrawing passwordless sign-in.
        wrapper.vm.settings.passkey_first_factor = false
        await wrapper.vm.save()

        expect(updateSecuritySettings).toHaveBeenCalledWith(expect.objectContaining({ passkey_first_factor: false }))
    })

    it('cannot allow a passkey sign-in while passkeys are switched off', async () => {
        const wrapper = await mountTab()

        const firstFactor = wrapper.find('[data-test="security-passkey-first-factor"] input')
        expect(firstFactor.attributes('disabled')).toBeDefined()

        wrapper.vm.settings.passkey_enabled = true
        await wrapper.vm.$nextTick()

        expect(wrapper.find('[data-test="security-passkey-first-factor"] input').attributes('disabled')).toBeUndefined()
    })

    it('cannot accept passkeys as a second factor while passkeys are switched off', async () => {
        const wrapper = await mountTab()

        const secondFactor = wrapper.find('[data-test="security-passkey-second-factor"] input')
        expect(secondFactor.attributes('disabled')).toBeDefined()

        wrapper.vm.settings.passkey_enabled = true
        await wrapper.vm.$nextTick()

        expect(wrapper.find('[data-test="security-passkey-second-factor"] input').attributes('disabled')).toBeUndefined()
    })

    it('does not call the API when the form is invalid', async () => {
        const wrapper = await mountTab()
        stubValidation(wrapper, false)

        await wrapper.vm.save()

        expect(updateSecuritySettings).not.toHaveBeenCalled()
    })

    it('surfaces the backend rejection (e.g. enabled without a relying party)', async () => {
        const wrapper = await mountTab()
        const error = new Error('bad request')
        error.response = { data: { error: 'Passkey sign-in requires a relying-party ID and at least one origin' } }
        updateSecuritySettings.mockRejectedValue(error)
        stubValidation(wrapper)

        await wrapper.vm.save()
        await wrapper.vm.$nextTick()

        expect(wrapper.vm.errorMessage).toContain('relying-party ID')
        expect(wrapper.find('.v-alert.text-error, .v-alert').exists()).toBe(true)
    })

    // ── API key policy ────────────────────────────
    it('shows the API key policy and edits the site-wide allowlist one network per line', async () => {
        const wrapper = await mountTab({
            ...SAVED,
            api_key_require_expiry: true,
            api_key_max_days: 90,
            api_key_require_allowlist: false,
            api_key_allowed_ips: ['185.10.0.0/16', '2a01:4f8::/32']
        })

        expect(wrapper.find('[data-test="security-api-keys"]').exists()).toBe(true)
        expect(wrapper.vm.settings.api_key_require_expiry).toBe(true)
        expect(wrapper.vm.maxDaysInput).toBe(90)
        expect(wrapper.vm.siteAllowlist).toBe('185.10.0.0/16\n2a01:4f8::/32')
        expect(wrapper.vm.siteAllowlistNarrowed).toBe(false)
    })

    it('saves the API key policy: a cleared maximum is null and the allowlist a list', async () => {
        const wrapper = await mountTab({ ...SAVED, api_key_max_days: 30, api_key_allowed_ips: [] })
        updateSecuritySettings.mockResolvedValue({ data: { ...SAVED, api_key_allowed_ips: ['185.10.0.0/16'] } })
        stubValidation(wrapper)

        wrapper.vm.maxDaysInput = ''
        wrapper.vm.siteAllowlist = '185.10.0.0/16\n\n'
        await wrapper.vm.save()

        expect(updateSecuritySettings).toHaveBeenCalledWith(
            expect.objectContaining({ api_key_max_days: null, api_key_allowed_ips: ['185.10.0.0/16'] })
        )
        expect(wrapper.vm.siteAllowlist).toBe('185.10.0.0/16')
    })

    it('validates the maximum lifetime and the allowlist entries', async () => {
        const wrapper = await mountTab()
        const [maxDaysRule] = wrapper.vm.maxDaysRules
        const [allowlistRule] = wrapper.vm.siteAllowlistRules

        expect(maxDaysRule(null)).toBe(true)
        expect(maxDaysRule('30')).toBe(true)
        expect(maxDaysRule('0')).not.toBe(true)
        expect(maxDaysRule('1.5')).not.toBe(true)
        expect(allowlistRule('185.10.0.0/16\n2a01:4f8::1')).toBe(true)
        expect(allowlistRule('185.10.0.0/16\nexample.com')).toContain('example.com')
        expect(allowlistRule('192.168.0.0/16')).toBe('Only public addresses can be listed, not: 192.168.0.0/16')
    })

    it('warns before a site-wide allowlist that would refuse addresses allowed now', async () => {
        const wrapper = await mountTab({ ...SAVED, api_key_allowed_ips: ['185.10.0.0/16', '185.20.30.0/24'] })

        wrapper.vm.siteAllowlist = '185.10.0.0/16\n185.20.30.0/24\n185.40.50.0/24'
        await wrapper.vm.$nextTick()
        expect(wrapper.vm.siteAllowlistNarrowed).toBe(false)

        wrapper.vm.siteAllowlist = '185.10.0.0/16'
        await wrapper.vm.$nextTick()
        expect(wrapper.vm.siteAllowlistNarrowed).toBe(true)
        expect(wrapper.find('[data-test="security-api-key-allowlist-warning"]').exists()).toBe(true)
    })
})
