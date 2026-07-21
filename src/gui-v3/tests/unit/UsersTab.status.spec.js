import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mountWithPlugins } from '../helpers/mount-helpers'
import UsersTab from '@/components/config/access-management/UsersTab.vue'
import { useConfigStore } from '@/stores/config'
import { updateUserStatus, deleteUser } from '@/api/config'

vi.mock('@/api/config', () => ({
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

const USERS = [
    {
        id: 1,
        username: 'admin',
        name: 'Admin',
        status: 'active',
        organizations: [{ id: 1, name: 'CERT' }],
        identities: [],
        has_password: true,
        mfa: { totp: true, passkeys: 0 }
    },
    {
        id: 2,
        username: 'newcomer',
        name: 'New Comer',
        status: 'pending',
        organizations: [],
        identities: [{ id: 9, provider_name: 'Corp SAML', external_username: 'newcomer@idp' }],
        has_password: false,
        mfa: { totp: false, passkeys: 0 }
    },
    {
        id: 3,
        username: 'gone',
        name: 'Gone Away',
        status: 'disabled',
        organizations: [],
        identities: [],
        has_password: true,
        mfa: { totp: false, passkeys: 0 }
    }
]

async function mountTab() {
    const wrapper = mountWithPlugins(UsersTab)
    const store = useConfigStore()
    store.users = { total_count: USERS.length, items: USERS }
    await new Promise((resolve) => setTimeout(resolve, 0))
    store.users = { total_count: USERS.length, items: USERS }
    await wrapper.vm.$nextTick()
    return { wrapper, store }
}

describe('UsersTab - status and login methods', () => {
    beforeEach(() => {
        vi.clearAllMocks()
    })

    it('renders a status chip per user', async () => {
        const { wrapper } = await mountTab()
        const text = wrapper.text()

        expect(text).toContain('Active')
        expect(text).toContain('Pending approval')
        expect(text).toContain('Disabled')
    })

    it('maps statuses to colours', async () => {
        const { wrapper } = await mountTab()
        expect(wrapper.vm.statusColor('pending')).toBe('warning')
        expect(wrapper.vm.statusColor('disabled')).toBe('grey')
        expect(wrapper.vm.statusColor('active')).toBe('success')
        // users predating the status column render as active
        expect(wrapper.vm.statusColor(undefined)).toBe('success')
    })

    it('lists the login methods of each user (local password and linked providers)', async () => {
        const { wrapper } = await mountTab()
        const text = wrapper.text()

        expect(text).toContain('local') // admin has a password
        expect(text).toContain('Corp SAML') // newcomer is linked to the SAML provider
    })

    it('flags users with an MFA enrollment', async () => {
        const { wrapper } = await mountTab()
        expect(wrapper.vm.hasMfa(USERS[0])).toBe(true) // TOTP enrolled
        expect(wrapper.vm.hasMfa(USERS[1])).toBe(false)
        expect(wrapper.vm.hasMfa({ mfa: { totp: false, passkeys: 2 } })).toBe(true) // passkeys count too
    })

    it('filters the table by status', async () => {
        const { wrapper } = await mountTab()
        expect(wrapper.vm.filteredUsers).toHaveLength(3)

        wrapper.vm.statusFilter = 'pending'
        await wrapper.vm.$nextTick()

        expect(wrapper.vm.filteredUsers).toHaveLength(1)
        expect(wrapper.vm.filteredUsers[0].username).toBe('newcomer')
    })

    it('approves a pending user', async () => {
        const { wrapper } = await mountTab()

        await wrapper.vm.setStatus(USERS[1], 'active')

        expect(updateUserStatus).toHaveBeenCalledWith(2, 'active')
    })

    it('disables an active user and re-enables a disabled one', async () => {
        const { wrapper } = await mountTab()

        await wrapper.vm.setStatus(USERS[0], 'disabled')
        expect(updateUserStatus).toHaveBeenCalledWith(1, 'disabled')

        await wrapper.vm.setStatus(USERS[2], 'active')
        expect(updateUserStatus).toHaveBeenCalledWith(3, 'active')
    })

    it('notifies the user when a status change fails', async () => {
        const { wrapper } = await mountTab()
        updateUserStatus.mockRejectedValueOnce(new Error('last admin'))
        const dispatched = vi.spyOn(window, 'dispatchEvent')

        await wrapper.vm.setStatus(USERS[0], 'disabled')

        expect(dispatched).toHaveBeenCalledWith(expect.objectContaining({ detail: expect.objectContaining({ type: 'error' }) }))
    })

    it('deletes a confirmed user', async () => {
        const { wrapper } = await mountTab()

        wrapper.vm.handleDelete(USERS[2])
        await wrapper.vm.confirmDelete()

        expect(deleteUser).toHaveBeenCalledWith(expect.objectContaining({ id: 3 }))
    })

    it('clears editItem when the dialog closes so a row can be re-edited', async () => {
        const { wrapper } = await mountTab()

        wrapper.vm.handleEdit(USERS[0])
        await wrapper.vm.$nextTick()
        expect(wrapper.vm.editItem).toEqual(USERS[0])

        wrapper.vm.onDialogChange(false)
        await wrapper.vm.$nextTick()
        expect(wrapper.vm.editItem).toBeNull()
    })
})
