import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mountWithPlugins } from '../helpers/mount-helpers'
import NewUser from '@/components/config/access-management/NewUser.vue'
import { createNewUser, updateUser } from '@/api/config'

vi.mock('@/api/config', () => ({
    createNewUser: vi.fn().mockResolvedValue({}),
    updateUser: vi.fn().mockResolvedValue({}),
    resetUserMfa: vi.fn().mockResolvedValue({}),
    getAllOrganizations: vi.fn().mockResolvedValue({ data: { items: [{ id: 1, name: 'ACME' }] } }),
    getAllRoles: vi.fn().mockResolvedValue({ data: { items: [{ id: 1, name: 'Admin' }] } }),
    getAllPermissions: vi.fn().mockResolvedValue({ data: { items: [] } }),
    getAllAuthProviders: vi.fn().mockResolvedValue({ data: { items: [{ id: 3, name: 'ACME SAML2', kind: 'saml' }] } })
}))

vi.mock('@/composables/useAuth', () => ({
    useAuth: () => ({ checkPermission: () => true })
}))

/** Mount the user dialog, optionally on an existing user. */
async function mountDialog(editItem = null) {
    const wrapper = mountWithPlugins(NewUser, { props: { modelValue: true, editItem } })
    await new Promise((resolve) => setTimeout(resolve, 0))
    await wrapper.vm.$nextTick()
    wrapper.vm.formRef = { validate: () => Promise.resolve({ valid: true }) }
    return wrapper
}

// The per-user switch is one of four levels that can demand a second factor (site,
// organization, login method, user). The backend ORs them, so this one only ever adds.
describe('NewUser - per-user two-factor requirement', () => {
    beforeEach(() => {
        vi.clearAllMocks()
    })

    it('defaults to not requiring a second factor on a new user', async () => {
        const wrapper = await mountDialog()

        expect(wrapper.vm.localItem.require_mfa).toBe(false)

        wrapper.vm.localItem.username = 'jsmith'
        wrapper.vm.localItem.name = 'John Smith'
        await wrapper.vm.persist()

        expect(createNewUser).toHaveBeenCalledWith(expect.objectContaining({ require_mfa: false }))
    })

    it('sends the requirement when it is switched on', async () => {
        const wrapper = await mountDialog()

        wrapper.vm.localItem.username = 'jsmith'
        wrapper.vm.localItem.name = 'John Smith'
        wrapper.vm.localItem.require_mfa = true
        await wrapper.vm.persist()

        expect(createNewUser).toHaveBeenCalledWith(expect.objectContaining({ require_mfa: true }))
    })

    // The backend refuses an identity that belongs to someone else. Its message names the
    // provider and the account holding it, so the admin can act on it - show that, not
    // a generic "error saving".
    it('shows what the backend rejected instead of a generic failure', async () => {
        const wrapper = await mountDialog()
        const rejection = new Error('bad request')
        rejection.response = {
            status: 400,
            data: {
                error: "The identity 'jsmith' at 'ACME SAML2' is already linked to 'jdoe'."
            }
        }
        createNewUser.mockRejectedValueOnce(rejection)

        wrapper.vm.localItem.username = 'jsmith'
        wrapper.vm.localItem.name = 'John Smith'
        const saved = await wrapper.vm.persist()
        await wrapper.vm.$nextTick()

        expect(saved).toBe(false)
        expect(wrapper.vm.showError).toBe(true)
        // the alert renders errorMessage, falling back to the generic text only when empty
        expect(wrapper.vm.errorMessage).toContain("already linked to 'jdoe'")
    })

    it('shows the stored requirement when editing a user, and keeps it on save', async () => {
        const wrapper = await mountDialog({
            id: 7,
            username: 'jsmith',
            name: 'John Smith',
            require_mfa: true,
            organizations: [],
            roles: [],
            permissions: []
        })

        expect(wrapper.vm.localItem.require_mfa).toBe(true)

        await wrapper.vm.persist()

        expect(updateUser).toHaveBeenCalledWith(expect.objectContaining({ id: 7, require_mfa: true }))
    })
})
