<template>
    <v-container fluid>
        <!-- Which changes users are notified of -->
        <v-card class="mb-4">
            <v-card-title class="d-flex align-center">
                <v-icon class="mr-2">mdi-bell-cog-outline</v-icon>
                {{ t('notification_channels.events_title') }}
            </v-card-title>
            <v-card-text>
                <p class="text-body-2 text-medium-emphasis mb-2">{{ t('notification_channels.events_hint') }}</p>
                <v-row dense>
                    <v-col
                        v-for="item in events"
                        :key="item.event"
                        cols="12"
                        sm="6"
                        md="4"
                    >
                        <v-switch
                            :model-value="item.enabled"
                            :label="eventLabel(item.event)"
                            color="primary"
                            density="compact"
                            hide-details
                            :disabled="!canUpdate"
                            :loading="savingEvent === item.event"
                            :data-test="'event-' + item.event"
                            @update:model-value="(value) => toggleEvent(item, !!value)"
                        />
                    </v-col>
                </v-row>
            </v-card-text>
        </v-card>

        <!-- E-mail -->
        <v-card class="mb-4">
            <v-card-title class="d-flex align-center">
                <v-icon class="mr-2">mdi-email-outline</v-icon>
                {{ t('notification_channels.email_title') }}
                <v-spacer />
                <v-switch
                    v-model="email.enabled"
                    :label="t('notification_channels.enabled')"
                    color="primary"
                    density="compact"
                    hide-details
                    :disabled="!canUpdate"
                    data-test="email-enabled"
                />
            </v-card-title>
            <v-card-text>
                <v-alert
                    v-if="usersWithoutEmail > 0"
                    type="warning"
                    variant="tonal"
                    density="compact"
                    class="mb-4"
                    data-test="users-without-email"
                >
                    {{ t('notification_channels.users_without_email', { count: usersWithoutEmail }) }}
                </v-alert>

                <v-form
                    ref="formRef"
                    :disabled="!canUpdate"
                    @submit.prevent="save"
                >
                    <v-row>
                        <v-col
                            cols="12"
                            md="6"
                        >
                            <v-text-field
                                v-model="email.config.host"
                                :label="t('notification_channels.smtp_host')"
                                :rules="[required]"
                                variant="outlined"
                                density="comfortable"
                                :spellcheck="false"
                                data-test="smtp-host"
                            />
                        </v-col>
                        <v-col
                            cols="6"
                            md="3"
                        >
                            <v-select
                                :model-value="email.config.security"
                                :items="securityItems"
                                :label="t('notification_channels.smtp_security')"
                                variant="outlined"
                                density="comfortable"
                                data-test="smtp-security"
                                @update:model-value="changeSecurity"
                            />
                        </v-col>
                        <v-col
                            cols="6"
                            md="3"
                        >
                            <v-text-field
                                v-model.number="email.config.port"
                                type="number"
                                :label="t('notification_channels.smtp_port')"
                                :rules="[validPort]"
                                variant="outlined"
                                density="comfortable"
                                data-test="smtp-port"
                            />
                        </v-col>
                        <v-col
                            cols="12"
                            md="6"
                        >
                            <v-text-field
                                v-model="email.config.username"
                                :label="t('notification_channels.smtp_username')"
                                variant="outlined"
                                density="comfortable"
                                autocomplete="off"
                                :spellcheck="false"
                                data-test="smtp-username"
                            />
                        </v-col>
                        <v-col
                            cols="12"
                            md="6"
                        >
                            <v-text-field
                                v-model="password"
                                type="password"
                                :label="t('notification_channels.smtp_password')"
                                :hint="email.has_secret ? t('notification_channels.password_stored') : ''"
                                persistent-hint
                                variant="outlined"
                                density="comfortable"
                                autocomplete="new-password"
                                data-test="smtp-password"
                            />
                        </v-col>
                        <v-col
                            cols="12"
                            md="6"
                        >
                            <v-text-field
                                v-model="email.config.from_address"
                                type="email"
                                :label="t('notification_channels.from_address')"
                                :rules="[required, validEmail]"
                                variant="outlined"
                                density="comfortable"
                                :spellcheck="false"
                                data-test="from-address"
                            />
                        </v-col>
                        <v-col
                            cols="12"
                            md="6"
                        >
                            <v-text-field
                                v-model="email.config.from_name"
                                :label="t('notification_channels.from_name')"
                                variant="outlined"
                                density="comfortable"
                                data-test="from-name"
                            />
                        </v-col>
                        <v-col cols="12">
                            <v-switch
                                v-model="email.config.verify_tls"
                                :label="t('notification_channels.verify_tls')"
                                :hint="t('notification_channels.verify_tls_hint')"
                                persistent-hint
                                color="primary"
                                density="compact"
                                data-test="verify-tls"
                            />
                        </v-col>
                    </v-row>

                    <v-alert
                        v-if="errorMessage"
                        type="error"
                        density="compact"
                        class="mt-4"
                        data-test="save-error"
                    >
                        {{ errorMessage }}
                    </v-alert>

                    <div class="d-flex align-center mt-4">
                        <span
                            v-if="email.updated_by"
                            class="text-caption text-medium-emphasis"
                        >
                            {{ t('routing.last_updated', { user: email.updated_by, at: formatTime(email.updated_at) }) }}
                        </span>
                        <v-spacer />
                        <v-btn
                            v-if="canUpdate"
                            type="submit"
                            color="primary"
                            variant="flat"
                            prepend-icon="mdi-content-save"
                            :loading="saving"
                            data-test="save-email"
                        >
                            {{ t('common.save') }}
                        </v-btn>
                    </div>
                </v-form>

                <template v-if="canUpdate">
                    <v-divider class="my-4" />
                    <div class="d-flex align-center flex-wrap ga-2">
                        <v-text-field
                            v-model="testRecipient"
                            type="email"
                            :label="t('notification_channels.test_recipient')"
                            variant="outlined"
                            density="compact"
                            hide-details
                            class="test-recipient"
                            :spellcheck="false"
                            data-test="test-recipient"
                        />
                        <v-btn
                            variant="tonal"
                            prepend-icon="mdi-email-fast-outline"
                            :loading="testing"
                            :disabled="!testRecipient"
                            data-test="send-test"
                            @click="sendTest"
                        >
                            {{ t('notification_channels.send_test') }}
                        </v-btn>
                    </div>
                    <v-alert
                        v-if="testResult"
                        :type="testResult.ok ? 'success' : 'error'"
                        density="compact"
                        class="mt-3"
                        data-test="test-result"
                    >
                        <bdi dir="auto">{{ testResult.message }}</bdi>
                    </v-alert>
                </template>
            </v-card-text>
        </v-card>

        <!-- Delivery log -->
        <v-card>
            <v-card-title class="d-flex align-center">
                <v-icon class="mr-2">mdi-history</v-icon>
                {{ t('notification_channels.outbox_title') }}
            </v-card-title>
            <v-card-text>
                <div class="d-flex align-center flex-wrap ga-2 mb-3">
                    <v-select
                        v-model="statusFilter"
                        :items="statusItems"
                        :label="t('notification_channels.status')"
                        clearable
                        density="compact"
                        variant="outlined"
                        hide-details
                        class="status-filter"
                        data-test="status-filter"
                    />
                    <v-btn
                        variant="text"
                        size="small"
                        prepend-icon="mdi-refresh"
                        :loading="loadingOutbox"
                        data-test="refresh-outbox"
                        @click="loadOutbox"
                    >
                        {{ t('notification_channels.refresh') }}
                    </v-btn>
                </div>
                <v-data-table
                    :headers="outboxHeaders"
                    :items="outbox"
                    :loading="loadingOutbox"
                    :no-data-text="t('notification_channels.outbox_empty')"
                    density="compact"
                    data-test="outbox-table"
                >
                    <template #item.created_at="{ item }">
                        {{ formatTime(asOutboxItem(item).created_at) }}
                    </template>
                    <template #item.event="{ item }">
                        {{ eventLabel(asOutboxItem(item).event) }}
                    </template>
                    <template #item.recipient="{ item }">
                        <bdi dir="ltr">{{ asOutboxItem(item).recipient }}</bdi>
                    </template>
                    <template #item.status="{ item }">
                        <v-chip
                            size="small"
                            variant="tonal"
                            :color="statusColor(asOutboxItem(item).status)"
                            :data-test="'status-' + asOutboxItem(item).status"
                        >
                            {{ t('notification_channels.statuses.' + asOutboxItem(item).status) }}
                        </v-chip>
                    </template>
                    <template #item.last_error="{ item }">
                        <span class="text-caption">{{ asOutboxItem(item).last_error || '' }}</span>
                    </template>
                    <template #item.actions="{ item }">
                        <v-btn
                            v-if="canUpdate && asOutboxItem(item).status === 'failed'"
                            size="small"
                            variant="text"
                            prepend-icon="mdi-replay"
                            data-test="retry"
                            @click="retry(asOutboxItem(item))"
                        >
                            {{ t('notification_channels.retry') }}
                        </v-btn>
                    </template>
                </v-data-table>
            </v-card-text>
        </v-card>
    </v-container>
