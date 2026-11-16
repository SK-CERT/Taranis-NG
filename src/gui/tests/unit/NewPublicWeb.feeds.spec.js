import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { mountWithPlugins } from '../helpers/mount-helpers'
import NewPublicWeb from '@/components/config/public-web/NewPublicWeb.vue'
import { updatePublicWeb } from '@/api/config'

// A web's feeds: how many reports a feed page carries, and the WebSub hub its node notifies.

vi.mock('@/api/config', () => ({
    createNewPublicWeb: vi.fn().mockResolvedValue({ data: { id: 3 } }),
    updatePublicWeb: vi.fn().mockResolvedValue({ data: {} }),
    getPublicWebImage: vi.fn().mockRejectedValue(new Error('no image')),
    uploadPublicWebImage: vi.fn(),
    deletePublicWebImage: vi.fn(),
    getAllOrganizations: vi.fn().mockResolvedValue({ data: { items: [] } }),
    testPublicWebEmail: vi.fn()
}))

vi.mock('@/composables/useAuth', () => ({
    useAuth: () => ({ checkPermission: () => true })
}))

const VDialogStub = { name: 'VDialog', template: '<div><slot /></div>' }
const mounted = []

async function openWeb(config = {}) {
    const wrapper = mountWithPlugins(NewPublicWeb, {
        props: {
            nodeId: 1,
            editItem: { id: 3, name: 'Cyberfeed', hostname: 'feed.example', config: { languages: ['en'], default_language: 'en', ...config } }
        },
        global: { stubs: { VDialog: VDialogStub } }
    })
    mounted.push(wrapper)
    await flushPromises()
    return wrapper
}

const input = (wrapper, test) => wrapper.get(`[data-test="${test}"] input`)

describe('NewPublicWeb feeds', () => {
    beforeEach(() => vi.clearAllMocks())
    afterEach(() => {
        while (mounted.length) mounted.pop().unmount()
    })

    it('offers 50 reports a feed page and no hub for a web that has set neither', async () => {
        const wrapper = await openWeb()

        expect(input(wrapper, 'web-feed-page-size').element.value).toBe('50')
        expect(input(wrapper, 'web-websub-hub').element.value).toBe('')
    })

    it('accepts only a web address as the hub, or none', async () => {
        const wrapper = await openWeb()

        expect(wrapper.vm.websubHubRule('')).toBe(true)
        expect(wrapper.vm.websubHubRule('https://pubsubhubbub.appspot.com/')).toBe(true)
        expect(wrapper.vm.websubHubRule('ftp://hub.example/')).toBe('Enter an http:// or https:// address')
    })

    it('saves the page size and the hub with the web', async () => {
        const wrapper = await openWeb({ feed_page_size: 20 })

        await input(wrapper, 'web-websub-hub').setValue('https://hub.example/')
        await wrapper.vm.persist()

        expect(updatePublicWeb).toHaveBeenCalledWith(
            1,
            expect.objectContaining({ config: expect.objectContaining({ feed_page_size: 20, websub_hub: 'https://hub.example/' }) })
        )
    })
})
