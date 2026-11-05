import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { Component } from 'vue'
import { flushPromises } from '@vue/test-utils'
import { mountWithPlugins } from '../helpers/mount-helpers'
import NewRemoteAccess from '@/components/config/remote/NewRemoteAccess.vue'
import NewRemoteNode from '@/components/config/remote/NewRemoteNode.vue'

const { submitted, connected } = vi.hoisted(() => ({ submitted: vi.fn(), connected: vi.fn() }))
vi.mock('@/composables/useAuth', () => ({ useAuth: () => ({ checkPermission: () => true }) }))
vi.mock('@/api/config', () => ({
    createNewRemoteAccess: vi.fn(async (payload) => submitted('create-access', { ...payload })),
    updateRemoteAccess: vi.fn(async (payload) => submitted('update-access', { ...payload })),
    createNewRemoteNode: vi.fn(async (payload) => submitted('create-node', { ...payload })),
    updateRemoteNode: vi.fn(async (payload) => submitted('update-node', { ...payload })),
    connectRemoteNode: connected,
    getAllOSINTSources: vi.fn().mockResolvedValue({ data: { items: [] } }),
    getAllReportItemTypes: vi.fn().mockResolvedValue({ data: { items: [] } }),
    getAllOSINTSourceGroups: vi.fn().mockResolvedValue({ data: { items: [] } })
}))

const mountDialog = (component: Component, editItem: Record<string, unknown>) =>
    mountWithPlugins(component, {
        props: { editItem },
        global: {
            stubs: {
                VDialog: { template: '<div><slot /></div>' },
                DialogToolbar: { name: 'DialogToolbar', emits: ['save'], template: '<div />' },
                UnsavedChangesDialog: true,
                AddNewButton: true
            }
        }
    })

const item = (overrides: Record<string, unknown> = {}) => ({
    id: null,
    name: 'Remote peer',
    remote_url: 'https://peer.example',
    api_key: 'key',
    ...overrides
})

const cases = [
    { name: 'access', component: NewRemoteAccess, label: 'Legacy response timezone' },
    { name: 'node', component: NewRemoteNode, label: 'Legacy provider timezone' }
]

beforeEach(() => vi.clearAllMocks())

describe.each(cases)('remote $name legacy timestamps', ({ name, component, label }) => {
    it('submits the selected IANA timezone', async () => {
        const wrapper = mountDialog(component, item())
        await flushPromises()
        const field = wrapper.findAllComponents({ name: 'VTextField' }).find((field) => field.props('label') === label)!
        expect(field.props('modelValue')).toBe('')
        expect(field.props('hint')).toContain('Version 2 uses UTC automatically')
        await field.vm.$emit('update:modelValue', ' Europe/Bratislava ')
        await wrapper.findComponent({ name: 'DialogToolbar' }).vm.$emit('save')
        await flushPromises()

        expect(submitted).toHaveBeenCalledWith(`create-${name}`, expect.objectContaining({ legacy_timezone: 'Europe/Bratislava' }))
        wrapper.unmount()
    })

    it('leaves blank new configurations to the installation default', async () => {
        const wrapper = mountDialog(component, item())
        await flushPromises()
        await wrapper.findComponent({ name: 'DialogToolbar' }).vm.$emit('save')
        await flushPromises()

        expect(submitted).toHaveBeenCalledOnce()
        expect(submitted.mock.calls[0]![0]).toBe(`create-${name}`)
        expect(submitted.mock.calls[0]![1]).not.toHaveProperty('legacy_timezone')
        wrapper.unmount()
    })

    it('preserves the migrated timezone when editing an existing configuration', async () => {
        const wrapper = mountDialog(component, item({ id: 42, legacy_timezone: 'America/New_York' }))
        await flushPromises()
        const field = wrapper.findAllComponents({ name: 'VTextField' }).find((field) => field.props('label') === label)!
        expect(field.props('modelValue')).toBe('America/New_York')
        await wrapper.findComponent({ name: 'DialogToolbar' }).vm.$emit('save')
        await flushPromises()

        expect(submitted).toHaveBeenCalledWith(`update-${name}`, expect.objectContaining({ id: 42, legacy_timezone: 'America/New_York' }))
        wrapper.unmount()
    })
})

it('saves the chosen provider timezone before connecting', async () => {
    const wrapper = mountDialog(NewRemoteNode, item({ id: 42, legacy_timezone: 'Europe/Bratislava', enabled: true }))
    await flushPromises()
    await wrapper
        .findAllComponents({ name: 'VBtn' })
        .find((button) => button.text().includes('Connect to remote node'))!
        .trigger('click')
    await flushPromises()

    expect(submitted).toHaveBeenCalledWith('update-node', expect.objectContaining({ legacy_timezone: 'Europe/Bratislava' }))
    expect(connected).toHaveBeenCalledOnce()
    expect(submitted.mock.invocationCallOrder[0]).toBeLessThan(connected.mock.invocationCallOrder[0]!)
    wrapper.unmount()
})
