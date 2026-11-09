import { describe, it, expect, beforeEach, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { mountWithPlugins } from '../helpers/mount-helpers'
import ApiKeysPanel from '@/components/common/api-keys/ApiKeysPanel.vue'
import ApiKeysTable from '@/components/common/api-keys/ApiKeysTable.vue'
import ApiKeyRevealDialog from '@/components/common/api-keys/ApiKeyRevealDialog.vue'
import { deleteApiKey, getAllApiKeys, updateApiKey } from '@/api/config'
import { deleteMyApiKey, getMyApiKeys, updateMyApiKey } from '@/api/user'

vi.mock('@/api/config', () => ({
    getAllApiKeys: vi.fn(),
    updateApiKey: vi.fn(),
    deleteApiKey: vi.fn(),
    createApiKey: vi.fn(),
    getApiKeyPermissions: vi.fn()
}))

vi.mock('@/api/user', () => ({
    getMyApiKeys: vi.fn(),
    updateMyApiKey: vi.fn(),
    deleteMyApiKey: vi.fn(),
    createMyApiKey: vi.fn()
}))

const granted = new Set()
vi.mock('@/composables/useAuth', () => ({
    useAuth: () => ({ checkPermission: (permission) => granted.has(permission) })
}))

const DAY = 24 * 60 * 60 * 1000
const key = (fields) => ({
    id: 1,
    name: 'SOAR sync',
    description: '',
    key_prefix: 'tnk_abcdefgh',
    user: { id: 3, username: 'soar', name: 'SOAR' },
    user_id: 3,
    created_at: '2026-11-01T10:00:00+00:00',
    created_by: 'admin',
    expires_at: null,
    expired: false,
    enabled: true,
    restricted: false,
    permissions: [],
    allowed_ips: [],
    last_used_at: null,
    last_used_ip: null,
    ...fields
})
const KEYS = [
    key({ id: 1 }),
    key({ id: 2, name: 'Paused', enabled: false, user: { id: 4, username: 'ci', name: 'CI' }, user_id: 4 }),
    key({ id: 3, name: 'Old', expired: true, expires_at: new Date(Date.now() - DAY).toISOString() }),
    key({
        id: 4,
        name: 'Soon',
        expires_at: new Date(Date.now() + 3 * DAY).toISOString(),
        restricted: true,
        permissions: [{ id: 'ASSESS_ACCESS' }]
    })
]
const LIST = {
    total_count: KEYS.length,
    items: KEYS,
    policy: { require_expiry: true, max_days: 30, require_allowlist: false, site_allowlist_active: true },
    client_ip: '198.51.100.7',
    client_ip_public: false,
    owners: [
        { id: 3, username: 'soar', name: 'SOAR' },
        { id: 4, username: 'ci', name: 'CI' }
    ],
    available_permissions: [{ id: 'ASSESS_ACCESS', name: 'Assess access' }]
}

async function mountPanel(mode) {
    const wrapper = mountWithPlugins(ApiKeysPanel, { props: { mode } })
    await flushPromises()
    return wrapper
}

describe('ApiKeysPanel', () => {
    beforeEach(() => {
        vi.clearAllMocks()
        granted.clear()
        // A fresh copy per load: the panel changes its rows in place.
        getAllApiKeys.mockImplementation(async () => ({ data: JSON.parse(JSON.stringify(LIST)) }))
        getMyApiKeys.mockImplementation(async () => ({ data: { ...JSON.parse(JSON.stringify(LIST)), owners: undefined } }))
        updateApiKey.mockResolvedValue({ data: {} })
        updateMyApiKey.mockResolvedValue({ data: {} })
        deleteApiKey.mockResolvedValue({ data: {} })
        deleteMyApiKey.mockResolvedValue({ data: {} })
    })

    it('lists every user’s keys for an admin, with the owner column and only the granted actions', async () => {
        granted.add('CONFIG_API_KEY_UPDATE')
        const wrapper = await mountPanel('admin')
        const table = wrapper.findComponent(ApiKeysTable)

        expect(getAllApiKeys).toHaveBeenCalled()
        expect(table.props('items')).toHaveLength(4)
        expect(table.props('showOwner')).toBe(true)
        expect(table.props('canUpdate')).toBe(true)
        expect(table.props('canDelete')).toBe(false)
        expect(wrapper.vm.canCreate).toBe(false)
        expect(wrapper.vm.policy.max_days).toBe(30)
        expect(wrapper.vm.clientIp).toBe('198.51.100.7')
        expect(wrapper.vm.clientIpPublic).toBe(false)
    })

    it('filters by owner, status and search', async () => {
        const wrapper = await mountPanel('admin')

        wrapper.vm.ownerFilter = 4
        await wrapper.vm.$nextTick()
        expect(wrapper.vm.visibleItems.map((item) => item.name)).toEqual(['Paused'])

        wrapper.vm.ownerFilter = null
        wrapper.vm.statusFilter = 'expired'
        await wrapper.vm.$nextTick()
        expect(wrapper.vm.visibleItems.map((item) => item.name)).toEqual(['Old'])

        wrapper.vm.statusFilter = null
        wrapper.vm.search = null // the clear button
        await wrapper.vm.$nextTick()
        expect(wrapper.vm.visibleItems).toHaveLength(4)
        wrapper.vm.search = 'SOO'
        await wrapper.vm.$nextTick()
        expect(wrapper.vm.visibleItems.map((item) => item.name)).toEqual(['Soon'])
    })

    it('manages the signed-in user’s own keys without the owner column', async () => {
        const wrapper = await mountPanel('self')
        const table = wrapper.findComponent(ApiKeysTable)

        expect(getMyApiKeys).toHaveBeenCalled()
        expect(getAllApiKeys).not.toHaveBeenCalled()
        expect(table.props('showOwner')).toBe(false)
        expect(wrapper.vm.canCreate && wrapper.vm.canUpdate && wrapper.vm.canDelete).toBe(true)
        expect(wrapper.vm.availablePermissions).toEqual(LIST.available_permissions)
    })

    /** Record every value `loading` takes, so a flash of the skeleton rows cannot go unseen. */
    const watchLoading = (wrapper) => {
        const seen = []
        wrapper.vm.$watch('loading', (value) => seen.push(value), { flush: 'sync' })
        return seen
    }

    it('pauses and resumes a key at once, through the endpoint of its mode, without the loading animation', async () => {
        const wrapper = await mountPanel('self')
        const loadingSeen = watchLoading(wrapper)
        let finishSave
        updateMyApiKey.mockImplementationOnce(() => new Promise((resolve) => (finishSave = resolve)))

        wrapper.findComponent(ApiKeysTable).vm.$emit('toggle', KEYS[0])
        await wrapper.vm.$nextTick()
        // flipped before the server answers, its switch waiting meanwhile
        expect(wrapper.vm.items[0].enabled).toBe(false)
        expect(wrapper.findComponent(ApiKeysTable).props('busyId')).toBe(1)
        finishSave({ data: {} })
        await flushPromises()
        expect(updateMyApiKey).toHaveBeenCalledWith(1, { enabled: false })
        expect(wrapper.findComponent(ApiKeysTable).props('busyId')).toBeNull()

        wrapper.findComponent(ApiKeysTable).vm.$emit('toggle', KEYS[1])
        await flushPromises()
        expect(updateMyApiKey).toHaveBeenCalledWith(2, { enabled: true })
        expect(getMyApiKeys).toHaveBeenCalledTimes(3) // re-read quietly after each save
        expect(loadingSeen).toEqual([])
        expect(wrapper.findComponent(ApiKeysTable).props('loading')).toBe(false)
    })

    it('puts a switch back when the save fails', async () => {
        const wrapper = await mountPanel('self')
        updateMyApiKey.mockRejectedValueOnce(new Error('down'))

        wrapper.findComponent(ApiKeysTable).vm.$emit('toggle', KEYS[0])
        await flushPromises()

        expect(wrapper.vm.items[0].enabled).toBe(true)
    })

    it('deletes a key only after confirmation, and drops its row without the loading animation', async () => {
        granted.add('CONFIG_API_KEY_DELETE')
        const wrapper = await mountPanel('admin')
        const loadingSeen = watchLoading(wrapper)

        wrapper.findComponent(ApiKeysTable).vm.$emit('delete', KEYS[2])
        await wrapper.vm.$nextTick()
        expect(wrapper.vm.deleteOpen).toBe(true)
        expect(deleteApiKey).not.toHaveBeenCalled()

        getAllApiKeys.mockImplementationOnce(() => new Promise(() => {})) // the re-read never lands
        wrapper.vm.confirmDelete()
        await flushPromises()
        expect(deleteApiKey).toHaveBeenCalledWith(3)
        expect(wrapper.vm.items.map((item) => item.id)).toEqual([1, 2, 4])
        expect(loadingSeen).toEqual([])
    })

    it('shows an edited key as saved, without the loading animation', async () => {
        const wrapper = await mountPanel('admin')
        const loadingSeen = watchLoading(wrapper)
        getAllApiKeys.mockImplementationOnce(() => new Promise(() => {}))

        wrapper.vm.onSaved({ item: key({ id: 2, name: 'Renamed', enabled: false, user_id: 4 }) })
        await flushPromises()

        expect(wrapper.vm.items.find((item) => item.id === 2).name).toBe('Renamed')
        expect(loadingSeen).toEqual([])
    })

    it('reveals a new key once and forgets it when the dialog closes', async () => {
        const wrapper = await mountPanel('self')

        wrapper.vm.onSaved({ item: key({ id: 9, name: 'New one' }), key: 'tnk_secret' })
        await wrapper.vm.$nextTick()
        const reveal = wrapper.findComponent(ApiKeyRevealDialog)
        expect(reveal.props()).toMatchObject({ modelValue: true, apiKey: 'tnk_secret', name: 'New one' })

        reveal.vm.$emit('update:modelValue', false)
        await wrapper.vm.$nextTick()
        expect(wrapper.vm.revealedKey).toBe('')
    })
})
