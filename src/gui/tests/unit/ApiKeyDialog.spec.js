import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mountWithPlugins } from '../helpers/mount-helpers'
import ApiKeyDialog from '@/components/common/api-keys/ApiKeyDialog.vue'
import { createApiKey, getApiKeyPermissions, updateApiKey } from '@/api/config'
import { createMyApiKey, updateMyApiKey } from '@/api/user'
import { dateInDays } from '@/components/common/api-keys/apiKeys'

vi.mock('@/api/config', () => ({
    createApiKey: vi.fn(),
    updateApiKey: vi.fn(),
    getApiKeyPermissions: vi.fn()
}))

vi.mock('@/api/user', () => ({
    createMyApiKey: vi.fn(),
    updateMyApiKey: vi.fn()
}))

const DAY = 24 * 60 * 60 * 1000
const OPEN_POLICY = { require_expiry: false, max_days: null, require_allowlist: false, site_allowlist_active: false }
const PERMISSIONS = [
    { id: 'ASSESS_ACCESS', name: 'Assess access', description: 'Access to Assess' },
    { id: 'ANALYZE_ACCESS', name: 'Analyze access', description: null }
]
const ITEM = {
    id: 7,
    name: 'SOAR sync',
    description: 'Pulls news items',
    key_prefix: 'tnk_abcdefgh',
    user: { id: 3, username: 'soar', name: 'SOAR' },
    user_id: 3,
    created_at: '2026-11-01T10:00:00+00:00',
    created_by: 'admin',
    expires_at: '2027-02-01T10:00:00+00:00',
    expired: false,
    enabled: true,
    restricted: true,
    permissions: [{ id: 'ASSESS_ACCESS', name: 'Assess access' }],
    allowed_ips: ['185.10.0.0/16'],
    last_used_at: null,
    last_used_ip: null
}

async function mountDialog(props = {}) {
    const wrapper = mountWithPlugins(ApiKeyDialog, {
        props: {
            modelValue: true,
            mode: 'self',
            policy: OPEN_POLICY,
            clientIp: '185.10.20.7',
            clientIpPublic: true,
            availablePermissions: PERMISSIONS,
            ...props
        }
    })
    await new Promise((resolve) => setTimeout(resolve, 0))
    await wrapper.vm.$nextTick()
    wrapper.vm.formRef = { validate: () => Promise.resolve({ valid: true }) }
    return wrapper
}

