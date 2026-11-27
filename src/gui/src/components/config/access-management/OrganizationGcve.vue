<template>
    <div data-test="organization-gcve">
        <v-progress-linear
            v-if="loading"
            indeterminate
            color="primary"
            class="mb-3"
        />

        <v-alert
            v-if="errorMessage"
            type="error"
            variant="tonal"
            density="compact"
            class="mb-4"
            data-test="organization-gcve-error"
        >
            <bdi dir="auto">{{ errorMessage }}</bdi>
        </v-alert>

        <v-form
            ref="formRef"
            :disabled="!canUpdate || saving"
            @submit.prevent
        >
            <!-- The GNA: a number from gcve.eu; its names come from the gcve.eu GNA directory. -->
            <section class="mb-6">
                <h3 class="text-subtitle-1 font-weight-medium d-flex align-center mb-1">
                    <v-icon
                        class="me-2"
                        size="small"
                        >mdi-identifier</v-icon
                    >
                    {{ t('gna.organization.gna_title') }}
                </h3>
                <p class="text-body-2 text-medium-emphasis mb-4">{{ t('gna.organization.gna_hint') }}</p>

                <v-row>
                    <v-col
                        cols="12"
                        sm="4"
                    >
                        <v-text-field
                            v-model="form.gna_id"
                            :label="t('gna.organization.gna_id')"
                            :hint="frozen ? t('gna.organization.gna_id_frozen') : t('gna.organization.gna_id_hint')"
                            persistent-hint
                            inputmode="numeric"
                            :rules="[gnaIdRule]"
                            :disabled="frozen"
                            variant="outlined"
                            density="comfortable"
                            :spellcheck="false"
                            data-test="organization-gna-id"
                        />
                    </v-col>
                    <v-col
                        cols="12"
                        sm="8"
                    >
                        <v-text-field
                            v-model="form.records_license"
                            :label="t('gna.organization.records_license')"
                            :placeholder="DEFAULT_LICENSE"
                            persistent-placeholder
                            variant="outlined"
                            density="comfortable"
                            :spellcheck="false"
                            :disabled="!hasNumber"
                            data-test="organization-gna-license"
                        />
                    </v-col>
                </v-row>

                <div
                    v-if="stored"
                    class="mt-2"
                    data-test="organization-gna-directory"
                >
                    <v-alert
                        v-if="stored.short_name"
                        type="success"
                        variant="tonal"
                        density="compact"
                        data-test="organization-gna-confirmed"
                    >
                        <div>
                            {{ t('gna.organization.directory_confirmed', { id: stored.gna_id }) }}
                            <strong>
                                <bdi dir="auto">{{ stored.short_name }}</bdi>
                            </strong>
                            <template v-if="stored.directory?.full_name">
                                (<bdi dir="auto">{{ stored.directory.full_name }}</bdi
                                >)
                            </template>
                        </div>
                        <div
                            v-if="stored.directory_checked_at"
                            class="text-caption"
                        >
                            {{ t('gna.organization.directory_checked', { at: formatTime(stored.directory_checked_at) }) }}
                        </div>
                    </v-alert>
                    <v-alert
                        v-else-if="stored.directory_checked_at"
                        type="warning"
                        variant="tonal"
                        density="compact"
                        data-test="organization-gna-unknown"
                    >
                        {{ t('gna.organization.directory_unknown', { id: stored.gna_id }) }}
                    </v-alert>
                    <v-alert
                        v-else
                        type="info"
                        variant="tonal"
                        density="compact"
                        data-test="organization-gna-unchecked"
                    >
                        {{ t('gna.organization.directory_unchecked') }}
                    </v-alert>
                </div>
                <v-alert
                    v-if="directory?.error"
                    type="warning"
                    variant="tonal"
                    density="compact"
                    class="mt-2"
                    data-test="organization-directory-error"
                >
                    {{ t('gna.organization.directory_error') }}
                    <bdi dir="auto">{{ directory.error }}</bdi>
                </v-alert>
                <v-alert
                    v-else-if="directory?.fetched_at && !directory.verified"
                    type="warning"
                    variant="tonal"
                    density="compact"
                    class="mt-2"
                    data-test="organization-directory-unverified"
                >
                    {{ t('gna.organization.directory_unverified', { url: directory.url }) }}
                </v-alert>

                <v-textarea
                    v-model="form.conformance"
                    :label="t('gna.organization.conformance')"
                    :hint="t('gna.organization.conformance_hint')"
                    persistent-hint
                    :rules="[conformanceRule]"
                    :disabled="!hasNumber"
                    variant="outlined"
                    density="comfortable"
                    class="mt-4 conformance"
                    rows="4"
                    auto-grow
                    :spellcheck="false"
                    data-test="organization-gna-conformance"
                />
            </section>

            <!-- Where its records are published, what to register at gcve.eu, and whether it answers. -->
            <section
                v-if="stored"
                class="mb-6"
                data-test="organization-gcve-publication"
            >
                <h3 class="text-subtitle-1 font-weight-medium d-flex align-center mb-1">
                    <v-icon
                        class="me-2"
                        size="small"
                        >mdi-web</v-icon
                    >
                    {{ t('gna.organization.publication_title') }}
                    <v-spacer />
                    <v-btn
                        v-if="canUpdate"
                        variant="tonal"
                        size="small"
                        prepend-icon="mdi-check-network-outline"
                        :loading="checking"
                        :title="t('gna.organization.check_hint')"
                        data-test="organization-gcve-check"
                        @click="check"
                    >
                        {{ t('gna.organization.check') }}
                    </v-btn>
                </h3>
                <v-alert
                    v-if="!webs.length"
                    type="info"
                    variant="tonal"
                    density="compact"
                    class="mt-2"
                    data-test="organization-gcve-no-webs"
                >
                    {{ t('gna.organization.no_webs') }}
                </v-alert>
                <div
                    v-for="web in webs"
                    :key="web.id"
                    class="mt-3"
                    :data-test="'organization-gcve-web-' + web.id"
                >
                    <div class="text-body-2 font-weight-medium">
                        <bdi dir="auto">{{ web.name }}</bdi>
                        <span class="text-medium-emphasis ms-1">({{ web.hostname }})</span>
                    </div>
                    <v-table density="compact">
                        <tbody>
                            <tr
                                v-for="entry in web.urls"
                                :key="entry.key"
                            >
                                <td class="text-no-wrap">
                                    {{ t('gna.web.url_' + entry.key) }}
                                    <code
                                        v-if="entry.field"
                                        class="ms-1"
                                        >{{ entry.field }}</code
                                    >
                                </td>
                                <td class="text-break">
                                    <code>{{ entry.url }}</code>
                                    <div
                                        class="text-caption"
                                        :data-test="'organization-gcve-status-' + web.id + '-' + entry.key"
                                    >
                                        <template v-if="entry.field">
                                            <span
                                                v-if="entry.matches"
                                                class="text-success"
                                            >
                                                <v-icon size="small">mdi-check-circle</v-icon>
                                                {{ t('gna.organization.registered') }}
                                            </span>
                                            <span
                                                v-else-if="entry.registered"
                                                class="text-warning"
                                            >
                                                <v-icon size="small">mdi-alert</v-icon>
                                                {{ t('gna.organization.registered_differently') }}
                                                <code>{{ entry.registered }}</code>
                                            </span>
                                            <span
                                                v-else
                                                class="text-medium-emphasis"
                                                >{{ t('gna.organization.not_registered') }}</span
                                            >
                                        </template>
                                        <span
                                            v-else-if="resultOf(web.id, entry.key)"
                                            :class="resultOf(web.id, entry.key)?.ok ? 'text-success' : 'text-error'"
                                        >
                                            <v-icon size="small">{{
                                                resultOf(web.id, entry.key)?.ok ? 'mdi-check-circle' : 'mdi-close-circle'
                                            }}</v-icon>
                                            <bdi dir="auto">{{ resultOf(web.id, entry.key)?.detail }}</bdi>
                                        </span>
                                    </div>
                                </td>
                                <td class="text-end">
                                    <v-btn
                                        icon="mdi-content-copy"
                                        size="small"
                                        variant="text"
                                        :title="t('gna.web.copy_url')"
                                        :aria-label="t('gna.web.copy_url')"
                                        @click="copyUrl(entry.url)"
                                    />
                                </td>
                            </tr>
                        </tbody>
                    </v-table>
                </div>
            </section>

            <!-- The CNA account at MITRE's CVE Services: reserves CVE IDs and publishes CVE Records. -->
            <section data-test="organization-cve-services">
                <h3 class="text-subtitle-1 font-weight-medium d-flex align-center mb-1">
                    <v-icon
                        class="me-2"
                        size="small"
                        >mdi-shield-star-outline</v-icon
                    >
                    {{ t('gna.cve.account_title') }}
                </h3>
                <p class="text-body-2 text-medium-emphasis mb-4">{{ t('gna.cve.account_hint') }}</p>
                <v-row>
                    <v-col
                        cols="12"
                        md="4"
                    >
                        <v-select
                            v-model="form.cve.environment"
                            :items="environmentItems"
                            :label="t('gna.cve.environment')"
                            variant="outlined"
                            density="comfortable"
                            data-test="cve-environment"
                        />
                    </v-col>
                    <v-col
                        cols="12"
                        md="4"
                    >
                        <v-text-field
                            v-model="form.cve.short_name"
                            :label="t('gna.cve.short_name')"
                            :hint="t('gna.cve.short_name_hint')"
                            persistent-hint
                            :rules="[cveRequired]"
                            variant="outlined"
                            density="comfortable"
                            :spellcheck="false"
                            data-test="cve-short-name"
                        />
                    </v-col>
                    <v-col
                        cols="12"
                        md="4"
                    >
                        <v-text-field
                            v-model="form.cve.username"
                            :label="t('gna.cve.username')"
                            :rules="[cveRequired]"
                            variant="outlined"
                            density="comfortable"
                            autocomplete="off"
                            :spellcheck="false"
                            data-test="cve-username"
                        />
                    </v-col>
                    <v-col cols="12">
                        <v-text-field
                            v-model="form.cve.api_key"
                            type="password"
                            :label="t('gna.cve.api_key')"
                            :hint="account.has_secret ? t('gna.cve.api_key_stored') : ''"
                            persistent-hint
                            :rules="[keyRequired]"
                            variant="outlined"
                            density="comfortable"
                            autocomplete="new-password"
                            data-test="cve-api-key"
                        />
                    </v-col>
                </v-row>
                <div
                    v-if="account.url"
                    class="text-caption text-medium-emphasis mt-2"
                >
                    {{ t('gna.cve.calls_to', { url: account.url }) }}
                </div>
                <v-alert
                    v-if="testResult"
                    :type="testResult.ok ? 'success' : 'error'"
                    density="compact"
                    class="mt-4"
                    data-test="cve-test-result"
                >
                    <bdi dir="auto">{{ testResult.message }}</bdi>
                </v-alert>
                <div class="d-flex align-center flex-wrap ga-2 mt-4">
                    <span
                        v-if="account.updated_by"
                        class="text-caption text-medium-emphasis"
                    >
                        {{ t('routing.last_updated', { user: account.updated_by, at: formatTime(account.updated_at) }) }}
                    </span>
                    <v-spacer />
                    <v-btn
                        v-if="canUpdate"
                        variant="tonal"
                        prepend-icon="mdi-connection"
                        :loading="testing"
                        data-test="cve-test"
                        @click="test"
                    >
                        {{ t('gna.cve.test') }}
                    </v-btn>
                </div>
            </section>
        </v-form>
    </div>
