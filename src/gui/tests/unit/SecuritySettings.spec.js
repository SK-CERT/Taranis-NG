import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mountWithPlugins } from '../helpers/mount-helpers'
import SecuritySettings from '@/components/SecuritySettings.vue'
import {
    getMyTotp,
    beginMyTotpEnrollment,
    confirmMyTotpEnrollment,
    disableMyTotp,
    getMyPasskeys,
    beginPasskeyRegistration,
    finishPasskeyRegistration,
    renamePasskey,
    deletePasskey
} from '@/api/user'

vi.mock('@/api/user', () => ({
    getMyTotp: vi.fn(),
    beginMyTotpEnrollment: vi.fn(),
    confirmMyTotpEnrollment: vi.fn(),
    disableMyTotp: vi.fn(),
    getMyPasskeys: vi.fn(),
    beginPasskeyRegistration: vi.fn(),
    finishPasskeyRegistration: vi.fn(),
    renamePasskey: vi.fn(),
    deletePasskey: vi.fn()
}))

vi.mock('qrcode', () => ({
    default: { toDataURL: vi.fn().mockResolvedValue('data:image/png;base64,QR') }
}))

vi.mock('@simplewebauthn/browser', () => ({
    startRegistration: vi.fn().mockResolvedValue({ id: 'new-credential' })
}))

const PASSKEYS = [{ id: 1, name: 'YubiKey', created_at: '2026-07-01 10:00', last_used_at: null }]

/** Mount the security panel with the given backend state already loaded. */
async function mountSecurity({ totpEnabled = false, passkeys = [] } = {}) {
    getMyTotp.mockResolvedValue({ data: { enabled: totpEnabled } })
    getMyPasskeys.mockResolvedValue({ data: { items: passkeys } })
    const wrapper = mountWithPlugins(SecuritySettings, { props: { loadTrigger: 1 } })
    await new Promise((resolve) => setTimeout(resolve, 0))
    await wrapper.vm.$nextTick()
    return wrapper
}

describe('SecuritySettings', () => {
    beforeEach(() => {
        vi.clearAllMocks()
    })

    // ── TOTP ──────────────────────────────────────
    it('loads the TOTP status and passkeys on mount', async () => {
        const wrapper = await mountSecurity({ totpEnabled: true, passkeys: PASSKEYS })

        expect(getMyTotp).toHaveBeenCalled()
        expect(getMyPasskeys).toHaveBeenCalled()
        expect(wrapper.vm.totpEnabled).toBe(true)
        expect(wrapper.vm.passkeys).toHaveLength(1)
        expect(wrapper.text()).toContain('YubiKey')
    })

    it('offers enrollment when TOTP is off', async () => {
        const wrapper = await mountSecurity({ totpEnabled: false })
        expect(wrapper.text()).toContain('Enable')
        expect(wrapper.text()).toContain('Disabled')
    })

    it('renders the QR code when enrollment starts', async () => {
        const wrapper = await mountSecurity()
        beginMyTotpEnrollment.mockResolvedValue({ data: { otpauth_uri: 'otpauth://totp/Taranis:admin?secret=ABC' } })

        await wrapper.vm.startTotpEnrollment()
        await wrapper.vm.$nextTick()

        expect(wrapper.vm.qrDataUrl).toBe('data:image/png;base64,QR')
        expect(wrapper.find('img[alt="TOTP QR code"]').exists()).toBe(true)
    })

    it('activates TOTP with a confirmation code', async () => {
        const wrapper = await mountSecurity()
        confirmMyTotpEnrollment.mockResolvedValue({ data: { enabled: true } })

        wrapper.vm.totpCode = '123456'
        await wrapper.vm.confirmTotpEnrollment()

        expect(confirmMyTotpEnrollment).toHaveBeenCalledWith('123456')
        expect(wrapper.vm.totpEnabled).toBe(true)
        expect(wrapper.vm.qrDataUrl).toBe('')
    })

    it('reports a wrong confirmation code without enabling TOTP', async () => {
        const wrapper = await mountSecurity()
        const error = new Error('bad code')
        error.response = { data: { error: 'Invalid authentication code' } }
        confirmMyTotpEnrollment.mockRejectedValue(error)

        wrapper.vm.totpCode = '000000'
        await wrapper.vm.confirmTotpEnrollment()
        await wrapper.vm.$nextTick()

        expect(wrapper.vm.totpEnabled).toBe(false)
        expect(wrapper.vm.totpError).toBe('Invalid authentication code')
    })

    it('disables TOTP with a current code', async () => {
        const wrapper = await mountSecurity({ totpEnabled: true })
        disableMyTotp.mockResolvedValue({ data: { enabled: false } })

        wrapper.vm.totpCode = '123456'
        await wrapper.vm.disableTotp()

        expect(disableMyTotp).toHaveBeenCalledWith('123456')
        expect(wrapper.vm.totpEnabled).toBe(false)
    })

    // ── Passkeys ──────────────────────────────────
    it('says so when no passkey is registered', async () => {
        const wrapper = await mountSecurity()
        expect(wrapper.text()).toContain('No passkeys registered')
    })

    it('registers a passkey through the WebAuthn ceremony', async () => {
        const wrapper = await mountSecurity()
        beginPasskeyRegistration.mockResolvedValue({ data: { options: { challenge: 'abc' }, challenge_id: 'chal-1' } })
        finishPasskeyRegistration.mockResolvedValue({ data: { id: 2, name: 'Laptop' } })
        getMyPasskeys.mockResolvedValue({ data: { items: [{ id: 2, name: 'Laptop' }] } })

        wrapper.vm.passkeyName = 'Laptop'
        await wrapper.vm.confirmName()
        await wrapper.vm.$nextTick()

        expect(beginPasskeyRegistration).toHaveBeenCalled()
        expect(finishPasskeyRegistration).toHaveBeenCalledWith('chal-1', { id: 'new-credential' }, 'Laptop')
        expect(wrapper.vm.passkeys).toHaveLength(1)
    })

    it('surfaces a failed registration (e.g. passkey provider not configured)', async () => {
        const wrapper = await mountSecurity()
        const error = new Error('not configured')
        error.response = { data: { error: 'Passkey login is not configured' } }
        beginPasskeyRegistration.mockRejectedValue(error)

        wrapper.vm.passkeyName = 'Laptop'
        await wrapper.vm.confirmName()
        await wrapper.vm.$nextTick()

        expect(wrapper.vm.passkeyError).toBe('Passkey login is not configured')
    })

    it('renames a passkey', async () => {
        const wrapper = await mountSecurity({ passkeys: PASSKEYS })
        renamePasskey.mockResolvedValue({ data: {} })

        wrapper.vm.startRename(PASSKEYS[0])
        wrapper.vm.passkeyName = 'Work key'
        await wrapper.vm.confirmName()

        expect(renamePasskey).toHaveBeenCalledWith(1, 'Work key')
        // a rename must not start a new WebAuthn ceremony
        expect(beginPasskeyRegistration).not.toHaveBeenCalled()
    })

    it('removes a passkey', async () => {
        const wrapper = await mountSecurity({ passkeys: PASSKEYS })
        deletePasskey.mockResolvedValue({ data: {} })
        getMyPasskeys.mockResolvedValue({ data: { items: [] } })

        await wrapper.vm.removePasskey(PASSKEYS[0])

        expect(deletePasskey).toHaveBeenCalledWith(1)
        expect(wrapper.vm.passkeys).toHaveLength(0)
    })
})
