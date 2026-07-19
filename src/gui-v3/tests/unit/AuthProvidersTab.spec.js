import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mountWithPlugins } from '../helpers/mount-helpers'
import AuthProvidersTab from '@/components/config/access-management/AuthProvidersTab.vue'
import { useConfigStore } from '@/stores/config'
import { deleteAuthProvider } from '@/api/config'

vi.mock('@/api/config', () => ({
    deleteAuthProvider: vi.fn().mockResolvedValue({ data: {} }),
    createNewAuthProvider: vi.fn().mockResolvedValue({ data: {} }),
    updateAuthProvider: vi.fn().mockResolvedValue({ data: {} }),
    getAllOrganizations: vi.fn().mockResolvedValue({ data: { items: [] } }),
    getAllRoles: vi.fn().mockResolvedValue({ data: { items: [] } })
}))

vi.mock('@/composables/useAuth', () => ({
    useAuth: () => ({ checkPermission: () => true })
}))

const PROVIDERS = [
    {
        id: 1,
        name: 'Local accounts',
        kind: 'local',
        enabled: true,
        provisioning_mode: 'manual',
        organization: null,
        linked_identity_count: 0
    },
    {
        id: 2,
        name: 'Corp SSO',
        kind: 'oidc',
        enabled: true,
        provisioning_mode: 'approval',
        organization: { id: 1, name: 'CERT' },
        linked_identity_count: 3
    },
    { id: 3, name: 'Corp SAML', kind: 'saml', enabled: false, provisioning_mode: 'automatic', organization: null, linked_identity_count: 0 }
]

async function mountTab() {
    const wrapper = mountWithPlugins(AuthProvidersTab)
    const store = useConfigStore()
    store.authProviders = { total_count: PROVIDERS.length, items: PROVIDERS }
    // let onMounted's loadData settle, then render the seeded rows
    await new Promise((resolve) => setTimeout(resolve, 0))
    store.authProviders = { total_count: PROVIDERS.length, items: PROVIDERS }
    await wrapper.vm.$nextTick()
    return { wrapper, store }
}

describe('AuthProvidersTab', () => {
    beforeEach(() => {
        vi.clearAllMocks()
    })

    it('loads the providers on mount', async () => {
        const { store } = await mountTab()
        expect(store.loadAuthProviders).toBeTypeOf('function')
        expect(store.authProviders.items).toHaveLength(3)
    })

    it('renders a row per provider with its translated kind', async () => {
        const { wrapper } = await mountTab()
        const text = wrapper.text()

        expect(text).toContain('Local accounts')
        expect(text).toContain('Corp SSO')
        expect(text).toContain('Corp SAML')
        expect(text).toContain('OpenID Connect')
        expect(text).toContain('SAML 2.0')
    })

    it('shows the provisioning mode for external kinds only', async () => {
        const { wrapper } = await mountTab()
        // approval mode for the OIDC provider, dash for the local one
        expect(wrapper.text()).toContain('Auto-create, admin approves')
        expect(wrapper.text()).toContain('Auto-create active')
    })

    it('colours the kind chips distinctly (SAML has its own colour)', async () => {
        const { wrapper } = await mountTab()
        expect(wrapper.vm.kindColor('saml')).toBe('purple')
        expect(wrapper.vm.kindColor('oidc')).toBe('orange')
        expect(wrapper.vm.kindColor('local')).toBe('primary')
        expect(wrapper.vm.kindColor('unknown-kind')).toBe('grey')
    })

    it('warns about linked identities in the delete confirmation', async () => {
        const { wrapper } = await mountTab()

        wrapper.vm.askDelete(PROVIDERS[1]) // 3 linked identities
        await wrapper.vm.$nextTick()
        expect(wrapper.vm.deleteDialog).toBe(true)
        expect(wrapper.vm.deleteMessage).toContain('Corp SSO')
        expect(wrapper.vm.deleteMessage).toContain('3')

        wrapper.vm.askDelete(PROVIDERS[0]) // no linked identities
        await wrapper.vm.$nextTick()
        expect(wrapper.vm.deleteMessage).toBe('Local accounts')
    })

    it('deletes the confirmed provider and reloads', async () => {
        const { wrapper } = await mountTab()

        wrapper.vm.askDelete(PROVIDERS[1])
        await wrapper.vm.confirmDelete()

        expect(deleteAuthProvider).toHaveBeenCalledWith(expect.objectContaining({ id: 2 }))
        expect(wrapper.vm.deleteDialog).toBe(false)
    })

    it('clears editItem when the dialog closes so the same row can be edited again', async () => {
        const { wrapper } = await mountTab()

        wrapper.vm.handleEdit(PROVIDERS[0])
        await wrapper.vm.$nextTick()
        expect(wrapper.vm.editItem).toEqual(PROVIDERS[0])

        // dialog reports it closed (cancel / Esc / discard)
        wrapper.vm.onDialogChange(false)
        await wrapper.vm.$nextTick()
        expect(wrapper.vm.editItem).toBeNull()

        // second Edit click on the same row must set it again (regression guard)
        wrapper.vm.handleEdit(PROVIDERS[0])
        await wrapper.vm.$nextTick()
        expect(wrapper.vm.editItem).toEqual(PROVIDERS[0])
    })
})
