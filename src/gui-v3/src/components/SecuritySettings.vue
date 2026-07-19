<template>
    <div>
        <!-- TOTP -->
        <v-card
            variant="outlined"
            class="mb-4"
        >
            <v-card-title class="d-flex align-center">
                <v-icon class="mr-2">mdi-cellphone-key</v-icon>
                {{ t('security.totp_title') }}
                <v-spacer />
                <v-chip
                    size="small"
                    :color="totpEnabled ? 'success' : 'grey'"
                    variant="tonal"
                >
                    {{ totpEnabled ? t('security.enabled') : t('security.disabled') }}
                </v-chip>
            </v-card-title>
            <v-card-text>
                <div
                    v-if="!totpEnabled && !qrDataUrl"
                    class="d-flex align-center"
                >
                    <span class="text-body-2 mr-4">{{ t('security.totp_hint') }}</span>
                    <v-spacer />
                    <v-btn
                        color="primary"
                        variant="flat"
                        prepend-icon="mdi-qrcode"
                        @click="startTotpEnrollment"
                    >
                        {{ t('security.totp_enable') }}
                    </v-btn>
                </div>

                <!-- Enrollment in progress -->
                <div
                    v-if="qrDataUrl"
                    class="text-center"
                >
                    <p class="text-body-2 mb-2">{{ t('security.totp_scan') }}</p>
                    <img
                        :src="qrDataUrl"
                        alt="TOTP QR code"
                        class="qr-image mb-3"
                    />
                    <v-text-field
                        v-model="totpCode"
                        :label="t('security.totp_code')"
                        variant="outlined"
                        density="comfortable"
                        autocomplete="one-time-code"
                        inputmode="numeric"
                        max-width="300"
                        class="mx-auto"
                    />
                    <v-btn
                        color="primary"
                        variant="flat"
                        prepend-icon="mdi-check"
                        @click="confirmTotpEnrollment"
                    >
                        {{ t('security.totp_activate') }}
                    </v-btn>
                </div>

                <!-- Enabled: allow disable with code -->
                <div
                    v-if="totpEnabled"
                    class="d-flex align-center"
                >
                    <v-text-field
                        v-model="totpCode"
                        :label="t('security.totp_code')"
                        variant="outlined"
                        density="compact"
                        autocomplete="one-time-code"
                        inputmode="numeric"
                        hide-details
                        class="mr-4"
                        style="max-width: 220px"
                    />
                    <v-btn
                        color="warning"
                        variant="outlined"
                        prepend-icon="mdi-cellphone-off"
                        @click="disableTotp"
                    >
                        {{ t('security.totp_disable') }}
                    </v-btn>
                </div>

                <v-alert
                    v-if="totpError"
                    type="error"
                    density="compact"
                    class="mt-3"
                >
                    {{ totpError }}
                </v-alert>
            </v-card-text>
        </v-card>

        <!-- Passkeys -->
        <v-card variant="outlined">
            <v-card-title class="d-flex align-center">
                <v-icon class="mr-2">mdi-fingerprint</v-icon>
                {{ t('security.passkeys_title') }}
                <v-spacer />
                <AddNewButton
                    :label="t('security.passkey_add')"
                    @click="addPasskey"
                />
            </v-card-title>
            <v-card-text>
                <v-table
                    v-if="passkeys.length > 0"
                    density="comfortable"
                >
                    <thead>
                        <tr>
                            <th>{{ t('security.passkey_name') }}</th>
                            <th>{{ t('security.passkey_created') }}</th>
                            <th>{{ t('security.passkey_last_used') }}</th>
                            <th class="text-right">{{ t('settings.actions') }}</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr
                            v-for="passkey in passkeys"
                            :key="passkey.id"
                        >
                            <td>{{ passkey.name }}</td>
                            <td>{{ passkey.created_at || '-' }}</td>
                            <td>{{ passkey.last_used_at || '-' }}</td>
                            <td class="text-right">
                                <v-btn
                                    icon="mdi-pencil"
                                    size="x-small"
                                    variant="text"
                                    @click="startRename(passkey)"
                                />
                                <v-btn
                                    icon="mdi-delete"
                                    size="x-small"
                                    variant="text"
                                    color="error"
                                    @click="removePasskey(passkey)"
                                />
                            </td>
                        </tr>
                    </tbody>
                </v-table>
                <p
                    v-else
                    class="text-body-2 text-medium-emphasis"
                >
                    {{ t('security.no_passkeys') }}
                </p>

                <v-alert
                    v-if="passkeyError"
                    type="error"
                    density="compact"
                    class="mt-3"
                >
                    {{ passkeyError }}
                </v-alert>
            </v-card-text>
        </v-card>

        <!-- Name prompt for new/renamed passkey -->
        <v-dialog
            v-model="nameDialog"
            max-width="400"
        >
            <v-card>
                <v-card-title>{{ t('security.passkey_name') }}</v-card-title>
                <v-card-text>
                    <v-text-field
                        v-model="passkeyName"
                        :label="t('security.passkey_name')"
                        variant="outlined"
                        density="comfortable"
                        autofocus
                    />
                </v-card-text>
                <v-card-actions>
                    <v-spacer />
                    <v-btn
                        variant="text"
                        @click="nameDialog = false"
                    >
                        {{ t('common.cancel') }}
                    </v-btn>
                    <v-btn
                        color="primary"
                        variant="flat"
                        @click="confirmName"
                    >
                        {{ t('common.save') }}
                    </v-btn>
                </v-card-actions>
            </v-card>
        </v-dialog>
    </div>
