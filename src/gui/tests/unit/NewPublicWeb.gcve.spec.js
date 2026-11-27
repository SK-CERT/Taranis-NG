import { flushPromises } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mountWithPlugins } from '../helpers/mount-helpers'
import NewPublicWeb from '@/components/config/public-web/NewPublicWeb.vue'
import DialogToolbar from '@/components/common/dialogs/DialogToolbar.vue'
import { getAllOrganizations, updatePublicWeb } from '@/api/config'

vi.mock('@/api/config', () => ({
    createNewPublicWeb: vi.fn().mockResolvedValue({ data: { id: 9 } }),
    updatePublicWeb: vi.fn().mockResolvedValue({ data: {} }),
    getPublicWebImage: vi.fn().mockRejectedValue(new Error('none')),
    uploadPublicWebImage: vi.fn(),
    deletePublicWebImage: vi.fn(),
    getAllOrganizations: vi.fn().mockResolvedValue({ data: { items: [] } }),
    testPublicWebEmail: vi.fn()
}))

vi.mock('@/composables/useAuth', () => ({
    useAuth: () => ({ checkPermission: () => true })
}))

const VDialogStub = {
    name: 'VDialog',
    template: '<div><slot name="activator" :props="{}" /><slot /></div>'
}

const web = (config = {}, overrides = {}) => ({
    id: 5,
    name: 'Example web',
    hostname: 'feed.example.org',
    config: { gcve_organization_id: 3, security_contact: 'cert@example.org', ...config },
    ...overrides
})

const mounted = []

// The organizations: CERT is a GNA (65535), the other one is not.
const organizations = (gnaId = 65535) => [
    { id: 3, name: 'CERT', gna_id: gnaId },
    { id: 4, name: 'Partner', gna_id: null }
]

async function mountDialog(editItem, gnaId = 65535) {
    vi.mocked(getAllOrganizations).mockResolvedValue({ data: { items: organizations(gnaId) } })
    const wrapper = mountWithPlugins(NewPublicWeb, {
        props: { nodeId: 1, editItem },
        global: { stubs: { VDialog: VDialogStub, UnsavedChangesDialog: true } }
    })
    mounted.push(wrapper)
    await flushPromises()
    return wrapper
}

const urls = (wrapper) =>
    wrapper.findAll('[data-test="web-gcve-urls"] tr').map((row) => [row.findAll('td')[0].text(), row.findAll('td')[1].text()])

describe('NewPublicWeb GCVE publication', () => {
    beforeEach(() => {
        vi.clearAllMocks()
    })

    afterEach(() => {
        while (mounted.length) mounted.pop().unmount()
    })

    it("lists what to register at gcve.eu, the dump named after the organization's GNA number", async () => {
        const wrapper = await mountDialog(web())

        expect(urls(wrapper)).toEqual([
            ['Website gcve_url', 'https://feed.example.org/'],
            ['Publication API base gcve_pull_api', 'https://feed.example.org/'],
            ['Dump directory gcve_dump', 'https://feed.example.org/dumps/'],
            ['Publication endpoint', 'https://feed.example.org/api/gcve/publication'],
            ['Dump', 'https://feed.example.org/dumps/gna-65535.ndjson'],
            ['Conformance document', 'https://feed.example.org/api/gcve/conformance'],
            ['security.txt', 'https://feed.example.org/.well-known/security.txt']
        ])
    })

    it('copies an address', async () => {
        const writeText = vi.fn().mockResolvedValue(undefined)
        Object.defineProperty(navigator, 'clipboard', { value: { writeText }, configurable: true })
        const wrapper = await mountDialog(web())

        await wrapper.find('[data-test="web-gcve-copy-dump"]').trigger('click')
        await flushPromises()

        expect(writeText).toHaveBeenCalledWith('https://feed.example.org/dumps/gna-65535.ndjson')
    })

    it('serves no security.txt without a security contact', async () => {
        const wrapper = await mountDialog(web({ security_contact: '' }))

        expect(urls(wrapper).map(([label]) => label)).not.toContain('security.txt')
    })

    it('offers the organizations that are GNAs', async () => {
        const wrapper = await mountDialog(web())

        const items = wrapper.findComponent('[data-test="web-gcve-organization"]').props('items')
        expect(items.map((item) => [item.title, item.value])).toEqual([
            ['No organization', null],
            ['CERT (GNA 65535)', 3]
        ])
    })

    it('warns when the organization has no GNA number any more', async () => {
        const wrapper = await mountDialog(web(), null)

        expect(wrapper.find('[data-test="web-gcve-gna-unset"]').exists()).toBe(true)
        expect(wrapper.find('[data-test="web-gcve-urls"]').exists()).toBe(false)
    })

    it('asks for the hostname before it can list the addresses', async () => {
        const wrapper = await mountDialog(web({}, { hostname: '' }))

        expect(wrapper.find('[data-test="web-gcve-hostname-needed"]').exists()).toBe(true)
    })

    it('shows nothing of it on a web that does not publish GCVE records', async () => {
        const wrapper = await mountDialog(web({ gcve_organization_id: null }))

        expect(wrapper.find('[data-test="web-gcve-urls"]').exists()).toBe(false)
        expect(wrapper.find('[data-test="web-gcve-gna-unset"]').exists()).toBe(false)
    })

    it('starts a new web without GCVE records', async () => {
        const wrapper = await mountDialog(null)

        expect(wrapper.findComponent('[data-test="web-gcve-organization"]').props('modelValue')).toBeNull()
    })

    it('forgets the switch of a web from before the organizations', async () => {
        const sent = []
        vi.mocked(updatePublicWeb).mockImplementationOnce(async (_node, item) => {
            sent.push(JSON.parse(JSON.stringify(item)))
            return { data: {} }
        })
        const wrapper = await mountDialog(web({ gcve_enabled: true, gcve_organization_id: undefined }))

        wrapper.findComponent(DialogToolbar).vm.$emit('save')
        await flushPromises()

        expect(sent[0].config).not.toHaveProperty('gcve_enabled')
        expect(sent[0].config.gcve_organization_id).toBeNull()
    })

    it('refuses a security contact that is not an address RFC 9116 takes', async () => {
        const wrapper = await mountDialog(web({ security_contact: 'call us' }))

        wrapper.findComponent(DialogToolbar).vm.$emit('save')
        await flushPromises()

        expect(updatePublicWeb).not.toHaveBeenCalled()
        expect(wrapper.text()).toContain('Enter an e-mail address, or a mailto:, https: or tel: address.')
    })

    it('saves the organization and the security contact with the web', async () => {
        // What was sent, as it was then: closing the dialog resets the form behind it.
        const sent = []
        vi.mocked(updatePublicWeb).mockImplementationOnce(async (_node, item) => {
            sent.push(JSON.parse(JSON.stringify(item)))
            return { data: {} }
        })
        const wrapper = await mountDialog(web({ security_contact: 'mailto:cert@example.org' }))

        wrapper.findComponent(DialogToolbar).vm.$emit('save')
        await flushPromises()

        expect(sent[0].config).toMatchObject({
            gcve_organization_id: 3,
            security_contact: 'mailto:cert@example.org'
        })
    })
})
