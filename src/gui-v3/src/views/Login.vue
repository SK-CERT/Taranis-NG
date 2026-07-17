<template>
    <div
        v-if="!authStore.hasExternalLoginUrl"
        class="login-screen bg-background"
    >
        <!-- Logo -->
        <div class="logo-container pb-3">
            <img
                :src="isDark ? darkLogo : lightLogo"
                alt="Taranis NG"
                class="login-logo"
            />
        </div>

        <!-- Credentials step -->
        <v-form
            v-if="step === 'credentials'"
            id="login-form"
            class="login-form bg-surface border rounded-lg pa-6"
            @submit.prevent="handleFormSubmit"
        >
            <div
                v-if="hasFormMethods"
                class="form-fields"
            >
                <v-select
                    v-if="formMethods.length > 1"
                    v-model="selectedProviderId"
                    :items="formMethods"
                    item-title="name"
                    item-value="id"
                    data-test="login-provider"
                    :label="t('login.provider')"
                    prepend-icon="mdi-domain"
                    variant="outlined"
                    density="comfortable"
                    class="login-field"
                />

                <v-text-field
                    v-model="username"
                    name="username"
                    data-test="login-username"
                    :placeholder="t('login.username')"
                    prepend-icon="mdi-account"
                    variant="outlined"
                    density="comfortable"
                    :error="!!usernameError"
                    :error-messages="usernameError ? [usernameError] : []"
                    class="login-field"
                    @blur="validateUsername"
                />

                <v-text-field
                    v-model="password"
                    name="password"
                    data-test="login-password"
                    :placeholder="t('login.password')"
                    prepend-icon="mdi-lock"
                    :type="showPassword ? 'text' : 'password'"
                    variant="outlined"
                    density="comfortable"
                    :error="!!passwordError"
                    :error-messages="passwordError ? [passwordError] : []"
                    class="login-field"
                    @blur="validatePassword"
                >
                    <template #append-inner>
                        <v-icon
                            class="password-toggle"
                            :icon="showPassword ? 'mdi-eye-off' : 'mdi-eye'"
                            @click="showPassword = !showPassword"
                        />
                    </template>
                </v-text-field>
            </div>

            <div
                v-if="hasFormMethods"
                class="form-actions"
            >
                <v-btn
                    type="submit"
                    data-test="login-submit"
                    color="primary"
                    prepend-icon="mdi-login-variant"
                    size="large"
                >
                    {{ t('login.login') }}
                </v-btn>
            </div>

            <!-- Alternative sign-in methods -->
            <template v-if="passkeyEnabled || redirectMethods.length > 0">
                <v-divider v-if="hasFormMethods" />

                <div class="form-actions flex-column">
                    <v-btn
                        v-if="passkeyEnabled"
                        data-test="login-passkey"
                        prepend-icon="mdi-fingerprint"
                        size="large"
                        variant="outlined"
                        block
                        @click="handlePasskeyLogin"
                    >
                        {{ t('login.passkey_sign_in') }}
                    </v-btn>

                    <v-btn
                        v-for="method in redirectMethods"
                        :key="method.id"
                        :data-test="`login-sso-${method.id}`"
                        prepend-icon="mdi-open-in-new"
                        size="large"
                        variant="outlined"
                        block
                        @click="handleRedirectLogin(method)"
                    >
                        {{ t('login.sign_in_with', { name: method.name }) }}
                    </v-btn>
                </div>
            </template>
        </v-form>

        <!-- MFA step -->
        <v-form
            v-else-if="step === 'mfa'"
            class="login-form bg-surface border rounded-lg pa-6"
            @submit.prevent="handleTotpSubmit"
        >
            <div class="text-subtitle-1 text-center">{{ t('login.mfa_title') }}</div>

            <div
                v-if="mfaMethods.includes('totp')"
                class="form-fields"
            >
                <v-text-field
                    v-model="totpCode"
                    name="totp-code"
                    data-test="login-totp"
                    :placeholder="t('login.mfa_code')"
                    prepend-icon="mdi-cellphone-key"
                    variant="outlined"
                    density="comfortable"
                    autocomplete="one-time-code"
                    inputmode="numeric"
                    autofocus
                    class="login-field"
                />
            </div>

            <div class="form-actions flex-column">
                <v-btn
                    v-if="mfaMethods.includes('totp')"
                    type="submit"
                    data-test="login-totp-submit"
                    color="primary"
                    prepend-icon="mdi-check"
                    size="large"
                >
                    {{ t('login.mfa_verify') }}
                </v-btn>
                <v-btn
                    v-if="mfaMethods.includes('passkey')"
                    prepend-icon="mdi-fingerprint"
                    size="large"
                    variant="outlined"
                    block
                    @click="handleMfaPasskey"
                >
                    {{ t('login.mfa_use_passkey') }}
                </v-btn>
                <v-btn
                    variant="text"
                    size="small"
                    @click="backToCredentials"
                >
                    {{ t('login.back') }}
                </v-btn>
            </div>
        </v-form>

        <!-- Forced enrollment step: set up a second factor before the login completes.
             A passkey is offered alongside TOTP whenever the site accepts one. -->
        <v-form
            v-else-if="step === 'enroll'"
            class="login-form bg-surface border rounded-lg pa-6"
            @submit.prevent="handleEnrollSubmit"
        >
            <div class="text-subtitle-1 text-center">{{ t('login.enroll_title') }}</div>
            <div class="text-body-2 text-center">{{ t('login.enroll_hint') }}</div>

            <div
                v-if="qrDataUrl"
                class="qr-container"
            >
                <img
                    :src="qrDataUrl"
                    alt="TOTP QR code"
                    class="qr-image"
                />
            </div>

            <div class="form-fields">
                <v-text-field
                    v-model="totpCode"
                    name="totp-enroll-code"
                    data-test="login-enroll-code"
                    :placeholder="t('login.mfa_code')"
                    prepend-icon="mdi-cellphone-key"
                    variant="outlined"
                    density="comfortable"
                    autocomplete="one-time-code"
                    inputmode="numeric"
                    class="login-field"
                />
            </div>

            <div class="form-actions flex-column">
                <v-btn
                    type="submit"
                    color="primary"
                    prepend-icon="mdi-check"
                    size="large"
                >
                    {{ t('login.enroll_activate') }}
                </v-btn>
                <v-btn
                    v-if="mfaMethods.includes('passkey')"
                    data-test="login-enroll-passkey"
                    prepend-icon="mdi-fingerprint"
                    size="large"
                    variant="outlined"
                    block
                    @click="handleEnrollPasskey"
                >
                    {{ t('login.enroll_use_passkey') }}
                </v-btn>
                <v-btn
                    variant="text"
                    size="small"
                    @click="backToCredentials"
                >
                    {{ t('login.back') }}
                </v-btn>
            </div>
        </v-form>

        <!-- Login alert (error for genuine auth faults, warning for expected
             policy rejections like disabled / pending-approval accounts). -->
        <v-alert
            v-if="showLoginError"
            data-test="login-error"
            :type="alertType"
            density="compact"
            :class="alertType === 'error' ? 'error-alert' : 'warning-alert'"
            closable
            @click:close="showLoginError = false"
        >
            {{ errorMessage }}
        </v-alert>
    </div>
