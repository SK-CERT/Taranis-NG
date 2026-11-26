import { describe, it, expect, vi, beforeEach } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { mountWithPlugins } from '../helpers/mount-helpers'
import NewDataProvider from '@/components/config/data-providers/NewDataProvider.vue'
import { updateDataProvider } from '@/api/config'

vi.mock('@/composables/useAuth', () => ({ useAuth: () => ({ checkPermission: () => true }) }))
vi.mock('@/api/config', () => ({
    createNewDataProvider: vi.fn().mockResolvedValue({}),
    updateDataProvider: vi.fn().mockResolvedValue({})
}))

const PROVIDER = {
    id: 4,
    name: 'VulnCheck',
    api_url: 'https://api.example.test',
    api_key: '',
    api_key_set: true,
    user_agent: '',
    type: 'CVE'
}

async function open() {
    const wrapper = mountWithPlugins(NewDataProvider, {
        props: { editItem: { ...PROVIDER } },
        global: { stubs: { VDialog: { template: '<div><slot /></div>' } } }
    })
    await flushPromises()
    wrapper.vm.formRef = { validate: () => Promise.resolve({ valid: true }), reset: () => {} }
    return wrapper
}

describe('Data provider API key', () => {
    beforeEach(() => vi.clearAllMocks())

    it('keeps the stored key when the field is left empty', async () => {
        const wrapper = await open()

        expect(await wrapper.vm.persist()).toBe(true)
        expect(updateDataProvider.mock.calls[0][0]).not.toHaveProperty('clear_api_key')
    })

    it('removes the stored key only when its remove button was pressed', async () => {
        const wrapper = await open()

        await wrapper.get('[data-test="stored-secret-toggle"]').trigger('click')
        wrapper.vm.formRef = { validate: () => Promise.resolve({ valid: true }), reset: () => {} }

        expect(await wrapper.vm.persist()).toBe(true)
        expect(updateDataProvider.mock.calls[0][0]).toMatchObject({ api_key: '', clear_api_key: true })
    })
})
