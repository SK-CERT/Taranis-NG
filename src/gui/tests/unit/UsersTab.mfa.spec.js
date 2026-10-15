import { describe, it, expect, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { mountWithPlugins } from '../helpers/mount-helpers'
import UsersTab from '@/components/config/access-management/UsersTab.vue'

const YUBIKEY = 'cb69481e-8ff7-4039-93ec-0a2729a154a8'
const UNLISTED = '11111111-2222-3333-4444-555555555555'
const ICON = 'data:image/svg+xml;base64,PHN2Zy8+'

// Hoisted so the vi.mock factory below — hoisted above all top-level code — can
// serve the same fixtures the assertions use.
const { USERS } = vi.hoisted(() => ({
    USERS: [
        {
            id: 1,
            username: 'both',
            name: 'Both Factors',
            status: 'active',
            roles: [],
            organizations: [],
            identities: [],
            has_password: true,
            mfa: {
                totp: true,
                passkeys: 3,
                passkey_details: [
                    {
                        id: 11,
                        name: 'Work key',
                        aaguid: 'cb69481e-8ff7-4039-93ec-0a2729a154a8',
                        authenticator: { name: 'YubiKey 5 Series', icon_light: 'data:image/svg+xml;base64,PHN2Zy8+', icon_dark: null },
                        authenticator_lookup: true
                    },
                    {
                        id: 13,
                        name: 'Odd key',
                        aaguid: '11111111-2222-3333-4444-555555555555',
                        authenticator: null,
                        authenticator_lookup: true
                    },
                    { id: 12, name: 'Old key', aaguid: null, authenticator: null, authenticator_lookup: true }
                ]
            }
        },
        {
            id: 2,
            username: 'totp-only',
            name: 'TOTP Only',
            status: 'active',
            roles: [],
            organizations: [],
            identities: [],
            has_password: true,
            mfa: { totp: true, passkeys: 0, passkey_details: [] }
        },
        {
            id: 3,
            username: 'none',
            name: 'No Factor',
            status: 'active',
            roles: [],
            organizations: [],
            identities: [],
            has_password: true,
            mfa: { totp: false, passkeys: 0, passkey_details: [] }
        }
    ]
}))

// Every export the component chain reaches must be listed: the factory replaces the
// module wholesale, and a missing one throws on access, which UsersTab swallows into
// console.error. `getAllUsers` is what the store's loadUsers calls.
vi.mock('@/api/config', () => ({
    getAllUsers: vi.fn().mockResolvedValue({ data: { total_count: USERS.length, items: USERS } }),
    updateUserStatus: vi.fn().mockResolvedValue({ data: {} }),
    deleteUser: vi.fn().mockResolvedValue({ data: {} }),
    resetUserMfa: vi.fn().mockResolvedValue({ data: {} }),
    createNewUser: vi.fn().mockResolvedValue({ data: {} }),
    updateUser: vi.fn().mockResolvedValue({ data: {} }),
    getAllOrganizations: vi.fn().mockResolvedValue({ data: { items: [] } }),
    getAllRoles: vi.fn().mockResolvedValue({ data: { items: [] } }),
    getAllPermissions: vi.fn().mockResolvedValue({ data: { items: [] } }),
    getAllAuthProviders: vi.fn().mockResolvedValue({ data: { items: [] } })
}))

vi.mock('@/composables/useAuth', () => ({
    useAuth: () => ({ checkPermission: () => true })
}))

async function mountTab() {
    const wrapper = mountWithPlugins(UsersTab)
    await flushPromises()
    await wrapper.vm.$nextTick()
    return wrapper
}

const rowOf = (wrapper, username) => wrapper.findAll('tbody tr').find((row) => row.text().includes(username))
const passkeyIcons = (row) => row.findAll('[data-test="user-mfa-passkey"]')

describe('UsersTab - second factors', () => {
    it('shows a TOTP icon, named in its tooltip', async () => {
        const wrapper = await mountTab()
        const totp = rowOf(wrapper, 'both').get('[data-test="user-mfa-totp"]')

        expect(totp.attributes('title')).toBe('Authenticator app (TOTP)')
        expect(totp.attributes('aria-label')).toBe('Authenticator app (TOTP)')
    })

    it("shows each passkey by its authenticator's icon, with the name or the AAGUID as the tooltip", async () => {
        const wrapper = await mountTab()
        const [yubikey, unlisted, legacy] = passkeyIcons(rowOf(wrapper, 'both'))

        expect(passkeyIcons(rowOf(wrapper, 'both'))).toHaveLength(3)
        expect(yubikey.get('img').attributes('src')).toBe(ICON)
        expect(yubikey.attributes('title')).toBe('YubiKey 5 Series')
        expect(yubikey.attributes('aria-label')).toBe('YubiKey 5 Series')
        expect(unlisted.find('img').exists()).toBe(false)
        expect(unlisted.attributes('title')).toBe(`AAGUID ${UNLISTED}`)
        expect(legacy.attributes('title')).toBe('Not recorded')
        // Icons only: no names or AAGUIDs written out in the table.
        expect(rowOf(wrapper, 'both').text()).not.toContain('YubiKey 5 Series')
        expect(rowOf(wrapper, 'both').text()).not.toContain(YUBIKEY)
    })

    it('shows only the factors a user has', async () => {
        const wrapper = await mountTab()
        const row = rowOf(wrapper, 'totp-only')

        expect(row.find('[data-test="user-mfa-totp"]').exists()).toBe(true)
        expect(passkeyIcons(row)).toHaveLength(0)
    })

    it('shows no second-factor icons for a user without one', async () => {
        const wrapper = await mountTab()
        const row = rowOf(wrapper, 'No Factor')

        expect(row.find('[data-test="user-mfa-totp"]').exists()).toBe(false)
        expect(passkeyIcons(row)).toHaveLength(0)
    })
})
