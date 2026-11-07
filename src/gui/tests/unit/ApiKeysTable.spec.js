import { describe, it, expect, vi } from 'vitest'
import { mountWithPlugins } from '../helpers/mount-helpers'
import ApiKeysTable from '@/components/common/api-keys/ApiKeysTable.vue'
import ApiKeyRevealDialog from '@/components/common/api-keys/ApiKeyRevealDialog.vue'

const DAY = 24 * 60 * 60 * 1000
const key = (fields) => ({
    id: 1,
    name: 'SOAR sync',
    description: 'Pulls news items',
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

const mountTable = (items, props = {}) => mountWithPlugins(ApiKeysTable, { props: { items, ...props } })

describe('ApiKeysTable', () => {
    it('shows the prefix, never the key, with the scope, allowlist and usage of each key', () => {
        const wrapper = mountTable([
            key({
                restricted: true,
                permissions: [{ id: 'ASSESS_ACCESS', name: 'Assess access' }],
                allowed_ips: ['185.10.0.0/16', '8.8.8.8/32']
            }),
            key({ id: 2, name: 'Second', last_used_at: '2026-11-06T09:00:00+00:00', last_used_ip: '198.51.100.7' })
        ])
        const text = wrapper.text()

        expect(text).toContain('tnk_abcdefgh…')
        expect(text).toContain('Limited (1)')
        expect(text).toContain('Limited (2)')
        expect(text).toContain('All')
        expect(text).toContain('Any')
        expect(text).toContain('Never used')
        expect(wrapper.findAll('[data-test="api-key-scope"]')[0].attributes('title')).toBe('Assess access')
        expect(wrapper.findAll('[data-test="api-key-ips"]')[0].attributes('title')).toBe('185.10.0.0/16\n8.8.8.8/32')
    })

    it('adds the owner column only for the admin view', () => {
        expect(mountTable([key()]).vm.headers.map((header) => header.key)).not.toContain('owner')
        expect(mountTable([key()], { showOwner: true }).vm.headers.map((header) => header.key)).toContain('owner')
        expect(mountTable([key()], { compact: true }).vm.headers.map((header) => header.key)).not.toContain('created_at')
    })

    it('marks expired keys and keys about to expire, and dims what does not work', () => {
        const wrapper = mountTable([
            key({ id: 1, expired: true, expires_at: new Date(Date.now() - DAY).toISOString() }),
            key({ id: 2, expires_at: new Date(Date.now() + 2 * DAY).toISOString() }),
            key({ id: 3, enabled: false })
        ])

        expect(wrapper.findAll('[data-test="api-key-expired"]')).toHaveLength(1)
        expect(wrapper.findAll('[data-test="api-key-expires-soon"]')).toHaveLength(1)
        expect(wrapper.findAll('tr.api-key-inactive')).toHaveLength(2)
    })

    it('offers enable for a paused key, disable for a working one, and hides what is not allowed', async () => {
        const items = [key({ id: 1 }), key({ id: 2, enabled: false })]
        const wrapper = mountTable(items)

        expect(wrapper.findAll('[data-test="api-key-disable"]')).toHaveLength(1)
        expect(wrapper.findAll('[data-test="api-key-enable"]')).toHaveLength(1)
        await wrapper.get('[data-test="api-key-enable"]').trigger('click')
        expect(wrapper.emitted('toggle')[0][0]).toEqual(items[1])

        const readOnly = mountTable(items, { canUpdate: false, canDelete: false })
        expect(readOnly.find('[data-test="api-key-edit"]').exists()).toBe(false)
        expect(readOnly.find('[data-test="api-key-delete"]').exists()).toBe(false)
        expect(readOnly.find('[data-test="api-key-enable"]').exists()).toBe(false)
    })
})

describe('ApiKeyRevealDialog', () => {
    it('builds a ready-to-paste example and copies the key', async () => {
        const writeText = vi.fn().mockResolvedValue(undefined)
        Object.defineProperty(navigator, 'clipboard', { value: { writeText }, configurable: true })
        const wrapper = mountWithPlugins(ApiKeyRevealDialog, { props: { modelValue: true, apiKey: 'tnk_secret', name: 'CI' } })

        expect(wrapper.vm.example).toContain('Authorization: ApiKey tnk_secret')
        expect(wrapper.vm.example).toContain(`${window.location.origin}/api/v1/assess/osint-source-groups`)

        await wrapper.vm.copy()
        expect(writeText).toHaveBeenCalledWith('tnk_secret')
        expect(wrapper.vm.copied).toBe(true)
    })

    it('says so when the browser refuses to copy', async () => {
        Object.defineProperty(navigator, 'clipboard', {
            value: { writeText: vi.fn().mockRejectedValue(new Error('denied')) },
            configurable: true
        })
        const wrapper = mountWithPlugins(ApiKeyRevealDialog, { props: { modelValue: true, apiKey: 'tnk_secret' } })

        await wrapper.vm.copy()
        expect(wrapper.vm.copyFailed).toBe(true)
    })
})
