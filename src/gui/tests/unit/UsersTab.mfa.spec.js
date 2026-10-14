import { describe, it, expect, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { defineComponent, h } from 'vue'
import { mountWithPlugins } from '../helpers/mount-helpers'
import UsersTab from '@/components/config/access-management/UsersTab.vue'

const YUBIKEY = 'cb69481e-8ff7-4039-93ec-0a2729a154a8'
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
                passkeys: 2,
                passkey_details: [
                    {
                        id: 11,
                        name: 'Work key',
                        aaguid: 'cb69481e-8ff7-4039-93ec-0a2729a154a8',
                        authenticator: { name: 'YubiKey 5 Series', icon_light: 'data:image/svg+xml;base64,PHN2Zy8+', icon_dark: null }
                    },
                    { id: 12, name: 'Old key', aaguid: null, authenticator: null }
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

// A tooltip renders its content only once hovered, and then into an overlay outside
// the wrapper. This stand-in renders the activator and the content inline.
const InlineTooltip = defineComponent({
    setup(_props, { slots }) {
        return () =>
            h('div', { class: 'tooltip-stub' }, [slots.activator?.({ props: {} }), h('div', { class: 'tooltip-content' }, slots.default?.())])
    }
})

async function mountTab() {
    const wrapper = mountWithPlugins(UsersTab, { global: { stubs: { VTooltip: InlineTooltip } } })
    await flushPromises()
    await wrapper.vm.$nextTick()
    return wrapper
}

const rowOf = (wrapper, username) => wrapper.findAll('tbody tr').find((row) => row.text().includes(username))

describe('UsersTab - second-factor badge', () => {
    it('lists TOTP and every passkey with its authenticator and AAGUID', async () => {
        const wrapper = await mountTab()
        const summary = rowOf(wrapper, 'both').get('[data-test="user-mfa-summary"]')
        const passkeys = summary.findAll('[data-test="user-mfa-passkey"]')

        expect(summary.text()).toContain('Two-factor authentication enabled')
        expect(summary.find('[data-test="user-mfa-totp"]').text()).toContain('Authenticator app (TOTP)')
        expect(summary.text()).toContain('Passkeys')
        expect(passkeys).toHaveLength(2)
        expect(passkeys[0].text()).toContain('Work key')
        expect(passkeys[0].text()).toContain('YubiKey 5 Series')
        expect(passkeys[0].text()).toContain(`AAGUID ${YUBIKEY}`)
        expect(passkeys[0].get('img').attributes('src')).toBe(ICON)
        // A passkey registered before AAGUIDs were recorded still shows up.
        expect(passkeys[1].text()).toContain('Old key')
        expect(passkeys[1].text()).toContain('Not recorded')
    })

    it('shows only the factors a user has', async () => {
        const wrapper = await mountTab()
        const summary = rowOf(wrapper, 'totp-only').get('[data-test="user-mfa-summary"]')

        expect(summary.find('[data-test="user-mfa-totp"]').exists()).toBe(true)
        expect(summary.text()).not.toContain('Passkeys')
        expect(summary.findAll('[data-test="user-mfa-passkey"]')).toHaveLength(0)
    })

    it('gives a user without a second factor no badge', async () => {
        const wrapper = await mountTab()

        expect(rowOf(wrapper, 'No Factor').find('[data-test="user-mfa-badge"]').exists()).toBe(false)
    })

    it('keeps the badge reachable and named for keyboard and screen-reader users', async () => {
        const wrapper = await mountTab()
        const badge = rowOf(wrapper, 'both').get('[data-test="user-mfa-badge"]')

        expect(badge.attributes('tabindex')).toBe('0')
        expect(badge.attributes('aria-label')).toBe('Two-factor authentication enabled')
    })
})
