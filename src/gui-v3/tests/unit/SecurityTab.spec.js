import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mountWithPlugins } from '../helpers/mount-helpers'
import SecurityTab from '@/components/config/access-management/SecurityTab.vue'
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
})
