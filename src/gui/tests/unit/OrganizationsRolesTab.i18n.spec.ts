import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { Component } from 'vue'
import { useConfigStore } from '@/stores/config'
import { mountWithPlugins } from '../helpers/mount-helpers'
import OrganizationsTab from '@/components/config/access-management/OrganizationsTab.vue'
import RolesTab from '@/components/config/access-management/RolesTab.vue'

vi.mock('@/api/config', async (importOriginal) => {
    const original = await importOriginal<typeof import('@/api/config')>()
    return {
        ...original,
        getAllOrganizations: vi.fn().mockResolvedValue({ data: { total_count: 0, items: [] } }),
        getAllRoles: vi.fn().mockResolvedValue({ data: { total_count: 0, items: [] } }),
        deleteOrganization: vi.fn().mockResolvedValue({ data: {} }),
        deleteRole: vi.fn().mockResolvedValue({ data: {} })
    }
})

vi.mock('@/composables/useAuth', () => ({
    useAuth: () => ({ checkPermission: () => true })
}))

type TabCase = {
    component: Component
    list: 'organizations' | 'roles'
    name: string
}

const tabCases: TabCase[] = [
    { component: OrganizationsTab, list: 'organizations', name: 'CERT العربية' },
    { component: RolesTab, list: 'roles', name: 'Analyst العربية' }
]

const ConfirmationDialogStub = {
    name: 'ConfirmationDialog',
    props: ['message'],
    template: '<div data-test="confirmation-dialog" />'
}

describe.each(tabCases)('$list tab locale-safe rendering', ({ component, list, name }) => {
    beforeEach(() => {
        vi.clearAllMocks()
    })

    it('isolates the displayed name and the plain-text confirmation message', async () => {
        const wrapper = mountWithPlugins(component, {
            global: {
                stubs: {
                    NewOrganization: true,
                    NewRole: true,
                    SearchField: true,
                    ConfirmationDialog: ConfirmationDialogStub
                }
            }
        })
        const store = useConfigStore()
        await new Promise((resolve) => setTimeout(resolve, 0))
        store[list] = {
            total_count: 1,
            items: [{ id: 1, name, description: 'Description' }]
        }
        await wrapper.vm.$nextTick()

        expect(wrapper.find('bdi[dir="auto"]').text()).toBe(name)

        wrapper.vm.handleDelete(store[list].items[0])
        await wrapper.vm.$nextTick()
        expect(wrapper.findComponent(ConfirmationDialogStub).props('message')).toBe(`\u2068${name}\u2069`)
    })

    it('uses logical toolbar alignment and action spacing', async () => {
        const wrapper = mountWithPlugins(component, {
            global: {
                stubs: {
                    NewOrganization: true,
                    NewRole: true,
                    SearchField: true,
                    ConfirmationDialog: ConfirmationDialogStub
                }
            }
        })
        const store = useConfigStore()
        await new Promise((resolve) => setTimeout(resolve, 0))
        store[list] = {
            total_count: 1,
            items: [{ id: 1, name, description: 'Description' }]
        }
        await wrapper.vm.$nextTick()

        expect(wrapper.find('.text-end').exists()).toBe(true)
        expect(wrapper.find('.text-right').exists()).toBe(false)
        expect(wrapper.find('.me-1').exists()).toBe(true)
        expect(wrapper.find('.mr-1').exists()).toBe(false)
    })
})
