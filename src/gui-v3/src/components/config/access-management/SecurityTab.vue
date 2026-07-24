<template>
    <v-container fluid>
        <v-form
            ref="formRef"
            @submit.prevent="save"
        >
            <v-card class="mb-4">
                <v-card-title class="d-flex align-center">
                    <v-icon class="mr-2">mdi-shield-lock</v-icon>
                    {{ t('access_management.security.mfa_title') }}
                </v-card-title>

                <v-card-subtitle class="pb-2">
                    {{ t('access_management.security.mfa_description') }}
                </v-card-subtitle>

                <v-card-text>
                    <v-switch
                        v-model="settings.require_mfa"
                        :label="t('access_management.security.require_mfa')"
                        :hint="t('access_management.security.require_mfa_hint')"
                        persistent-hint
                        color="primary"
                        :disabled="!canUpdate || saving"
                        data-test="security-require-mfa"
                    />
                </v-card-text>
            </v-card>

            <v-card>
                <v-card-title class="d-flex align-center">
                    <v-icon class="mr-2">mdi-fingerprint</v-icon>
                    {{ t('access_management.security.passkeys_title') }}
                </v-card-title>

                <v-card-subtitle class="pb-2">
                    {{ t('access_management.security.passkeys_description') }}
                </v-card-subtitle>

                <v-card-text>
                    <v-row>
                        <v-col cols="12">
                            <v-switch
                                v-model="settings.passkey_enabled"
                                :label="t('access_management.security.passkey_enabled')"
                                :hint="t('access_management.security.passkey_enabled_hint')"
                                persistent-hint
                                color="primary"
                                :disabled="!canUpdate || saving"
                            />
                        </v-col>
                        <v-col cols="12">
                            <v-switch
                                v-model="settings.passkey_second_factor"
                                :label="t('access_management.security.passkey_second_factor')"
                                :hint="t('access_management.security.passkey_second_factor_hint')"
                                persistent-hint
                                color="primary"
                                :disabled="!canUpdate || saving || !settings.passkey_enabled"
                                data-test="security-passkey-second-factor"
                            />
                        </v-col>
                    </v-row>

                    <v-row>
                        <v-col
                            cols="12"
                            md="4"
                        >
                            <v-text-field
                                v-model="settings.rp_id"
                                :label="t('access_management.security.rp_id')"
                                variant="outlined"
                                density="comfortable"
                                :placeholder="suggestedRpId"
                                :hint="t('access_management.security.rp_id_hint', { host: suggestedRpId })"
                                persistent-hint
                                :rules="rpIdRules"
                                :disabled="!canUpdate || saving"
                            />
                        </v-col>
                        <v-col
                            cols="12"
                            md="4"
                        >
                            <v-text-field
                                v-model="settings.rp_name"
                                :label="t('access_management.security.rp_name')"
                                variant="outlined"
                                density="comfortable"
                                placeholder="Taranis NG"
                                :hint="t('access_management.security.rp_name_hint')"
                                persistent-hint
                                :disabled="!canUpdate || saving"
                            />
                        </v-col>
                        <v-col
                            cols="12"
                            md="4"
                        >
                            <v-text-field
                                v-model="settings.origins"
                                :label="t('access_management.security.origins')"
                                variant="outlined"
                                density="comfortable"
                                :placeholder="suggestedOrigin"
                                :hint="t('access_management.security.origins_hint')"
                                persistent-hint
                                :rules="originsRules"
                                :disabled="!canUpdate || saving"
                            />
                        </v-col>
                    </v-row>

                    <v-alert
                        type="info"
                        variant="tonal"
                        density="compact"
                        class="mt-4"
                    >
                        {{ t('access_management.security.secure_context_hint') }}
                    </v-alert>

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
                            {{ t('access_management.security.last_updated', { user: settings.updated_by, at: settings.updated_at }) }}
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
    import { getSecuritySettings, updateSecuritySettings } from '@/api/config'

    type SecuritySettingsItem = {
        require_mfa: boolean
        passkey_enabled: boolean
        passkey_second_factor: boolean
        rp_id: string
        rp_name: string
        origins: string
        updated_by?: string
        updated_at?: string
    }

    type FormValidationResult = {
        valid: boolean
    }

    const { t } = useI18n()
    const { checkPermission } = useAuth()

    const formRef = ref<any>(null)
    const saving = ref(false)
    const errorMessage = ref('')

    const settings = ref<SecuritySettingsItem>({
        require_mfa: false,
        passkey_enabled: false,
        passkey_second_factor: true,
        rp_id: '',
        rp_name: '',
        origins: ''
    })

    const canUpdate = computed(() => checkPermission('CONFIG_AUTH_PROVIDER_UPDATE'))

    // The relying-party ID must be the site's domain, and the origin must be the
    // exact URL the browser is on - so the current location is the right suggestion.
    const suggestedRpId = computed(() => window.location.hostname)
    const suggestedOrigin = computed(() => window.location.origin)

    // Only enforced when passkeys are switched on: an incomplete draft may be saved
    // while the feature is off, and the backend applies the same rule.
    const rpIdRules = computed(() => [(v: string) => !settings.value.passkey_enabled || !!v || t('error.required')])

    const originsRules = computed(() => [
        (v: string) => !settings.value.passkey_enabled || !!v || t('error.required'),
        (v: string) =>
            !v ||
            v
                .split(',')
                .map((origin) => origin.trim())
                .filter((origin) => !!origin)
                .every((origin) => /^https?:\/\/[^/]+$/.test(origin)) ||
            t('access_management.security.origins_invalid')
    ])

    const loadData = async (): Promise<void> => {
        try {
            const response = (await getSecuritySettings()) as { data: SecuritySettingsItem }
            settings.value = { ...settings.value, ...response.data }
        } catch (error) {
            console.error('Error loading security settings:', error)
        }
    }

    const save = async (): Promise<void> => {
        errorMessage.value = ''
        const { valid } = (await formRef.value.validate()) as FormValidationResult
        if (!valid) {
            return
        }

        saving.value = true
        try {
            const response = (await updateSecuritySettings(settings.value)) as { data: SecuritySettingsItem }
            settings.value = { ...settings.value, ...response.data }
            window.dispatchEvent(new CustomEvent('notification', { detail: { type: 'success', loc: 'common.updated_successfully' } }))
        } catch (error) {
            const data = (error as { response?: { data?: { error?: string } } })?.response?.data
            errorMessage.value = data?.error || t('access_management.security.error')
            window.dispatchEvent(new CustomEvent('notification', { detail: { type: 'error', loc: 'common.error_saving' } }))
        } finally {
            saving.value = false
        }
    }

    onMounted(() => {
        loadData()
    })
</script>
