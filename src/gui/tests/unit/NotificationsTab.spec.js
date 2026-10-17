import { describe, it, expect, beforeEach, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { mountWithPlugins } from '../helpers/mount-helpers'
import NotificationsTab from '@/components/config/NotificationsTab.vue'
import SettingsView from '@/views/admin/SettingsView.vue'
import {
    getNotificationSettings,
    saveNotificationEvents,
    saveNotificationChannel,
    testNotificationChannel,
    getNotificationOutbox,
    retryNotification
} from '@/api/config'

const { granted } = vi.hoisted(() => ({ granted: new Set() }))

vi.mock('@/composables/useAuth', () => ({
    useAuth: () => ({ checkPermission: (permission) => granted.has(permission) })
}))

vi.mock('@/api/config', () => ({
    getNotificationSettings: vi.fn(),
    saveNotificationEvents: vi.fn(),
    saveNotificationChannel: vi.fn(),
    testNotificationChannel: vi.fn(),
    getNotificationOutbox: vi.fn(),
    retryNotification: vi.fn()
}))

const CHANNEL = {
    kind: 'email',
    enabled: true,
    config: {
        host: 'smtp.example.test',
        port: 587,
        security: 'starttls',
        verify_tls: true,
        username: 'taranis',
        from_address: 'taranis@example.test',
        from_name: 'Taranis NG'
    },
    has_secret: true,
    updated_by: 'Admin',
    updated_at: '2026-10-15T10:00:00+02:00'
}

const EVENTS = [
    { event: 'password_changed', enabled: true },
    { event: 'password_removed', enabled: true },
    { event: 'totp_enabled', enabled: false },
    { event: 'totp_disabled', enabled: true },
    { event: 'passkey_added', enabled: true },
    { event: 'passkey_removed', enabled: true },
    { event: 'mfa_reset', enabled: true }
]

const OUTBOX = [
    {
        id: 1,
        channel_kind: 'email',
        recipient: 'alice@example.test',
        event: 'totp_enabled',
        subject: 'S',
        status: 'sent',
        attempts: 1,
        last_error: null,
        created_at: '2026-10-15T10:01:00+02:00'
    },
    {
        id: 2,
        channel_kind: 'email',
        recipient: 'bob@example.test',
        event: 'passkey_removed',
        subject: 'S',
        status: 'failed',
        attempts: 7,
        last_error: 'SMTP login failed: 535',
        created_at: '2026-10-15T09:00:00+02:00'
    }
]

async function mountTab({
    permissions = ['CONFIG_NOTIFICATIONS_ACCESS', 'CONFIG_NOTIFICATIONS_UPDATE'],
    channel = CHANNEL,
    withoutEmail = 3
} = {}) {
    granted.clear()
    permissions.forEach((permission) => granted.add(permission))
    getNotificationSettings.mockResolvedValue({
        data: { channels: [channel], events: EVENTS.map((item) => ({ ...item })), users_without_email: withoutEmail }
    })
    getNotificationOutbox.mockResolvedValue({ data: { items: OUTBOX } })
    const wrapper = mountWithPlugins(NotificationsTab)
    await flushPromises()
    return wrapper
}

const byTest = (wrapper, name) => wrapper.find(`[data-test="${name}"]`)
const input = (wrapper, name) => wrapper.get(`[data-test="${name}"] input`)

describe('NotificationsTab', () => {
    beforeEach(() => {
        vi.clearAllMocks()
    })

    it('shows the saved e-mail settings, never a stored password', async () => {
        const wrapper = await mountTab()

        expect(input(wrapper, 'smtp-host').element.value).toBe('smtp.example.test')
        expect(input(wrapper, 'from-address').element.value).toBe('taranis@example.test')
        expect(input(wrapper, 'smtp-password').element.value).toBe('')
        expect(wrapper.text()).toContain('A password is stored. Leave empty to keep it.')
    })

    it('warns how many active users e-mail cannot reach', async () => {
        const wrapper = await mountTab()

        expect(byTest(wrapper, 'users-without-email').text()).toContain('Active users without an e-mail address: 3.')
    })

    it('says nothing about addresses when every user has one', async () => {
        const wrapper = await mountTab({ withoutEmail: 0 })

        expect(byTest(wrapper, 'users-without-email').exists()).toBe(false)
    })

    it('shows a switch for every change users can be notified of', async () => {
        const wrapper = await mountTab()

        expect(byTest(wrapper, 'event-password_changed').text()).toContain('Password changed')
        expect(byTest(wrapper, 'event-password_removed').text()).toContain('Password sign-in turned off')
        expect(input(wrapper, 'event-password_changed').element.checked).toBe(true)
        expect(input(wrapper, 'event-totp_enabled').element.checked).toBe(false)
    })

    it('saves a switch as soon as it is flipped', async () => {
        saveNotificationEvents.mockResolvedValue({
            data: { events: EVENTS.map((item) => (item.event === 'password_changed' ? { ...item, enabled: false } : item)) }
        })
        const wrapper = await mountTab()

        await input(wrapper, 'event-password_changed').setValue(false)
        await flushPromises()

        expect(saveNotificationEvents).toHaveBeenCalledWith({ password_changed: false })
        expect(input(wrapper, 'event-password_changed').element.checked).toBe(false)
    })

    it('puts a switch back when saving it fails', async () => {
        saveNotificationEvents.mockRejectedValue(new Error('offline'))
        const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
        const wrapper = await mountTab()

        await input(wrapper, 'event-mfa_reset').setValue(false)
        await flushPromises()

        expect(input(wrapper, 'event-mfa_reset').element.checked).toBe(true)
        errorSpy.mockRestore()
    })

    it('saves without a password when none was typed, so the stored one is kept', async () => {
        saveNotificationChannel.mockResolvedValue({ data: CHANNEL })
        const wrapper = await mountTab()

        await wrapper.vm.save()
        await flushPromises()

        expect(saveNotificationChannel).toHaveBeenCalledWith('email', { enabled: true, config: { ...CHANNEL.config, port: 587 } })
    })

    it('sends a typed password once and then forgets it', async () => {
        saveNotificationChannel.mockResolvedValue({ data: CHANNEL })
        const wrapper = await mountTab()
        await input(wrapper, 'smtp-password').setValue('n3w-secret')

        await wrapper.vm.save()
        await flushPromises()

        expect(saveNotificationChannel.mock.calls[0][1].secret).toBe('n3w-secret')
        expect(input(wrapper, 'smtp-password').element.value).toBe('')
    })

    it('shows why the server refused the settings', async () => {
        saveNotificationChannel.mockRejectedValue({ response: { data: { error: 'Sender address must be an e-mail address' } } })
        const wrapper = await mountTab()

        await wrapper.vm.save()
        await flushPromises()

        expect(byTest(wrapper, 'save-error').text()).toBe('Sender address must be an e-mail address')
    })

    it('moves the port with the security mode unless one was typed in', async () => {
        const wrapper = await mountTab()

        wrapper.vm.changeSecurity('ssl')
        expect(wrapper.vm.email.config.port).toBe(465)

        wrapper.vm.email.config.port = 2525
        wrapper.vm.changeSecurity('starttls')
        expect(wrapper.vm.email.config.port).toBe(2525)
    })

    it('tests the settings in the form, and reports the outcome', async () => {
        testNotificationChannel.mockResolvedValueOnce({ data: { ok: true } })
        testNotificationChannel.mockRejectedValueOnce({ response: { data: { error: 'SMTP login failed: 535 Bad credentials' } } })
        const wrapper = await mountTab()
        wrapper.vm.email.config.host = 'relay.example.test'
        await input(wrapper, 'test-recipient').setValue('admin@example.test')

        await byTest(wrapper, 'send-test').trigger('click')
        await flushPromises()

        expect(testNotificationChannel).toHaveBeenCalledWith(
            'email',
            expect.objectContaining({ recipient: 'admin@example.test', config: expect.objectContaining({ host: 'relay.example.test' }) })
        )
        expect(byTest(wrapper, 'test-result').text()).toBe('Test e-mail sent to admin@example.test.')

        await byTest(wrapper, 'send-test').trigger('click')
        await flushPromises()

        expect(byTest(wrapper, 'test-result').text()).toBe('SMTP login failed: 535 Bad credentials')
    })

    it('lists deliveries with their status and offers a retry only for failed ones', async () => {
        const wrapper = await mountTab()
        const rows = wrapper.findAll('[data-test="outbox-table"] tbody tr')

        expect(rows).toHaveLength(2)
        expect(rows[0].text()).toContain('TOTP turned on')
        expect(rows[0].text()).toContain('Sent')
        expect(rows[0].find('[data-test="retry"]').exists()).toBe(false)
        expect(rows[1].text()).toContain('Passkey removed')
        expect(rows[1].text()).toContain('SMTP login failed: 535')
        expect(rows[1].find('[data-test="retry"]').exists()).toBe(true)
    })

    it('retries a failed delivery and reloads the log', async () => {
        retryNotification.mockResolvedValue({ data: {} })
        const wrapper = await mountTab()

        await wrapper.get('[data-test="outbox-table"] [data-test="retry"]').trigger('click')
        await flushPromises()

        expect(retryNotification).toHaveBeenCalledWith(2)
        expect(getNotificationOutbox).toHaveBeenCalledTimes(2)
    })

    it('filters the log by status', async () => {
        const wrapper = await mountTab()

        wrapper.vm.statusFilter = 'failed'
        await flushPromises()

        expect(getNotificationOutbox).toHaveBeenLastCalledWith('failed')
    })

    it('is read-only without the update permission', async () => {
        const wrapper = await mountTab({ permissions: ['CONFIG_NOTIFICATIONS_ACCESS'] })

        expect(byTest(wrapper, 'save-email').exists()).toBe(false)
        expect(byTest(wrapper, 'send-test').exists()).toBe(false)
        expect(byTest(wrapper, 'retry').exists()).toBe(false)
        expect(input(wrapper, 'event-password_changed').attributes('disabled')).toBeDefined()
    })
})

describe('SettingsView notifications tab', () => {
    async function mountView(permissions) {
        granted.clear()
        permissions.forEach((permission) => granted.add(permission))
        const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/', component: SettingsView }] })
        await router.push('/')
        await router.isReady()
        const wrapper = mountWithPlugins(SettingsView, {
            global: {
                plugins: [router],
                stubs: {
                    SettingsTable: true,
                    RoutingTlsTab: true,
                    NotificationsTab: { template: '<div data-test="notifications-content" />' }
                }
            }
        })
        await flushPromises()
        return wrapper
    }

    const tabValues = (wrapper) => wrapper.findAllComponents({ name: 'VTab' }).map((tab) => tab.props('value'))

    it('is shown to whoever may see the notification settings', async () => {
        const wrapper = await mountView(['CONFIG_SETTINGS_ACCESS', 'CONFIG_NOTIFICATIONS_ACCESS'])

        expect(tabValues(wrapper)).toEqual(['general', 'notifications'])
    })

    it('is hidden from everyone else', async () => {
        const wrapper = await mountView(['CONFIG_SETTINGS_ACCESS'])

        expect(tabValues(wrapper)).toEqual(['general'])
    })
})
