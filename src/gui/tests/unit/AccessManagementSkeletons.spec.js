import { describe, it, expect, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { mountWithPlugins } from '../helpers/mount-helpers'
import UsersTab from '@/components/config/access-management/UsersTab.vue'
import RolesTab from '@/components/config/access-management/RolesTab.vue'
import ACLTab from '@/components/config/access-management/ACLTab.vue'
import OrganizationsTab from '@/components/config/access-management/OrganizationsTab.vue'
import AuthProvidersTab from '@/components/config/access-management/AuthProvidersTab.vue'

const store = {
    users: { items: [] },
    roles: { items: [] },
    acls: { items: [] },
    organizations: { items: [] },
    authProviders: { items: [] },
    loadUsers: vi.fn(),
    loadRoles: vi.fn(),
    loadACLEntries: vi.fn(),
    loadOrganizations: vi.fn(),
    loadAuthProviders: vi.fn()
}

vi.mock('@/stores/config', () => ({ useConfigStore: () => store }))
vi.mock('@/composables/useAuth', () => ({ useAuth: () => ({ checkPermission: () => true }) }))

const stubs = {
    NewUser: true,
    NewRole: true,
    NewACL: true,
    NewOrganization: true,
    NewAuthProvider: true,
    ConfirmationDialog: true,
    SearchField: true
}

describe.each([
    ['Users', UsersTab, 'loadUsers'],
    ['Roles', RolesTab, 'loadRoles'],
    ['ACL', ACLTab, 'loadACLEntries'],
    ['Organizations', OrganizationsTab, 'loadOrganizations'],
    ['Login Methods', AuthProvidersTab, 'loadAuthProviders']
])('%s table skeleton', (_name, component, action) => {
    it.each(['success', 'failure'])('clears loading rows after request %s', async (outcome) => {
        let resolveRequest
        let rejectRequest
        store[action].mockImplementationOnce(
            () =>
                new Promise((resolve, reject) => {
                    resolveRequest = resolve
                    rejectRequest = reject
                })
        )
        const log = vi.spyOn(console, 'error').mockImplementation(() => {})
        const wrapper = mountWithPlugins(component, { global: { stubs } })
        try {
            await flushPromises()
            const headers = wrapper.findAll('thead th')
            const rows = wrapper.findAll('tbody .table-skeleton-row')
            expect(headers.length).toBeGreaterThan(0)
            expect(rows).toHaveLength(5)
            expect(rows[0].findAll('td')).toHaveLength(headers.length)
            const expectedChips = action === 'loadUsers' ? 3 : action === 'loadAuthProviders' ? 1 : 0
            expect(rows[0].findAll('.v-skeleton-loader__chip')).toHaveLength(expectedChips)
            expect(rows[0].findAll('.v-skeleton-loader__actions .v-skeleton-loader__button')).toHaveLength(action === 'loadUsers' ? 3 : 2)
            expect(rows[0].find('td:last-child').classes()).toContain('v-data-table-column--align-end')
            expect(wrapper.text()).not.toContain('No data available')

            if (outcome === 'success') resolveRequest()
            else rejectRequest(new Error('Request failed'))
            await flushPromises()
            expect(wrapper.find('.table-skeleton-row').exists()).toBe(false)
            expect(wrapper.findAll('thead th')).toHaveLength(headers.length)
        } finally {
            wrapper.unmount()
            log.mockRestore()
        }
    })
})
