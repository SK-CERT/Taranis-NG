import { describe, it, expect, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { mountWithPlugins } from '../helpers/mount-helpers'
import AssetGroupDialog from '@/components/config/assets/AssetGroupDialog.vue'
import { getOrganizationMembers } from '@/api/config'

vi.mock('@/api/config', () => ({
    getOrganizationMembers: vi.fn()
}))

vi.mock('@/api/assets', () => ({
    createNewAssetGroup: vi.fn(),
    updateAssetGroup: vi.fn(),
    getAllNotificationTemplates: vi.fn(() => Promise.resolve({ data: { items: [] } }))
}))

describe('Asset group allowed users', () => {
    it('offers every member of the organization and keeps members it does not list', async () => {
        getOrganizationMembers.mockResolvedValue({
            data: {
                items: [
                    { id: 1, username: 'portal-user', name: 'Portal User' },
                    { id: 2, username: 'analyst', name: 'Analyst With A Role' }
                ]
            }
        })
        const group = { id: 'g1', name: 'Servers', description: '', users: [{ id: 9, username: 'elsewhere', name: 'Added Earlier' }] }
        const wrapper = mountWithPlugins(AssetGroupDialog, {
            props: { modelValue: false, group },
            global: { stubs: { VDialog: { template: '<div><slot /></div>' } } }
        })

        await wrapper.setProps({ modelValue: true })
        await flushPromises()

        expect(getOrganizationMembers).toHaveBeenCalledWith({ search: '' })
        expect(wrapper.vm.users.map((user) => user.id)).toEqual([1, 2, 9])
        expect(wrapper.vm.selectedUsers).toEqual([9])
    })
})
