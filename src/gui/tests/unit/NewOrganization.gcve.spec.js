import { flushPromises } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mountWithPlugins } from '../helpers/mount-helpers'
import NewOrganization from '@/components/config/access-management/NewOrganization.vue'
import DialogToolbar from '@/components/common/dialogs/DialogToolbar.vue'
import { createNewOrganization, updateOrganization } from '@/api/config'

// An existing organization also has its GCVE and CVE publishing, in a tab of its own, saved with it.

vi.mock('@/api/config', () => ({
    createNewOrganization: vi.fn().mockResolvedValue({}),
    updateOrganization: vi.fn().mockResolvedValue({})
}))

vi.mock('@/composables/useAuth', () => ({
    useAuth: () => ({ checkPermission: () => true })
}))

vi.mock('@/composables/useSpellcheck', () => ({
    useSpellcheck: () => false
}))

const gcve = { dirty: false, saved: true, calls: 0 }

// The GCVE & CVE tab itself is OrganizationGcve's (see OrganizationGcve.spec.js).
const OrganizationGcveStub = {
    name: 'OrganizationGcve',
    props: ['organizationId', 'canUpdate'],
    template: '<div data-test="organization-gcve-stub">{{ organizationId }}</div>',
    setup(_props, { expose }) {
        expose({
            get dirty() {
                return gcve.dirty
            },
            save: async () => {
                gcve.calls += 1
                return gcve.saved
            }
        })
    }
}

const VDialogStub = {
    name: 'VDialog',
    template: '<div><slot name="activator" :props="{}" /><slot /></div>'
}

const ORGANIZATION = { id: 3, name: 'CERT', description: '', require_mfa: false, address: { street: '', city: '', zip: '', country: '' } }

const mounted = []

async function mountDialog(editItem) {
    const wrapper = mountWithPlugins(NewOrganization, {
        props: { editItem },
        global: { stubs: { VDialog: VDialogStub, UnsavedChangesDialog: true, OrganizationGcve: OrganizationGcveStub } }
    })
    mounted.push(wrapper)
    await flushPromises()
    return wrapper
}

async function openGcveTab(wrapper) {
    await wrapper.get('[data-test="organization-tab-gcve"]').trigger('click')
    await flushPromises()
}

describe('NewOrganization GCVE & CVE', () => {
    beforeEach(() => {
        vi.clearAllMocks()
        Object.assign(gcve, { dirty: false, saved: true, calls: 0 })
    })

    afterEach(() => {
        while (mounted.length) mounted.pop().unmount()
    })

    it('has the tab only once the organization exists', async () => {
        const created = await mountDialog(null)
        expect(created.find('[data-test="organization-tabs"]').exists()).toBe(false)

        const existing = await mountDialog(ORGANIZATION)
        await openGcveTab(existing)
        expect(existing.get('[data-test="organization-gcve-stub"]').text()).toBe('3')
    })

    it('saves the GCVE and CVE settings after the organization, when they changed', async () => {
        const wrapper = await mountDialog(ORGANIZATION)
        await openGcveTab(wrapper)
        gcve.dirty = true

        wrapper.findComponent(DialogToolbar).vm.$emit('save')
        await flushPromises()

        expect(updateOrganization).toHaveBeenCalledTimes(1)
        expect(gcve.calls).toBe(1)
        expect(wrapper.emitted('saved')).toHaveLength(1)
    })

    it('leaves unchanged settings alone', async () => {
        const wrapper = await mountDialog(ORGANIZATION)
        await openGcveTab(wrapper)

        wrapper.findComponent(DialogToolbar).vm.$emit('save')
        await flushPromises()

        expect(updateOrganization).toHaveBeenCalledTimes(1)
        expect(gcve.calls).toBe(0)
        expect(createNewOrganization).not.toHaveBeenCalled()
    })

    it('stays open on the tab when the settings were refused', async () => {
        const wrapper = await mountDialog(ORGANIZATION)
        await openGcveTab(wrapper)
        gcve.dirty = true
        gcve.saved = false

        wrapper.findComponent(DialogToolbar).vm.$emit('save')
        await flushPromises()

        expect(gcve.calls).toBe(1)
        expect(wrapper.vm.activeTab).toBe('gcve')
        expect(wrapper.vm.dialog).toBe(true)
    })
})
