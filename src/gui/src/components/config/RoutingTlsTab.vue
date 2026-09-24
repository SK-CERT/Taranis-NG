<template>
    <v-container fluid>
        <v-form
            ref="formRef"
            @submit.prevent="save"
        >
            <v-alert
                type="info"
                variant="tonal"
                density="compact"
                class="mb-4"
            >
                {{ t('routing.intro') }}
            </v-alert>

            <!-- Certificates -->
            <!-- What Traefik actually serves, read from Traefik itself -->
            <v-card class="mb-4">
                <v-card-title class="d-flex align-center">
                    <v-icon class="mr-2">mdi-certificate-outline</v-icon>
                    {{ t('routing.served_title') }}
                    <v-spacer />
                    <v-btn
                        variant="text"
                        size="small"
                        prepend-icon="mdi-refresh"
                        :loading="loadingCertificates"
                        @click="loadCertificates"
                    >
                        {{ t('routing.served_refresh') }}
                    </v-btn>
                </v-card-title>

                <v-card-subtitle class="pb-2">
                    {{ t('routing.served_description') }}
                </v-card-subtitle>

                <v-card-text>
                    <v-table density="comfortable">
                        <thead>
                            <tr>
                                <th>{{ t('routing.served_hostname') }}</th>
                                <th>{{ t('routing.served_subject') }}</th>
                                <th>{{ t('routing.served_issuer') }}</th>
                                <th>{{ t('routing.served_key') }}</th>
                                <th>{{ t('routing.served_expires') }}</th>
                                <th>{{ t('routing.served_renews') }}</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr
                                v-for="row in certificates"
                                :key="row.hostname"
                            >
                                <td class="text-no-wrap">
                                    <v-icon
                                        :color="statusColor(row)"
                                        size="small"
                                        class="mr-1"
                                        >mdi-circle</v-icon
                                    >
                                    {{ row.hostname }}
                                </td>
                                <td>{{ row.subject || '-' }}</td>
                                <td>{{ row.issuer || '-' }}</td>
                                <td class="text-no-wrap">{{ row.key_type || '-' }}</td>
                                <td class="text-no-wrap">
                                    <span v-if="row.not_after">
                                        {{ row.not_after.slice(0, 10) }}
                                        <span class="text-medium-emphasis">{{ t('routing.served_days_left', { days: row.days_left }) }}</span>
                                    </span>
                                    <span v-else>{{ statusText(row) }}</span>
                                </td>
                                <td class="text-no-wrap">{{ row.renews_after || '-' }}</td>
                            </tr>
                            <tr v-if="!certificates.length">
                                <td
                                    colspan="6"
                                    class="text-medium-emphasis"
                                >
                                    {{ loadingCertificates ? t('routing.served_loading') : t('routing.served_none') }}
                                </td>
                            </tr>
                        </tbody>
                    </v-table>

                    <div class="text-caption text-medium-emphasis mt-3">
                        {{ t('routing.served_note') }}
                    </div>
                </v-card-text>
            </v-card>

            <v-card class="mb-4">
                <v-card-title class="d-flex align-center">
                    <v-icon class="mr-2">mdi-certificate</v-icon>
                    {{ t('routing.certificates_title') }}
                </v-card-title>

                <v-card-subtitle class="pb-2">
                    {{ t('routing.certificates_description') }}
                </v-card-subtitle>

                <v-card-text>
                    <v-text-field
                        v-model="settings.cert_resolver"
                        :label="t('routing.cert_resolver')"
                        variant="outlined"
                        density="comfortable"
                        placeholder="myresolver"
                        :hint="t('routing.cert_resolver_hint')"
                        persistent-hint
                        :rules="resolverRules"
                        :disabled="!canUpdate || saving"
                        class="mb-4"
                    />

                    <div
                        v-if="certSummary"
                        class="text-caption text-medium-emphasis mb-2"
                    >
                        {{ certSummary }}
                    </div>

                    <v-textarea
                        v-model="settings.default_cert"
                        :label="t('routing.default_cert')"
                        variant="outlined"
                        density="comfortable"
                        rows="4"
                        placeholder="-----BEGIN CERTIFICATE-----"
                        :hint="t('routing.default_cert_hint')"
                        persistent-hint
                        :disabled="!canUpdate || saving"
                        class="mb-4"
                    />

                    <v-textarea
                        v-model="settings.default_key"
                        :label="t('routing.default_key')"
                        variant="outlined"
                        density="comfortable"
                        rows="4"
                        :placeholder="settings.has_default_key ? t('routing.default_key_stored') : '-----BEGIN PRIVATE KEY-----'"
                        :hint="t('routing.default_key_hint')"
                        persistent-hint
                        :disabled="!canUpdate || saving"
                    />
                </v-card-text>
            </v-card>

            <!-- TLS handshake -->
            <v-card class="mb-4">
                <v-card-title class="d-flex align-center">
                    <v-icon class="mr-2">mdi-lock-check</v-icon>
                    {{ t('routing.tls_title') }}
                </v-card-title>

                <v-card-subtitle class="pb-2">
                    {{ t('routing.tls_description') }}
                </v-card-subtitle>

                <v-card-text>
                    <v-row>
                        <v-col
                            cols="12"
                            md="4"
                        >
                            <v-select
                                v-model="settings.tls_min_version"
                                :items="TLS_VERSIONS"
                                :label="t('routing.tls_min_version')"
                                variant="outlined"
                                density="comfortable"
                                clearable
                                :hint="t('routing.tls_min_version_hint')"
                                persistent-hint
                                :disabled="!canUpdate || saving"
                            />
                        </v-col>
                        <v-col
                            cols="12"
                            md="8"
                        >
                            <v-select
                                v-model="curves"
                                :items="TLS_CURVES"
                                :label="t('routing.tls_curves')"
                                variant="outlined"
                                density="comfortable"
                                multiple
                                chips
                                :hint="t('routing.tls_curves_hint')"
                                persistent-hint
                                :disabled="!canUpdate || saving"
                            />
                        </v-col>
                    </v-row>
                </v-card-text>
            </v-card>

            <!-- HSTS -->
            <v-card class="mb-4">
                <v-card-title class="d-flex align-center">
                    <v-icon class="mr-2">mdi-lock-check</v-icon>
                    {{ t('routing.hsts_title') }}
                </v-card-title>

                <v-card-subtitle class="pb-2">
                    {{ t('routing.hsts_description') }}
                </v-card-subtitle>

                <v-card-text>
                    <v-alert
                        v-if="settings.hsts_enabled"
                        type="warning"
                        variant="tonal"
                        density="comfortable"
                        class="mb-4"
                        :text="t('routing.hsts_warning')"
                    />

                    <v-switch
                        v-model="settings.hsts_enabled"
                        :label="t('routing.hsts_enabled')"
                        color="primary"
                        density="comfortable"
                        hide-details
                        :disabled="!canUpdate || saving"
                    />

                    <v-row class="mt-2">
                        <v-col
                            cols="12"
                            md="4"
                        >
                            <v-text-field
                                v-model.number="settings.hsts_max_age"
                                :label="t('routing.hsts_max_age')"
                                type="number"
                                variant="outlined"
                                density="comfortable"
                                :hint="t('routing.hsts_max_age_hint')"
                                persistent-hint
                                :rules="hstsMaxAgeRules"
                                :disabled="!canUpdate || saving || !settings.hsts_enabled"
                            />
                        </v-col>
                        <v-col
                            cols="12"
                            md="8"
                        >
                            <v-switch
                                v-model="settings.hsts_include_subdomains"
                                :label="t('routing.hsts_include_subdomains')"
                                color="primary"
                                density="comfortable"
                                :hint="t('routing.hsts_include_subdomains_hint')"
                                persistent-hint
                                :disabled="!canUpdate || saving || !settings.hsts_enabled"
                            />
                            <v-switch
                                v-model="settings.hsts_preload"
                                :label="t('routing.hsts_preload')"
                                color="primary"
                                density="comfortable"
                                :hint="t('routing.hsts_preload_hint')"
                                persistent-hint
                                :disabled="!canUpdate || saving || !settings.hsts_enabled || !settings.hsts_include_subdomains"
                            />
                        </v-col>
                    </v-row>

                    <v-alert
                        type="info"
                        variant="tonal"
                        density="compact"
                        class="mt-2"
                    >
                        <span class="text-medium-emphasis">{{ t('routing.hsts_preview') }}</span>
                        <code class="ml-2">{{ hstsPreviewHeader }}</code>
                    </v-alert>
                </v-card-text>
            </v-card>

            <!-- Response headers -->
            <v-card>
                <v-card-title class="d-flex align-center">
                    <v-icon class="mr-2">mdi-shield-check</v-icon>
                    {{ t('routing.headers_title') }}
                    <v-spacer />
                    <v-btn
                        v-if="canUpdate"
                        variant="text"
                        size="small"
                        prepend-icon="mdi-restore"
                        :disabled="saving"
                        @click="resetHeaders"
                    >
                        {{ t('routing.headers_reset') }}
                    </v-btn>
                </v-card-title>

                <v-card-subtitle class="pb-2">
                    {{ t('routing.headers_description') }}
                </v-card-subtitle>

                <v-card-text>
                    <EditableEntityTable
                        v-model="headerRows"
                        :title="t('routing.headers_title')"
                        :headers="headerColumns"
                        :default-item="() => ({ name: '', value: '' })"
                        :add-title="t('routing.header_add')"
                        :edit-title="t('routing.header_edit')"
                        :disabled="!canUpdate || saving"
                        dialog-max-width="800"
                        searchable
                        :no-data-text="t('routing.headers_none')"
                    >
                        <template #item.value="{ item }">
                            <span class="text-truncate d-inline-block header-value">{{ item.value }}</span>
                        </template>

                        <template #form="{ item }">
                            <v-text-field
                                v-model="item.name"
                                :label="t('routing.header_name')"
                                variant="outlined"
                                density="comfortable"
                                :rules="headerNameRules"
                            />
                            <v-textarea
                                v-model="item.value"
                                :label="t('routing.header_value')"
                                variant="outlined"
                                density="comfortable"
                                rows="5"
                                :rules="headerValueRules"
                            />
                        </template>
                    </EditableEntityTable>

                    <v-alert
                        v-if="errorMessage"
                        type="error"
                        density="compact"
                        class="mt-4"
                    >
                        {{ errorMessage }}
                    </v-alert>

                    <div class="d-flex align-center mt-4">
                        <span
                            v-if="settings.updated_by"
                            class="text-caption text-medium-emphasis"
                        >
                            {{ t('routing.last_updated', { user: settings.updated_by, at: settings.updated_at }) }}
                        </span>
                        <v-spacer />
                        <v-btn
                            v-if="canUpdate"
                            type="submit"
                            color="primary"
                            variant="flat"
                            prepend-icon="mdi-content-save"
                            :loading="saving"
                        >
                            {{ t('common.save') }}
                        </v-btn>
                    </div>
                </v-card-text>
            </v-card>
        </v-form>
    </v-container>
