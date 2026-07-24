import { describe, it, expect, beforeEach, vi } from 'vitest'
import ApiService from '@/services/api_service'
import {
    getAllAuthProviders,
    createNewAuthProvider,
    updateAuthProvider,
    deleteAuthProvider,
    updateUserStatus,
    resetUserMfa
} from '@/api/config'
import {
    getLoginMethods,
    mfaTotp,
    mfaTotpEnroll,
    mfaWebauthnBegin,
    mfaWebauthnFinish,
    passkeyLoginBegin,
    passkeyLoginFinish
} from '@/api/auth'
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

vi.mock('@/services/api_service', () => ({
    default: {
        get: vi.fn().mockResolvedValue({ data: {} }),
        post: vi.fn().mockResolvedValue({ data: {} }),
        put: vi.fn().mockResolvedValue({ data: {} }),
        delete: vi.fn().mockResolvedValue({ data: {} })
    }
}))

describe('Auth provider config API', () => {
    beforeEach(() => {
        vi.clearAllMocks()
    })

    it('lists providers with the search filter', () => {
        getAllAuthProviders({ search: 'corp' })
        expect(ApiService.get).toHaveBeenCalledWith('/config/auth-providers?search=corp')
    })

    it('creates a provider', () => {
        const provider = { id: -1, name: 'Corp SSO', kind: 'oidc' }
        createNewAuthProvider(provider)
        expect(ApiService.post).toHaveBeenCalledWith('/config/auth-providers', provider)
    })

    it('updates a provider on its own id', () => {
        const provider = { id: 7, name: 'Corp SSO', kind: 'oidc' }
        updateAuthProvider(provider)
        expect(ApiService.put).toHaveBeenCalledWith('/config/auth-providers/7', provider)
    })

    it('deletes a provider', () => {
        deleteAuthProvider({ id: 7 })
        expect(ApiService.delete).toHaveBeenCalledWith('/config/auth-providers/7')
    })

    it('changes a user status through the dedicated endpoint', () => {
        updateUserStatus(3, 'active')
        expect(ApiService.put).toHaveBeenCalledWith('/config/users/3/status', { status: 'active' })
    })

    it('resets a user MFA enrollment', () => {
        resetUserMfa(3)
        expect(ApiService.post).toHaveBeenCalledWith('/config/users/3/reset-mfa', {})
    })
})

describe('Auth API (login methods, MFA, passkeys)', () => {
    beforeEach(() => {
        vi.clearAllMocks()
    })

    it('fetches the public login methods', () => {
        getLoginMethods()
        expect(ApiService.get).toHaveBeenCalledWith('/auth/methods')
    })

    it('submits a TOTP code with the scoped MFA token', () => {
        mfaTotp('mfa-token', '123456')
        expect(ApiService.post).toHaveBeenCalledWith('/auth/mfa/totp', { mfa_token: 'mfa-token', code: '123456' })
    })

    it('begins forced TOTP enrollment without a code, confirms with one', () => {
        mfaTotpEnroll('enroll-token')
        expect(ApiService.post).toHaveBeenCalledWith('/auth/mfa/totp/enroll', { enroll_token: 'enroll-token' })

        mfaTotpEnroll('enroll-token', '654321')
        expect(ApiService.post).toHaveBeenCalledWith('/auth/mfa/totp/enroll', { enroll_token: 'enroll-token', code: '654321' })
    })

    it('runs the passkey second-factor ceremony', () => {
        mfaWebauthnBegin('mfa-token')
        expect(ApiService.post).toHaveBeenCalledWith('/auth/mfa/webauthn/begin', { mfa_token: 'mfa-token' })

        mfaWebauthnFinish('mfa-token', 'chal-1', { id: 'cred' })
        expect(ApiService.post).toHaveBeenCalledWith('/auth/mfa/webauthn/finish', {
            mfa_token: 'mfa-token',
            challenge_id: 'chal-1',
            credential: { id: 'cred' }
        })
    })

    it('runs the passwordless passkey login ceremony', () => {
        passkeyLoginBegin()
        expect(ApiService.post).toHaveBeenCalledWith('/auth/webauthn/login/begin', {})

        passkeyLoginFinish('chal-2', { id: 'cred' })
        expect(ApiService.post).toHaveBeenCalledWith('/auth/webauthn/login/finish', { challenge_id: 'chal-2', credential: { id: 'cred' } })
    })
})

describe('Self-service security API', () => {
    beforeEach(() => {
        vi.clearAllMocks()
    })

    it('reads the TOTP status', () => {
        getMyTotp()
        expect(ApiService.get).toHaveBeenCalledWith('/users/my-totp')
    })

    it('enrolls and disables TOTP', () => {
        beginMyTotpEnrollment()
        expect(ApiService.post).toHaveBeenCalledWith('/users/my-totp', {})

        confirmMyTotpEnrollment('123456')
        expect(ApiService.post).toHaveBeenCalledWith('/users/my-totp', { code: '123456' })

        // DELETE carries the confirmation code in the request body
        disableMyTotp('123456')
        expect(ApiService.delete).toHaveBeenCalledWith('/users/my-totp', { data: { code: '123456' } })
    })

    it('manages passkeys', () => {
        getMyPasskeys()
        expect(ApiService.get).toHaveBeenCalledWith('/users/my-passkeys')

        beginPasskeyRegistration()
        expect(ApiService.post).toHaveBeenCalledWith('/users/my-passkeys/register-begin', {})

        finishPasskeyRegistration('chal-3', { id: 'cred' }, 'YubiKey')
        expect(ApiService.post).toHaveBeenCalledWith('/users/my-passkeys/register-finish', {
            challenge_id: 'chal-3',
            credential: { id: 'cred' },
            name: 'YubiKey'
        })

        renamePasskey(2, 'Laptop')
        expect(ApiService.put).toHaveBeenCalledWith('/users/my-passkeys/2', { name: 'Laptop' })

        deletePasskey(2)
        expect(ApiService.delete).toHaveBeenCalledWith('/users/my-passkeys/2')
    })
})