</template>

<script setup lang="ts">
    import { ref, computed, watch } from 'vue'
    import { useI18n } from 'vue-i18n'
    import QRCode from 'qrcode'
    import { startRegistration } from '@simplewebauthn/browser'
    import AddNewButton from '@/components/common/buttons/AddNewButton.vue'
    import {
        getMyTotp,
        beginMyTotpEnrollment,
        confirmMyTotpEnrollment,
        disableMyTotp,
        getMyPasskeys,
        beginPasskeyRegistration,
        finishPasskeyRegistration,
        renamePasskey,
        deletePasskey
    } from '@/api/user'

    type Passkey = {
        id: number
        name: string
        created_at?: string | null
        last_used_at?: string | null
    }

    const props = withDefaults(
        defineProps<{
            // When this prop changes, the component reloads its data. Used by
            // the parent tab host to trigger a refresh when the Security tab
            // becomes visible (mirrors the open/close watcher of the previous
            // standalone-dialog design).
            loadTrigger?: number
        }>(),
        {
            loadTrigger: 0
        }
    )

    const { t } = useI18n()

    const totpEnabled = ref(false)
    const totpCode = ref('')
    const qrDataUrl = ref('')
    const totpError = ref('')

    const passkeys = ref<Passkey[]>([])
    const passkeyError = ref('')
    const nameDialog = ref(false)
    const passkeyName = ref('')
    // null while registering a new passkey; set when renaming an existing one
    const renameTarget = ref<Passkey | null>(null)

    const extractError = (error: unknown): string => {
        const data = (error as { response?: { data?: { error?: string } } })?.response?.data
        return data?.error || t('security.error')
    }

    const loadData = async (): Promise<void> => {
        totpError.value = ''
        passkeyError.value = ''
        try {
            const totpResponse = (await getMyTotp()) as { data: { enabled: boolean } }
            totpEnabled.value = totpResponse.data.enabled
        } catch (error) {
            console.error('Error loading TOTP status:', error)
        }
        try {
            const passkeysResponse = (await getMyPasskeys()) as { data: { items: Passkey[] } }
            passkeys.value = passkeysResponse.data.items || []
        } catch (error) {
            console.error('Error loading passkeys:', error)
        }
    }

    // Reload data whenever the parent toggles loadTrigger (e.g. when the
    // Security tab becomes visible). Also reset transient enrollment state.
    watch(
        () => props.loadTrigger,
        () => {
            qrDataUrl.value = ''
            totpCode.value = ''
            loadData()
        }
    )

    // Initial load on mount so the tab is populated even before the user
    // first switches to it (matches the previous dialog-open behavior).
    loadData()

    const startTotpEnrollment = async (): Promise<void> => {
        totpError.value = ''
        try {
            const response = (await beginMyTotpEnrollment()) as { data: { otpauth_uri: string } }
            qrDataUrl.value = await QRCode.toDataURL(response.data.otpauth_uri)
            totpCode.value = ''
        } catch (error) {
            totpError.value = extractError(error)
        }
    }

    const confirmTotpEnrollment = async (): Promise<void> => {
        totpError.value = ''
        try {
            await confirmMyTotpEnrollment(totpCode.value)
            totpEnabled.value = true
            qrDataUrl.value = ''
            totpCode.value = ''
            window.dispatchEvent(new CustomEvent('notification', { detail: { type: 'success', loc: 'security.totp_enabled' } }))
        } catch (error) {
            totpError.value = extractError(error)
        }
    }

    const disableTotp = async (): Promise<void> => {
        totpError.value = ''
        try {
            await disableMyTotp(totpCode.value)
            totpEnabled.value = false
            totpCode.value = ''
            window.dispatchEvent(new CustomEvent('notification', { detail: { type: 'success', loc: 'security.totp_disabled' } }))
        } catch (error) {
            totpError.value = extractError(error)
        }
    }

    const addPasskey = (): void => {
        renameTarget.value = null
        passkeyName.value = ''
        nameDialog.value = true
    }

    const startRename = (passkey: Passkey): void => {
        renameTarget.value = passkey
        passkeyName.value = passkey.name
        nameDialog.value = true
    }

    const confirmName = async (): Promise<void> => {
        nameDialog.value = false
        if (renameTarget.value) {
            try {
                await renamePasskey(renameTarget.value.id, passkeyName.value)
                await loadData()
            } catch (error) {
                passkeyError.value = extractError(error)
            }
            return
        }
        await registerPasskey(passkeyName.value)
    }

    const registerPasskey = async (name: string): Promise<void> => {
        passkeyError.value = ''
        try {
            const beginResponse = (await beginPasskeyRegistration()) as { data: { options: never; challenge_id: string } }
            const credential = await startRegistration({ optionsJSON: beginResponse.data.options })
            await finishPasskeyRegistration(beginResponse.data.challenge_id, credential, name || 'Passkey')
            window.dispatchEvent(new CustomEvent('notification', { detail: { type: 'success', loc: 'security.passkey_added' } }))
            await loadData()
        } catch (error) {
            passkeyError.value = extractError(error)
        }
    }

    const removePasskey = async (passkey: Passkey): Promise<void> => {
        passkeyError.value = ''
        try {
            await deletePasskey(passkey.id)
            await loadData()
        } catch (error) {
            passkeyError.value = extractError(error)
        }
    }
</script>

<style scoped>
    .qr-image {
        width: 200px;
        height: 200px;
        border-radius: 6px;
        background: white;
        padding: 8px;
    }
</style>