</template>

<script setup lang="ts">
    import { ref, computed, onMounted } from 'vue'
    import { useRouter, useRoute } from 'vue-router'
    import { useI18n } from 'vue-i18n'
    import { useTheme } from 'vuetify'
    import QRCode from 'qrcode'
    import { startAuthentication, startRegistration } from '@simplewebauthn/browser'
    import { useAuthStore } from '@/stores/auth'
    import { useAuth } from '@/composables/useAuth'
    import { useProviderDisplay } from '@/composables/useProviderDisplay'
    import {
        mfaTotp,
        mfaTotpEnroll,
        mfaWebauthnEnroll,
        mfaWebauthnBegin,
        mfaWebauthnFinish,
        passkeyLoginBegin,
        passkeyLoginFinish
    } from '@/api/auth'
    import type { LoginErrorResponse, LoginMethod } from '@/types/auth'
    import lightLogo from '@/assets/taranis-logo-nav.svg'
    import darkLogo from '@/assets/taranis-logo-nav-dark.svg'

    // Reactive theme detection — follows the app's DARK_THEME preference, not
    // just the OS preference at mount time (which doesn't track Vuetify theme
    // changes from Settings → General → Dark theme).
    // NOTE: useTheme() must be called at the top of setup, NOT inside a
    // computed() getter — the getter runs lazily (e.g. when an async store
    // update triggers re-computation), where getCurrentInstance() is null, and
    // Vuetify's useTheme() asserts its presence ("useTheme must be called from
    // inside a setup function").
    const { global: themeGlobal } = useTheme()
    const isDark = computed(() => themeGlobal.current.value.dark)
    const router = useRouter()
    const route = useRoute()
    const { t } = useI18n()
    const authStore = useAuthStore()
    const { isAuthenticated } = useAuth()
    const { providerName } = useProviderDisplay()

    type LoginStep = 'credentials' | 'mfa' | 'enroll'

    // Form data
    const step = ref<LoginStep>('credentials')
    const username = ref<string>('')
    const password = ref<string>('')
    const showLoginError = ref(false)
    const showPassword = ref(false)
    const errorKey = ref('login.error')
    // 'error' (red) for genuine auth faults (auth_failed, totp_invalid);
    // 'warning' (orange) for expected security-policy rejections
    // (account_disabled, pending_approval, account_not_linked, ...).
    const alertType = ref<'error' | 'warning'>('error')
    const selectedProviderId = ref<number | null>(null)

    // MFA state
    const mfaToken = ref('')
    const mfaMethods = ref<string[]>([])
    const enrollToken = ref('')
    const totpCode = ref('')
    const qrDataUrl = ref('')

    // Validation error states
    const usernameError = ref<string | null>(null)
    const passwordError = ref<string | null>(null)

    // The local provider's stored name is English; show every method through the
    // display helper so the built-in local method is localized on the login page too.
    const formMethods = computed(() =>
        authStore.loginMethods
            .filter((method: LoginMethod) => method.form)
            .map((method: LoginMethod) => ({ ...method, name: providerName(method) }))
    )
    const redirectMethods = computed(() =>
        authStore.loginMethods
            .filter((method: LoginMethod) => !!method.login_url)
            .map((method: LoginMethod) => ({ ...method, name: providerName(method) }))
    )
    // Passkeys are a site-wide capability (a security setting), not a provider.
    const passkeyEnabled = computed(() => authStore.passkeyEnabled)
    // Fall back to a plain credentials form when the methods endpoint is unavailable (older backend)
    const hasFormMethods = computed(() => formMethods.value.length > 0 || authStore.loginMethods.length === 0)

    const errorMessage = computed(() => t(errorKey.value))

    // Backend codes that represent expected security-policy rejections, not
    // authentication faults. The IdP authn itself succeeded (or it's a local
    // provider deliberately refusing a known user); the system is working as
    // designed and denying entry, so the login alert is shown as a warning.
    const WARNING_CODES = new Set([
        'pending_approval',
        'account_disabled',
        'username_collision',
        'account_not_linked',
        'domain_not_allowed',
        'auth_cancelled'
    ])

    // Maps backend error codes (POST payload code / redirect login_error param) to i18n keys
    const errorKeyForCode = (code: string): string => {
        const keys: Record<string, string> = {
            pending_approval: 'login.pending_approval',
            account_disabled: 'login.account_disabled',
            username_collision: 'login.username_collision',
            account_not_linked: 'login.account_not_linked',
            domain_not_allowed: 'login.domain_not_allowed',
            auth_cancelled: 'login.auth_cancelled',
            totp_invalid: 'login.totp_invalid'
        }
        return keys[code.toLowerCase()] || 'login.error'
    }

    const showError = (code?: string): void => {
        const normalized = code?.toLowerCase() || ''
        errorKey.value = code ? errorKeyForCode(code) : 'login.error'
        alertType.value = normalized && WARNING_CODES.has(normalized) ? 'warning' : 'error'
        showLoginError.value = true
    }

    // Validation functions
    const validateUsername = (): boolean => {
        if (!username.value) {
            usernameError.value = t('validations.custom.username.required')
            return false
        }
        usernameError.value = null
        return true
    }

    const validatePassword = (): boolean => {
        if (!password.value) {
            passwordError.value = t('validations.custom.password.required')
            return false
        }
        passwordError.value = null
        return true
    }

    const resetForm = (): void => {
        username.value = ''
        password.value = ''
        usernameError.value = null
        passwordError.value = null
    }

    const backToCredentials = (): void => {
        step.value = 'credentials'
        mfaToken.value = ''
        enrollToken.value = ''
        totpCode.value = ''
        qrDataUrl.value = ''
        showLoginError.value = false
    }

    const redirectQuery = (): string => {
        const queryRedirect = route.query['redirect']
        return typeof queryRedirect === 'string' ? queryRedirect : Array.isArray(queryRedirect) ? (queryRedirect[0] ?? '') : ''
    }

    const redirectAfterLogin = (): void => {
        router.push(redirectQuery() || '/')
    }

    const finishLoginWithToken = (accessToken: string): void => {
        authStore.finishLogin(accessToken)
        showLoginError.value = false
        redirectAfterLogin()
    }

    const extractErrorData = (error: unknown): LoginErrorResponse => {
        const response = (error as { response?: { data?: LoginErrorResponse } })?.response
        return response?.data || {}
    }

    /**
     * Handle credentials form submission with validation
     */
    const handleFormSubmit = async (): Promise<void> => {
        const usernameValid = validateUsername()
        const passwordValid = validatePassword()

        if (!(usernameValid && passwordValid && username.value && password.value)) {
            return
        }
        showLoginError.value = false

        try {
            if (authStore.hasExternalLoginUrl) {
                // DEPRECATED external authentication via env URL (OAuth/Keycloak)
                await authStore.login({
                    params: {
                        code: route.query['code'],
                        session_state: route.query['session_state']
                    },
                    method: 'get'
                })
            } else {
                await authStore.login({
                    username: username.value,
                    password: password.value,
                    provider_id: selectedProviderId.value
                })
            }

            if (isAuthenticated()) {
                showLoginError.value = false
                redirectAfterLogin()
            } else {
                validationFailed()
            }
        } catch (error) {
            const data = extractErrorData(error)
            if (data.code === 'MFA_REQUIRED' && data.mfa_token) {
                mfaToken.value = data.mfa_token
                mfaMethods.value = data.methods || ['totp']
                totpCode.value = ''
                step.value = 'mfa'
                return
            }
            if (data.code === 'MFA_ENROLLMENT_REQUIRED' && data.enroll_token) {
                enrollToken.value = data.enroll_token
                // which factors this installation lets the user set up
                mfaMethods.value = data.methods || ['totp']
                await beginTotpEnrollment()
                return
            }
            if (data.code) {
                showError(data.code)
                return
            }
            console.error('[Login] Authentication error:', error)
            validationFailed()
        }
    }

    /**
     * Handle validation failure
     */
    const validationFailed = (): void => {
        if (authStore.hasExternalLogoutUrl) {
            // Redirect to external logout (no gotoUrl)
            window.location.href = authStore.getLogoutURL
        } else {
            showError()
            resetForm()
        }
    }

    const handleTotpSubmit = async (): Promise<void> => {
        if (!totpCode.value) {
            return
        }
        try {
            const response = (await mfaTotp(mfaToken.value, totpCode.value)) as { data: { access_token: string } }
            finishLoginWithToken(response.data.access_token)
        } catch (error) {
            const data = extractErrorData(error)
            showError(data.code || 'totp_invalid')
            totpCode.value = ''
        }
    }

    const beginTotpEnrollment = async (): Promise<void> => {
        try {
            const response = (await mfaTotpEnroll(enrollToken.value)) as { data: { otpauth_uri: string } }
            qrDataUrl.value = await QRCode.toDataURL(response.data.otpauth_uri)
            totpCode.value = ''
            step.value = 'enroll'
        } catch (error) {
            console.error('[Login] TOTP enrollment error:', error)
            showError()
        }
    }

    const handleEnrollSubmit = async (): Promise<void> => {
        if (!totpCode.value) {
            return
        }
        try {
            const response = (await mfaTotpEnroll(enrollToken.value, totpCode.value)) as { data: { access_token: string } }
            finishLoginWithToken(response.data.access_token)
        } catch (error) {
            const data = extractErrorData(error)
            showError(data.code || 'totp_invalid')
            totpCode.value = ''
        }
    }

    /**
     * Satisfy a forced enrollment by registering a passkey instead of TOTP.
     *
     * Registering the passkey *is* the second factor - the authenticator has just
     * verified the user - so the backend answers with the access token and the login
     * completes here, with no further code to type.
     */
    const handleEnrollPasskey = async (): Promise<void> => {
        showLoginError.value = false
        try {
            const beginResponse = (await mfaWebauthnEnroll(enrollToken.value)) as { data: { options: never; challenge_id: string } }
            const credential = await startRegistration({ optionsJSON: beginResponse.data.options })
            const finishResponse = (await mfaWebauthnEnroll(
                enrollToken.value,
                beginResponse.data.challenge_id,
                credential,
                t('login.enroll_passkey_name')
            )) as { data: { access_token: string } }
            finishLoginWithToken(finishResponse.data.access_token)
        } catch (error) {
            console.error('[Login] Passkey enrollment error:', error)
            showError(extractErrorData(error).code)
        }
    }

    const handleMfaPasskey = async (): Promise<void> => {
        try {
            const beginResponse = (await mfaWebauthnBegin(mfaToken.value)) as { data: { options: never; challenge_id: string } }
            const assertion = await startAuthentication({ optionsJSON: beginResponse.data.options })
            const finishResponse = (await mfaWebauthnFinish(mfaToken.value, beginResponse.data.challenge_id, assertion)) as {
                data: { access_token: string }
            }
            finishLoginWithToken(finishResponse.data.access_token)
        } catch (error) {
            console.error('[Login] Passkey MFA error:', error)
            showError(extractErrorData(error).code)
        }
    }

    const handlePasskeyLogin = async (): Promise<void> => {
        showLoginError.value = false
        try {
            const beginResponse = (await passkeyLoginBegin()) as { data: { options: never; challenge_id: string } }
            const assertion = await startAuthentication({ optionsJSON: beginResponse.data.options })
            const finishResponse = (await passkeyLoginFinish(beginResponse.data.challenge_id, assertion)) as {
                data: { access_token: string }
            }
            finishLoginWithToken(finishResponse.data.access_token)
        } catch (error) {
            console.error('[Login] Passkey login error:', error)
            showError(extractErrorData(error).code)
        }
    }

    const handleRedirectLogin = (method: LoginMethod): void => {
        if (!method.login_url) {
            return
        }
        // login_url is an absolute path on the core API host
        const apiBase: string = import.meta.env.VITE_APP_TARANIS_NG_CORE_API || '/api/v1'
        const apiRoot = apiBase.replace(/\/api\/v1\/?$/, '')
        const base: string = import.meta.env.BASE_URL || '/'
        // Send the IdP round-trip straight back into the app, not to this page: the
        // core redirects to gotoUrl with the JWT in a cookie, main.ts adopts it before
        // the router's first navigation, and the user never sees the login screen
        // again. On failure the core appends ?login_error= to the same URL, and the
        // auth guard forwards that back here.
        const gotoUrl = window.location.origin + base.replace(/\/$/, '') + (redirectQuery() || '/dashboard')
        window.location.href = apiRoot + method.login_url + '?gotoUrl=' + encodeURIComponent(gotoUrl)
    }

    /** Read a cookie the core set on the way back from a redirect login, and clear it. */
    const takeCookie = (name: string): string => {
        const match = document.cookie.split(';').find((cookie) => cookie.trim().startsWith(`${name}=`))
        if (!match) {
            return ''
        }
        document.cookie = `${name}=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT`
        return decodeURIComponent(match.trim().slice(name.length + 1))
    }

    /**
     * Pick up a second factor still owed after an OIDC/OAuth2/SAML login.
     *
     * The core cannot answer a browser redirect with an MFA challenge in a JSON body,
     * so it hands the scoped token over in a cookie and lets this page run the same
     * TOTP/passkey step a form login would have run.
     */
    const resumeMfaFromRedirect = async (): Promise<boolean> => {
        const enrollFromRedirect = takeCookie('mfa_enroll')
        if (enrollFromRedirect) {
            enrollToken.value = enrollFromRedirect
            mfaMethods.value = (takeCookie('mfa_methods') || 'totp').split(',').filter(Boolean)
            await beginTotpEnrollment()
            return true
        }

        const tokenFromRedirect = takeCookie('mfa_token')
        if (!tokenFromRedirect) {
            return false
        }
        mfaToken.value = tokenFromRedirect
        mfaMethods.value = (takeCookie('mfa_methods') || 'totp').split(',').filter(Boolean)
        totpCode.value = ''
        step.value = 'mfa'
        return true
    }

    /**
     * Component mount - handle authentication flow
     */
    onMounted(async () => {
        // If already authenticated, redirect to dashboard
        if (isAuthenticated()) {
            router.push('/dashboard')
            return
        }

        // Handle DEPRECATED external login flow (env-configured URL takes precedence)
        if (authStore.hasExternalLoginUrl) {
            const code = route.query['code']
            const sessionState = route.query['session_state']

            if (code !== undefined && sessionState !== undefined) {
                // Complete external auth with code
                handleFormSubmit()
            } else {
                // Redirect to external login
                window.location.href = authStore.getLoginURL
            }
            return
        }

        // Error passed back from an OAuth redirect flow
        const loginError = route.query['login_error']
        if (typeof loginError === 'string' && loginError) {
            showError(loginError)
        }

        await authStore.loadLoginMethods()
        const firstForm = formMethods.value[0]
        if (firstForm) {
            selectedProviderId.value = firstForm.id
        }

        // Loaded first, so that backing out of the challenge lands on a usable form
        await resumeMfaFromRedirect()
    })