describe('ApiKeyDialog', () => {
    beforeEach(() => {
        vi.clearAllMocks()
        createMyApiKey.mockResolvedValue({ data: { item: { ...ITEM, id: 8 }, key: 'tnk_plaintext' } })
        createApiKey.mockResolvedValue({ data: { item: { ...ITEM, id: 8 }, key: 'tnk_plaintext' } })
        updateApiKey.mockResolvedValue({ data: { item: ITEM } })
        updateMyApiKey.mockResolvedValue({ data: { item: ITEM } })
        getApiKeyPermissions.mockResolvedValue({ data: { items: PERMISSIONS } })
    })

    it('offers every preset, a date and never, and starts at 90 days', async () => {
        const wrapper = await mountDialog()

        expect(wrapper.vm.expiryOptions.map((option) => option.value)).toEqual(['30', '90', '180', '365', 'custom', 'never'])
        expect(wrapper.vm.form.expiry).toBe('90')
    })

    it('follows the policy: no never, nothing past the maximum, which becomes the default', async () => {
        const wrapper = await mountDialog({ policy: { ...OPEN_POLICY, require_expiry: true, max_days: 60 } })

        expect(wrapper.vm.expiryOptions.map((option) => option.value)).toEqual(['30', 'max', 'custom'])
        expect(wrapper.vm.form.expiry).toBe('max')
        expect(wrapper.vm.maxDate).toBe(dateInDays(60))
        expect(wrapper.vm.withinMaxDate('2999-01-01')).not.toBe(true)
    })

    it('creates an own key with the chosen expiry, scope and allowlist, and hands back the plaintext', async () => {
        const wrapper = await mountDialog()
        const before = Date.now()
        wrapper.vm.form.name = '  CI pipeline '
        wrapper.vm.form.scope = 'selected'
        wrapper.vm.form.permissions = ['ANALYZE_ACCESS']
        wrapper.vm.form.allowedIps = '185.10.0.0/16\n\n2a01:4f8::/32'

        await wrapper.vm.save()

        expect(createMyApiKey).toHaveBeenCalledTimes(1)
        const body = createMyApiKey.mock.calls[0][0]
        expect(body).toMatchObject({
            name: 'CI pipeline',
            restricted: true,
            permissions: ['ANALYZE_ACCESS'],
            allowed_ips: ['185.10.0.0/16', '2a01:4f8::/32']
        })
        expect(body.user_id).toBeUndefined()
        const expires = Date.parse(body.expires_at)
        expect(expires).toBeGreaterThanOrEqual(before + 90 * DAY - 1000)
        expect(expires).toBeLessThanOrEqual(Date.now() + 90 * DAY)
        expect(wrapper.emitted('saved')[0][0]).toEqual({ item: { ...ITEM, id: 8 }, key: 'tnk_plaintext' })
        expect(wrapper.emitted('update:modelValue')[0]).toEqual([false])
    })

    it('sends no expiry for a key that never expires', async () => {
        const wrapper = await mountDialog()
        wrapper.vm.form.name = 'Forever'
        wrapper.vm.form.expiry = 'never'

        await wrapper.vm.save()

        expect(createMyApiKey.mock.calls[0][0].expires_at).toBeNull()
    })

    it('refuses a limited key with nothing picked', async () => {
        const wrapper = await mountDialog()
        wrapper.vm.form.name = 'Nothing'
        wrapper.vm.form.scope = 'selected'

        await wrapper.vm.save()

        expect(wrapper.vm.scopeError).toBe(true)
        expect(createMyApiKey).not.toHaveBeenCalled()
    })

    it('validates the allowlist and requires one when the policy does', async () => {
        const wrapper = await mountDialog({ policy: { ...OPEN_POLICY, require_allowlist: true } })

        expect(wrapper.vm.allowlistRule('')).toBe('New API keys must have an IP allowlist.')
        expect(wrapper.vm.allowlistRule('185.10.0.0/16\nexample.com')).toContain('example.com')
        expect(wrapper.vm.allowlistRule('185.10.0.0/16')).toBe(true)
    })

    it('refuses private, broadcast and other special addresses', async () => {
        const wrapper = await mountDialog()

        expect(wrapper.vm.allowlistRule('185.10.0.0/16\n10.0.0.0/8\n255.255.255.255\nfe80::1')).toBe(
            'Only public addresses can be listed, not: 10.0.0.0/8, 255.255.255.255, fe80::1'
        )
    })

    it('does not offer an address that is not public', async () => {
        const wrapper = await mountDialog({ clientIp: '172.20.0.1', clientIpPublic: false })

        expect(wrapper.vm.clientIpPublic).toBe(false)
        wrapper.vm.addMyIp()
        expect(wrapper.vm.form.allowedIps).toBe('')
    })

    it('adds the caller’s address once', async () => {
        const wrapper = await mountDialog()
        wrapper.vm.form.allowedIps = '185.10.0.0/16\n'

        wrapper.vm.addMyIp()
        wrapper.vm.addMyIp()

        expect(wrapper.vm.form.allowedIps).toBe('185.10.0.0/16\n185.10.20.7')
        expect(wrapper.vm.ipAlreadyListed).toBe(true)
    })

    it('lets an admin pick the owner and limits the picker to that user’s permissions', async () => {
        const owners = [
            { id: 3, username: 'soar', name: 'SOAR', status: 'active' },
            { id: 5, username: 'gone', name: 'Gone', status: 'disabled' }
        ]
        const wrapper = await mountDialog({ mode: 'admin', owners, availablePermissions: [] })

        expect(wrapper.vm.ownerItems).toEqual([{ value: 3, title: 'SOAR (soar)' }])
        wrapper.vm.form.ownerId = 3
        await new Promise((resolve) => setTimeout(resolve, 0))
        expect(getApiKeyPermissions).toHaveBeenCalledWith(3)
        expect(wrapper.vm.permissionItems.map((permission) => permission.id)).toEqual(['ASSESS_ACCESS', 'ANALYZE_ACCESS'])
        expect(wrapper.vm.permissionItems[1].description).toBe('')

        wrapper.vm.form.name = 'SOAR sync'
        await wrapper.vm.save()
        expect(createApiKey).toHaveBeenCalledWith(expect.objectContaining({ user_id: 3, name: 'SOAR sync' }))
    })

    it('edits a key without touching its owner or expiry', async () => {
        const wrapper = await mountDialog({ mode: 'admin', item: ITEM })

        expect(wrapper.vm.form).toMatchObject({
            name: 'SOAR sync',
            scope: 'selected',
            permissions: ['ASSESS_ACCESS'],
            allowedIps: '185.10.0.0/16'
        })
        expect(getApiKeyPermissions).toHaveBeenCalledWith(3)

        wrapper.vm.form.allowedIps = ''
        await wrapper.vm.save()

        expect(updateApiKey).toHaveBeenCalledWith(7, {
            name: 'SOAR sync',
            description: 'Pulls news items',
            restricted: true,
            permissions: ['ASSESS_ACCESS'],
            allowed_ips: []
        })
        expect(wrapper.emitted('saved')[0][0]).toEqual({ item: ITEM })
    })

    it('shows what the server refused', async () => {
        const rejection = new Error('bad request')
        rejection.response = { status: 400, data: { error: 'API keys may be valid for at most 30 days' } }
        createMyApiKey.mockRejectedValueOnce(rejection)
        const wrapper = await mountDialog()
        wrapper.vm.form.name = 'Too long'

        await wrapper.vm.save()

        expect(wrapper.vm.errorMessage).toBe('API keys may be valid for at most 30 days')
        expect(wrapper.emitted('saved')).toBeUndefined()
    })
})
