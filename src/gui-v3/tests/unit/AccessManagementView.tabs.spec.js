import { describe, it, expect, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { mountWithPlugins } from '../helpers/mount-helpers'
import AccessManagementView from '@/views/admin/AccessManagementView.vue'

vi.mock('@/composables/useAuth', () => ({
    useAuth: () => ({ checkPermission: () => true })
}))

const tabStubs = {
    UsersTab: { template: '<div data-test="users-content">Users content</div>' },
    RolesTab: { template: '<div data-test="roles-content">Roles content</div>' },
    ACLTab: { template: '<div data-test="acls-content">ACL content</div>' },
    OrganizationsTab: { template: '<div data-test="organizations-content">Organizations content</div>' },
    AuthProvidersTab: { template: '<div data-test="login-methods-content">Login Methods content</div>' },
    SecurityTab: { template: '<div data-test="security-content">Two-factor authentication Passkeys</div>' }
}

describe('AccessManagementView tab panels', () => {
    it('unmounts Security when switching back to Login Methods', async () => {
        const router = createRouter({
            history: createMemoryHistory(),
            routes: [{ path: '/', component: AccessManagementView }]
        })
        await router.push({ path: '/', query: { tab: 'security' } })
        await router.isReady()

        const wrapper = mountWithPlugins(AccessManagementView, {
            global: { plugins: [router], stubs: tabStubs }
        })
        await flushPromises()

        expect(wrapper.find('[data-test="security-content"]').exists()).toBe(true)
        expect(wrapper.find('[data-test="login-methods-content"]').exists()).toBe(false)

        const loginMethodsTab = wrapper.findAllComponents({ name: 'VTab' }).find((tab) => tab.props('value') === 'login-methods')
        expect(loginMethodsTab).toBeDefined()
        await loginMethodsTab.trigger('click')
        await flushPromises()

        expect(wrapper.vm.activeTab).toBe('login-methods')
        expect(wrapper.find('[data-test="security-content"]').exists()).toBe(false)
        expect(wrapper.text()).not.toContain('Two-factor authentication')
        expect(wrapper.text()).not.toContain('Passkeys')
        expect(wrapper.find('[data-test="login-methods-content"]').exists()).toBe(true)
    })
})