</template>

<script setup lang="ts">
    import { computed, onMounted, ref } from 'vue'
    import { useI18n } from 'vue-i18n'
    import { useLocaleFormatters } from '@/composables/useLocaleFormatters'
    import { checkOrganizationGcve, getOrganizationGcve, saveOrganizationGcve, testOrganizationCveServices } from '@/api/config'

    /**
     * An organization's GCVE and CVE publishing: its GNA (the number gcve.eu allocated; its names
     * come from the gcve.eu GNA directory), the webs publishing its records with what to register
     * at gcve.eu, and its CVE Services account. The organization dialog saves it with the
     * organization (``save``), and asks ``dirty`` whether there is anything to save.
     */
    type Environment = 'production' | 'test'

    type CveServicesAccount = {
        environment: Environment
        short_name: string
        username: string
        has_secret: boolean
        org_uuid?: string | null
        complete?: boolean
        url?: string
        updated_by?: string | null
        updated_at?: string | null
    }

    type Gna = {
        gna_id: number
        short_name: string | null
        directory: { full_name?: string; [field: string]: unknown } | null
        directory_checked_at: string | null
        records_license: string
        conformance: Record<string, unknown> | null
        frozen: boolean
    }

    type WebUrl = { key: string; field: string | null; url: string; registered: string | null; matches: boolean }
    type Web = { id: number; name: string; hostname: string; enabled: boolean; urls: WebUrl[] }
    type Probe = { key: string; url: string; ok: boolean; status: number | null; detail: string }
    type WebCheck = { web_id: number; hostname: string; results: Probe[] }
    type Directory = {
        url: string | null
        enabled: boolean
        verified: boolean
        fetched_at: string | null
        warning: string | null
        error: string | null
    }

    type Settings = {
        organization_id: number
        gna: Gna | null
        cve_services: CveServicesAccount
        directory: Directory
        webs: Web[]
        checks?: WebCheck[]
    }

    type OrgInfo = { name?: string; short_name?: string; id_quota?: number | null; available?: number | null }
    type ApiError = { response?: { data?: { error?: string } } }

    const props = defineProps<{ organizationId: number; canUpdate: boolean }>()

    const { t } = useI18n()
    const { formatDateTime } = useLocaleFormatters()

    const DEFAULT_LICENSE = 'CC-BY-4.0'
    const GNA_ID_MAX = 65535

    const emptyAccount = (): CveServicesAccount => ({ environment: 'test', short_name: '', username: '', has_secret: false })

    type Form = {
        gna_id: string
        records_license: string
        conformance: string
        cve: { environment: Environment; short_name: string; username: string; api_key: string }
    }

    const formRef = ref<{ validate: () => Promise<{ valid: boolean }> } | null>(null)
    const loading = ref(false)
    const saving = ref(false)
    const checking = ref(false)
    const testing = ref(false)
    const errorMessage = ref('')
    const testResult = ref<{ ok: boolean; message: string } | null>(null)

    const stored = ref<Gna | null>(null)
    const account = ref<CveServicesAccount>(emptyAccount())
    const webs = ref<Web[]>([])
    const directory = ref<Directory | null>(null)
    const checks = ref<WebCheck[]>([])

    const formOf = (settings: Settings | null): Form => ({
        gna_id: settings?.gna ? String(settings.gna.gna_id) : '',
        records_license: settings?.gna?.records_license ?? '',
        conformance: settings?.gna?.conformance ? JSON.stringify(settings.gna.conformance, null, 2) : '',
        cve: {
            environment: settings?.cve_services?.environment ?? 'test',
            short_name: settings?.cve_services?.short_name ?? '',
            username: settings?.cve_services?.username ?? '',
            // Write-only: the stored key never comes back; empty keeps it.
            api_key: ''
        }
    })

    const form = ref<Form>(formOf(null))
    const baseline = ref(JSON.stringify(form.value))

    const dirty = computed(() => JSON.stringify(form.value) !== baseline.value)
    const frozen = computed(() => !!stored.value?.frozen)
    const hasNumber = computed(() => !!form.value.gna_id.trim())
    // The account is saved once any of it is filled in (or one is stored).
    const cveFilled = computed(
        () =>
            account.value.has_secret ||
            !!(form.value.cve.short_name.trim() || form.value.cve.username.trim() || form.value.cve.api_key.trim())
    )

    const environmentItems = computed(() => [
        { title: t('gna.cve.environment_test'), value: 'test' },
        { title: t('gna.cve.environment_production'), value: 'production' }
    ])

    function gnaIdRule(value: string): true | string {
        const text = (value ?? '').trim()
        if (!text) return true
        return (/^\d+$/.test(text) && Number(text) >= 1 && Number(text) <= GNA_ID_MAX) || t('gna.organization.gna_id_invalid')
    }

    function conformanceRule(value: string): true | string {
        const text = (value ?? '').trim()
        if (!text) return true
        try {
            const parsed = JSON.parse(text)
            return (parsed !== null && typeof parsed === 'object' && !Array.isArray(parsed)) || t('gna.organization.conformance_invalid')
        } catch {
            return t('gna.organization.conformance_invalid')
        }
    }

    const cveRequired = (value: string): true | string => !cveFilled.value || !!(value ?? '').trim() || t('error.required')
    // A key is needed until one is stored.
    const keyRequired = (value: string): true | string =>
        !cveFilled.value || account.value.has_secret || !!(value ?? '').trim() || t('error.required')

    const formatTime = (value?: string | null): string => (value ? formatDateTime(value) : '')
    const serverError = (error: unknown): string => (error as ApiError)?.response?.data?.error || t('common.error_saving')

    function resultOf(webId: number, key: string): Probe | undefined {
        return checks.value.find((check) => check.web_id === webId)?.results.find((result) => result.key === key)
    }

    function apply(settings: Settings): void {
        stored.value = settings.gna
        account.value = { ...emptyAccount(), ...(settings.cve_services ?? {}) }
        webs.value = settings.webs ?? []
        directory.value = settings.directory ?? null
        form.value = formOf(settings)
        baseline.value = JSON.stringify(form.value)
    }

    async function load(): Promise<void> {
        loading.value = true
        errorMessage.value = ''
        try {
            const response = (await getOrganizationGcve(props.organizationId)) as { data: Settings }
            apply(response.data)
        } catch (error) {
            errorMessage.value = serverError(error)
        } finally {
            loading.value = false
        }
    }

    const cvePayload = () => ({
        environment: form.value.cve.environment,
        short_name: form.value.cve.short_name.trim(),
        username: form.value.cve.username.trim(),
        ...(form.value.cve.api_key.trim() ? { api_key: form.value.cve.api_key.trim() } : {})
    })

    /** Saves the GNA and the account; resolves to false (saying why) when they were refused. */
    async function save(): Promise<boolean> {
        if (!dirty.value) return true
        if (!props.canUpdate) return false
        const { valid } = (await formRef.value?.validate()) ?? { valid: true }
        if (!valid) return false
        saving.value = true
        errorMessage.value = ''
        try {
            const conformance = form.value.conformance.trim()
            const response = (await saveOrganizationGcve(props.organizationId, {
                gna: {
                    gna_id: form.value.gna_id.trim() || null,
                    records_license: form.value.records_license.trim(),
                    conformance: conformance ? JSON.parse(conformance) : null
                },
                ...(cveFilled.value ? { cve_services: cvePayload() } : {})
            })) as { data: Settings }
            apply(response.data)
            window.dispatchEvent(new CustomEvent('notification', { detail: { type: 'success', loc: 'gna.organization.saved' } }))
            return true
        } catch (error) {
            errorMessage.value = serverError(error)
            return false
        } finally {
            saving.value = false
        }
    }

    // Asks the gcve.eu directory again and every endpoint of the webs; keeps what was typed.
    async function check(): Promise<void> {
        checking.value = true
        errorMessage.value = ''
        try {
            const response = (await checkOrganizationGcve(props.organizationId)) as { data: Settings }
            const typed = form.value
            const wasDirty = dirty.value
            apply(response.data)
            checks.value = response.data.checks ?? []
            if (wasDirty) form.value = typed
        } catch (error) {
            errorMessage.value = serverError(error)
        } finally {
            checking.value = false
        }
    }

    // With the form as it is, saved or not; an empty key uses the stored one.
    async function test(): Promise<void> {
        testing.value = true
        testResult.value = null
        try {
            const response = (await testOrganizationCveServices(props.organizationId, cvePayload())) as { data?: OrgInfo }
            const info = response.data ?? {}
            testResult.value = {
                ok: true,
                message: t('gna.cve.test_ok', {
                    name: info.name || info.short_name || form.value.cve.short_name,
                    available: info.available ?? '?',
                    quota: info.id_quota ?? '?'
                })
            }
        } catch (error) {
            testResult.value = { ok: false, message: serverError(error) }
        } finally {
            testing.value = false
        }
    }

    async function copyUrl(url: string): Promise<void> {
        try {
            await navigator.clipboard.writeText(url)
            window.dispatchEvent(new CustomEvent('notification', { detail: { type: 'success', loc: 'gna.web.url_copied' } }))
        } catch {
            window.dispatchEvent(new CustomEvent('notification', { detail: { type: 'error', loc: 'gna.web.copy_failed' } }))
        }
    }

    defineExpose({ dirty, save, saving })

    onMounted(load)
</script>

<style scoped>
    .conformance :deep(textarea) {
        font-family: monospace;
    }
</style>