</template>

<script setup lang="ts">
    import { ref, computed, onMounted, watch } from 'vue'
    import { useI18n } from 'vue-i18n'
    import { useAuth } from '@/composables/useAuth'
    import { useLocaleFormatters } from '@/composables/useLocaleFormatters'
    import {
        getNotificationSettings,
        saveNotificationEvents,
        saveNotificationChannel,
        testNotificationChannel,
        getNotificationOutbox,
        retryNotification
    } from '@/api/config'

    type Security = 'starttls' | 'ssl' | 'none'

    type EmailConfig = {
        host: string
        port: number | string
        security: Security
        verify_tls: boolean
        username: string
        from_address: string
        from_name: string
    }

    type EmailChannel = {
        kind: 'email'
        enabled: boolean
        config: EmailConfig
        has_secret: boolean
        updated_by?: string | null
        updated_at?: string | null
    }

    type OutboxItem = {
        id: number
        channel_kind: string
        recipient: string
        event: string
        subject: string
        status: 'pending' | 'sending' | 'sent' | 'failed'
        attempts: number
        last_error?: string | null
        created_at?: string | null
        sent_at?: string | null
    }

    type EventSwitch = {
        event: string
        enabled: boolean
    }

    type ApiError = { response?: { data?: { error?: string } } }

    // Kept in step with managers/notifications/channels.py.
    const DEFAULT_PORTS: Record<Security, number> = { starttls: 587, ssl: 465, none: 25 }
    const EMAIL_RE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/
    const STATUSES = ['pending', 'sending', 'sent', 'failed'] as const

    const { t, te } = useI18n()
    const { checkPermission } = useAuth()
    const { formatDateTime } = useLocaleFormatters()

    const canUpdate = computed(() => checkPermission('CONFIG_NOTIFICATIONS_UPDATE'))

    const defaultEmail = (): EmailChannel => ({
        kind: 'email',
        enabled: false,
        config: {
            host: '',
            port: DEFAULT_PORTS.starttls,
            security: 'starttls',
            verify_tls: true,
            username: '',
            from_address: '',
            from_name: ''
        },
        has_secret: false,
        updated_by: null,
        updated_at: null
    })

    const formRef = ref<{ validate: () => Promise<{ valid: boolean }> } | null>(null)
    const email = ref<EmailChannel>(defaultEmail())
    // Write-only: the stored password never comes back; empty keeps it.
    const password = ref('')
    const usersWithoutEmail = ref(0)
    const saving = ref(false)
    const errorMessage = ref('')

    const testRecipient = ref('')
    const testing = ref(false)
    const testResult = ref<{ ok: boolean; message: string } | null>(null)

    const events = ref<EventSwitch[]>([])
    const savingEvent = ref<string | null>(null)

    const outbox = ref<OutboxItem[]>([])
    const loadingOutbox = ref(false)
    const statusFilter = ref<string | null>(null)

    const securityItems = computed(() => [
        { title: t('notification_channels.security_starttls'), value: 'starttls' },
        { title: t('notification_channels.security_ssl'), value: 'ssl' },
        { title: t('notification_channels.security_none'), value: 'none' }
    ])
    const statusItems = computed(() => STATUSES.map((status) => ({ title: t('notification_channels.statuses.' + status), value: status })))
    const outboxHeaders = computed(() => [
        { title: t('notification_channels.created_at'), key: 'created_at' },
        { title: t('notification_channels.event'), key: 'event' },
        { title: t('notification_channels.recipient'), key: 'recipient' },
        { title: t('notification_channels.status'), key: 'status' },
        { title: t('notification_channels.attempts'), key: 'attempts', align: 'end' as const },
        { title: t('notification_channels.last_error'), key: 'last_error', sortable: false },
        { title: t('settings.actions'), key: 'actions', sortable: false, align: 'end' as const }
    ])

    const required = (value: unknown): true | string => !!String(value ?? '').trim() || t('error.required')
    const validEmail = (value: unknown): true | string =>
        EMAIL_RE.test(String(value ?? '').trim()) || t('notification_channels.invalid_email')
    const validPort = (value: unknown): true | string => {
        const port = Number(value)
        return (Number.isInteger(port) && port >= 1 && port <= 65535) || t('notification_channels.invalid_port')
    }

    const asOutboxItem = (item: unknown): OutboxItem => item as OutboxItem
    const formatTime = (value?: string | null): string => (value ? formatDateTime(value) || value : '')
    const eventLabel = (event: string): string =>
        te('notification_channels.events.' + event) ? t('notification_channels.events.' + event) : event
    const statusColor = (status: string): string =>
        ({ pending: 'info', sending: 'info', sent: 'success', failed: 'error' })[status] || 'default'

    const errorOf = (error: unknown, fallback: string): string => (error as ApiError)?.response?.data?.error || fallback

    // A port left at the old mode's default follows the new mode; one typed in stays.
    const changeSecurity = (security: Security): void => {
        const previous = email.value.config.security
        if (!email.value.config.port || Number(email.value.config.port) === DEFAULT_PORTS[previous]) {
            email.value.config.port = DEFAULT_PORTS[security]
        }
        email.value.config.security = security
    }

    const applyChannel = (channel?: Partial<EmailChannel> | null): void => {
        const base = defaultEmail()
        email.value = { ...base, ...(channel || {}), config: { ...base.config, ...(channel?.config || {}) } } as EmailChannel
    }

    const loadSettings = async (): Promise<void> => {
        try {
            const response = (await getNotificationSettings()) as {
                data: { channels: Partial<EmailChannel>[]; events?: EventSwitch[]; users_without_email: number }
            }
            applyChannel(response.data.channels.find((channel) => channel.kind === 'email'))
            events.value = response.data.events || []
            usersWithoutEmail.value = response.data.users_without_email || 0
        } catch (error) {
            errorMessage.value = errorOf(error, t('notification_channels.error'))
        }
    }

    const loadOutbox = async (): Promise<void> => {
        loadingOutbox.value = true
        try {
            const response = (await getNotificationOutbox(statusFilter.value)) as { data: { items: OutboxItem[] } }
            outbox.value = response.data.items || []
        } catch (error) {
            console.error('Error loading the notification outbox:', error)
        } finally {
            loadingOutbox.value = false
        }
    }

    const payload = (): Record<string, unknown> => ({
        enabled: email.value.enabled,
        config: { ...email.value.config, port: Number(email.value.config.port) },
        ...(password.value ? { secret: password.value } : {})
    })

    const save = async (): Promise<void> => {
        errorMessage.value = ''
        const result = await formRef.value?.validate()
        if (result && !result.valid) return
        saving.value = true
        try {
            const response = (await saveNotificationChannel('email', payload())) as { data: EmailChannel }
            applyChannel(response.data)
            password.value = ''
            window.dispatchEvent(new CustomEvent('notification', { detail: { type: 'success', loc: 'common.updated_successfully' } }))
        } catch (error) {
            errorMessage.value = errorOf(error, t('notification_channels.error'))
            window.dispatchEvent(new CustomEvent('notification', { detail: { type: 'error', loc: 'common.error_saving' } }))
        } finally {
            saving.value = false
        }
    }

    // A switch saves at once; a refusal puts it back.
    const toggleEvent = async (item: EventSwitch, enabled: boolean): Promise<void> => {
        const previous = item.enabled
        item.enabled = enabled
        savingEvent.value = item.event
        try {
            const response = (await saveNotificationEvents({ [item.event]: enabled })) as { data: { events: EventSwitch[] } }
            events.value = response.data.events || events.value
            window.dispatchEvent(new CustomEvent('notification', { detail: { type: 'success', loc: 'common.updated_successfully' } }))
        } catch (error) {
            item.enabled = previous
            console.error('Error saving the notification events:', error)
            window.dispatchEvent(new CustomEvent('notification', { detail: { type: 'error', loc: 'common.error_saving' } }))
        } finally {
            savingEvent.value = null
        }
    }

    // Tests the settings in the form, saved or not.
    const sendTest = async (): Promise<void> => {
        testResult.value = null
        testing.value = true
        const recipient = testRecipient.value.trim()
        try {
            await testNotificationChannel('email', { ...payload(), recipient })
            testResult.value = { ok: true, message: t('notification_channels.test_sent', { recipient }) }
        } catch (error) {
            testResult.value = { ok: false, message: errorOf(error, t('notification_channels.error')) }
        } finally {
            testing.value = false
        }
    }

    const retry = async (item: OutboxItem): Promise<void> => {
        try {
            await retryNotification(item.id)
            window.dispatchEvent(new CustomEvent('notification', { detail: { type: 'success', loc: 'notification_channels.retried' } }))
        } catch (error) {
            console.error('Error retrying a notification:', error)
        }
        await loadOutbox()
    }

    watch(statusFilter, () => {
        loadOutbox()
    })

    onMounted(() => {
        loadSettings()
        loadOutbox()
    })
</script>

<style scoped>
    .test-recipient {
        max-width: 360px;
        min-width: 240px;
    }

    .status-filter {
        max-width: 200px;
        min-width: 160px;
    }
</style>