</template>

<script setup lang="ts">
    import { ref, computed, onMounted } from 'vue'
    import { useI18n } from 'vue-i18n'
    import { useAuth } from '@/composables/useAuth'
    import { getTraefikSettings, updateTraefikSettings, getTraefikCertificates } from '@/api/config'
    import EditableEntityTable from '@/components/common/EditableEntityTable.vue'

    // Kept in step with model/traefik_settings.py: Traefik rejects the whole
    // configuration document over one unknown name, so the form offers only
    // values it knows, and the backend checks them again.
    // No TLS 1.0/1.1: deprecated by RFC 8996 and refused by current browsers, so
    // they are not offered as a floor. Kept in step with model/traefik_settings.py.
    const TLS_VERSIONS = ['VersionTLS12', 'VersionTLS13']
    // Key-exchange groups, not certificate curves - an RSA certificate works with
    // these too. X25519MLKEM768 is the post-quantum hybrid.
    const TLS_CURVES = ['X25519MLKEM768', 'X25519', 'CurveP521', 'CurveP384', 'CurveP256']

    // Two years, and the one-year floor the browser preload list demands.
    const HSTS_MAX_AGE_LIMIT = 63072000
    const HSTS_PRELOAD_MIN_MAX_AGE = 31536000

    type TraefikSettingsItem = {
        security_headers: Record<string, string>
        hsts_enabled: boolean
        hsts_max_age: number
        hsts_include_subdomains: boolean
        hsts_preload: boolean
        tls_min_version: string
        tls_curve_preferences: string
        cert_resolver: string
        default_cert: string
        default_key: string
        has_default_key?: boolean
        cert_subject?: string
        cert_not_after?: string
        updated_by?: string
        updated_at?: string
    }

    type HeaderRow = Record<string, unknown> & { name: string; value: string }

    type FormValidationResult = {
        valid: boolean
    }

    const { t } = useI18n()
    const { checkPermission } = useAuth()

    type ServedCertificate = {
        hostname: string
        status: 'ok' | 'default' | 'error'
        subject?: string
        issuer?: string
        key_type?: string
        not_after?: string
        days_left?: number
        renews_after?: string
        self_signed?: boolean
        message?: string
    }

    const certificates = ref<ServedCertificate[]>([])
    const loadingCertificates = ref(false)

    const formRef = ref<any>(null)
    const saving = ref(false)
    const errorMessage = ref('')
    const headerRows = ref<HeaderRow[]>([])
    // Shipped defaults, captured on first load so "reset" has something to
    // restore even after the row has been edited.
    const defaultHeaders = ref<Record<string, string>>({})

    const settings = ref<TraefikSettingsItem>({
        security_headers: {},
        hsts_enabled: false,
        hsts_max_age: HSTS_PRELOAD_MIN_MAX_AGE,
        hsts_include_subdomains: false,
        hsts_preload: false,
        tls_min_version: '',
        tls_curve_preferences: '',
        cert_resolver: '',
        default_cert: '',
        default_key: ''
    })

    const canUpdate = computed(() => checkPermission('CONFIG_TRAEFIK_UPDATE'))

    const headerColumns = [
        { title: t('routing.header_name'), key: 'name', width: '30%' },
        { title: t('routing.header_value'), key: 'value' },
        { title: t('settings.actions'), key: 'actions', sortable: false, align: 'end' as const, width: '120px' }
    ]

    // The select works on a list; the backend stores the preference order as a
    // comma-separated string, because order is the whole point of the setting.
    const curves = computed<string[]>({
        get: () =>
            settings.value.tls_curve_preferences
                .split(',')
                .map((curve) => curve.trim())
                .filter((curve) => !!curve),
        set: (value: string[]) => {
            settings.value.tls_curve_preferences = value.join(',')
        }
    })

    const certSummary = computed(() => {
        if (!settings.value.cert_subject) return ''
        return t('routing.cert_summary', {
            subject: settings.value.cert_subject,
            expires: settings.value.cert_not_after
        })
    })

    // Mirrors _validated_hsts_max_age/_check_hsts in model/traefik_settings.py, so
    // the form says no before the backend has to.
    const hstsMaxAgeRules = [
        (v: number) => !settings.value.hsts_enabled || Number.isFinite(v) || t('routing.hsts_max_age_invalid'),
        (v: number) => !settings.value.hsts_enabled || v > 0 || t('routing.hsts_max_age_invalid'),
        (v: number) => v <= HSTS_MAX_AGE_LIMIT || t('routing.hsts_max_age_too_long'),
        (v: number) => !settings.value.hsts_preload || v >= HSTS_PRELOAD_MIN_MAX_AGE || t('routing.hsts_preload_needs_year')
    ]

    // Exactly what TraefikSettings.hsts_header_value builds, so the administrator
    // can see the header before saving it - including the "max-age=0" that an
    // unchecked switch sends to release browsers that are already pinned.
    const hstsPreview = computed(() => {
        if (!settings.value.hsts_enabled) return 'max-age=0'
        let value = `max-age=${settings.value.hsts_max_age ?? 0}`
        if (settings.value.hsts_include_subdomains) value += '; includeSubDomains'
        if (settings.value.hsts_preload) value += '; preload'
        return value
    })

    // Rendered as a binding rather than literal template text: the header name is
    // an HTTP token, not translatable copy, and @intlify/vue-i18n/no-raw-text
    // (rightly) rejects bare strings in the template.
    const hstsPreviewHeader = computed(() => `Strict-Transport-Security: ${hstsPreview.value}`)

    const resolverRules = [(v: string) => !v || /^[A-Za-z0-9_-]{1,64}$/.test(v) || t('routing.cert_resolver_invalid')]

    const headerNameRules = [
        (v: string) => !!v || t('error.required'),
        (v: string) => /^[A-Za-z0-9!#$%&'*+\-.^_`|~]+$/.test(v || '') || t('routing.header_name_invalid')
    ]

    // A line break in a value would let one header inject another; the backend
    // refuses it too.
    const headerValueRules = [(v: string) => !/[\r\n]/.test(v || '') || t('routing.header_value_invalid')]

    const toRows = (headers: Record<string, string>): HeaderRow[] => Object.entries(headers || {}).map(([name, value]) => ({ name, value }))

    const toHeaders = (rows: HeaderRow[]): Record<string, string> =>
        rows.reduce<Record<string, string>>((acc, row) => {
            if (row.name) acc[row.name] = row.value ?? ''
            return acc
        }, {})

    const applyResponse = (data: TraefikSettingsItem): void => {
        // The columns are nullable, so the API can hand back null for any of the
        // string fields. They are bound to inputs and split on, so they are
        // coerced here rather than guarded at every use.
        settings.value = {
            ...settings.value,
            ...data,
            tls_min_version: data.tls_min_version ?? '',
            tls_curve_preferences: data.tls_curve_preferences ?? '',
            cert_resolver: data.cert_resolver ?? '',
            hsts_max_age: data.hsts_max_age ?? HSTS_PRELOAD_MIN_MAX_AGE,
            default_cert: data.default_cert ?? '',
            // Write-only on the backend: it is never sent back, so the field is
            // cleared after every save and an empty one keeps the stored key.
            default_key: ''
        }
        headerRows.value = toRows(data.security_headers)
    }

    // Amber for Traefik's self-signed fallback or a certificate close to expiry,
    // red when the handshake failed outright.
    const statusColor = (row: ServedCertificate): string => {
        if (row.status === 'error') return 'error'
        if (row.status === 'default' || row.self_signed) return 'warning'
        if ((row.days_left ?? 0) < 30) return 'warning'
        return 'success'
    }

    const statusText = (row: ServedCertificate): string =>
        row.status === 'error' ? row.message || t('routing.served_unreachable') : t('routing.served_default')

    const loadCertificates = async (): Promise<void> => {
        loadingCertificates.value = true
        try {
            const response = (await getTraefikCertificates()) as { data: { items: ServedCertificate[] } }
            certificates.value = response.data.items ?? []
        } catch (error) {
            console.error('Error loading served certificates:', error)
            certificates.value = []
        } finally {
            loadingCertificates.value = false
        }
    }

    const loadData = async (): Promise<void> => {
        try {
            const response = (await getTraefikSettings()) as { data: TraefikSettingsItem }
            applyResponse(response.data)
            defaultHeaders.value = { ...response.data.security_headers }
        } catch (error) {
            console.error('Error loading routing and TLS settings:', error)
        }
    }

    const resetHeaders = (): void => {
        headerRows.value = toRows(defaultHeaders.value)
    }

    const save = async (): Promise<void> => {
        errorMessage.value = ''
        const { valid } = (await formRef.value.validate()) as FormValidationResult
        if (!valid) {
            return
        }

        saving.value = true
        try {
            const payload = { ...settings.value, security_headers: toHeaders(headerRows.value) }
            const response = (await updateTraefikSettings(payload)) as { data: TraefikSettingsItem }
            applyResponse(response.data)
            window.dispatchEvent(new CustomEvent('notification', { detail: { type: 'success', loc: 'common.updated_successfully' } }))
        } catch (error) {
            const data = (error as { response?: { data?: { error?: string } } })?.response?.data
            errorMessage.value = data?.error || t('routing.error')
            window.dispatchEvent(new CustomEvent('notification', { detail: { type: 'error', loc: 'common.error_saving' } }))
        } finally {
            saving.value = false
        }
    }

    onMounted(() => {
        loadData()
        loadCertificates()
    })
</script>

<style scoped>
    /* Values like the CSP are long enough to push the actions column off-screen. */
    .header-value {
        max-width: 40vw;
        vertical-align: middle;
    }
</style>