</script>

<style scoped>
    /* Layout-only styles. All theming (background, border, button colors) is
       handled by Vuetify utility classes (bg-background, bg-surface, border,
       rounded-lg, pa-6) and component props (color="primary",
       variant="outlined", type="error") which auto-adapt to the active
       Vuetify theme. Mixing custom CSS variables with Vuetify's --v-theme-*
       was the root cause of multiple dark-mode bugs; removing it eliminates
       that class of issues going forward. */

    .login-screen {
        width: 100%;
        min-height: 100vh;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 20px;
    }

    .logo-container {
        display: flex;
        justify-content: center;
        align-items: center;
        width: 100%;
        min-height: 100px;
        padding-bottom: 12px;
    }

    .login-logo {
        max-width: 400px;
        width: 100%;
        height: auto;
        display: block;
    }

    /* Surface, border, radius, and padding come from Vuetify utility classes
       (bg-surface border rounded-lg pa-6); the class below only handles the
       size + fl/column layout of the form contents. */
    .login-form {
        width: 100%;
        max-width: 400px;
        display: flex;
        flex-direction: column;
        gap: 16px;
    }

    .form-fields {
        display: flex;
        flex-direction: column;
        gap: 12px;
        flex: 1;
        min-width: 0;
    }

    .login-field {
        width: 100%;
        min-width: 200px;
    }

    .password-toggle {
        cursor: pointer;
        user-select: none;
    }

    .form-actions {
        display: flex;
        justify-content: center;
        gap: 12px;
    }

    .form-actions.flex-column {
        flex-direction: column;
        align-items: stretch;
    }

    .qr-container {
        display: flex;
        justify-content: center;
    }

    .qr-image {
        width: 200px;
        height: 200px;
        border-radius: 6px;
        background: white;
        padding: 8px;
    }

    .error-alert {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        width: 100%;
        max-height: 80px;
        margin: 0;
        border-radius: 0;
        z-index: 1000;
        overflow: hidden;
    }

    .warning-alert {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        width: 100%;
        max-height: 80px;
        margin: 0;
        border-radius: 0;
        z-index: 1000;
        overflow: hidden;
    }

    /* ===== Responsive ===== */
    @media (max-width: 600px) {
        .login-screen {
            padding: 16px;
        }

        .login-form {
            max-width: 100%;
        }

        .login-logo {
            width: 100%;
        }
    }
</style>
