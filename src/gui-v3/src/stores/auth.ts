import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import ApiService from '@/services/api_service'
import { getLoginMethods, login as loginApi, logout as logoutApi, refresh } from '@/api/auth'
import { parseJwtClaims } from '@/services/jwt'
import { getExternalAuthCallbackUrl, getExternalAuthUrl, resolveExternalAuthUrl } from '@/services/auth/runtime_urls'
import { useUserStore } from './user'
import type { AuthTokenResponse, JwtClaims, LoginMethod, LoginMethodsResponse, LoginPayload, UserClaims } from '@/types/auth'

type ApiResponse<T> = {
    data: T
}

const getStoredAccessToken = (): string => {
    const tokenFromItem = localStorage.getItem('ACCESS_TOKEN')
    if (tokenFromItem) {
        return tokenFromItem
    }

    const tokenFromProp = (localStorage as unknown as { ACCESS_TOKEN?: unknown }).ACCESS_TOKEN
    return typeof tokenFromProp === 'string' ? tokenFromProp : ''
}

const setStoredAccessToken = (value: string): void => {
    localStorage.setItem('ACCESS_TOKEN', value)
    ;(localStorage as unknown as { ACCESS_TOKEN?: string }).ACCESS_TOKEN = value
}

const parseJwtPayload = (token: string): JwtClaims | null => parseJwtClaims(token)

export const useAuthStore = defineStore('auth', () => {
    // State - Initialize from localStorage if available
    const jwt = ref(getStoredAccessToken())

    // Enabled login methods (providers) fetched from the backend for the login page
    const loginMethods = ref<LoginMethod[]>([])
    const loginMethodsLoaded = ref(false)
    const loginMethodsError = ref(false)
    // Passkeys are a site-wide capability (a security setting), not a provider.
    const passkeyEnabled = ref(false)

    // Getters
    const getUserData = computed(() => {
        if (!jwt.value) return null
        const data = parseJwtPayload(jwt.value)
        return data?.user_claims ?? null
    })

    const getSubjectName = computed(() => {
        if (!jwt.value) return ''
        const data = parseJwtPayload(jwt.value)
        return data?.sub ?? ''
    })

    const hasExternalLoginUrl = computed(() => {
        return getExternalAuthUrl(import.meta.env.VITE_APP_TARANIS_NG_LOGIN_URL) !== null
    })

    const getLoginURL = computed(() => {
        const configured = getExternalAuthUrl(import.meta.env.VITE_APP_TARANIS_NG_LOGIN_URL)
        return configured ? resolveExternalAuthUrl(configured) : '/login'
    })

    const hasExternalLogoutUrl = computed(() => {
        return getExternalAuthUrl(import.meta.env.VITE_APP_TARANIS_NG_LOGOUT_URL) !== null
    })

    const getLogoutURL = computed(() => {
        const configured = getExternalAuthUrl(import.meta.env.VITE_APP_TARANIS_NG_LOGOUT_URL)
        return configured ? resolveExternalAuthUrl(configured) : '/logout'
    })

    const getExternalCallbackURL = computed(() => getExternalAuthCallbackUrl())

    const getJWT = computed(() => jwt.value)

    const isAuthenticated = computed(() => {
        if (!jwt.value || jwt.value.split('.').length < 3) {
            return false
        }
        const data = parseJwtPayload(jwt.value)
        if (!data) {
            return false
        }
        const exp = new Date((data.exp || 0) * 1000)
        const now = new Date()
        return now < exp
    })

    // Actions
    function setJwtToken(access_token: string): void {
        setStoredAccessToken(access_token)
        ApiService.setHeader()
        jwt.value = access_token
    }

    function clearJwtToken(): void {
        setStoredAccessToken('')
        ApiService.setHeader()
        jwt.value = ''
    }

    function clearSession(): void {
        clearJwtToken()
        useUserStore().clearUser()
        window.dispatchEvent(new Event('logged-out'))
    }

    async function login(userData: LoginPayload): Promise<ApiResponse<AuthTokenResponse>> {
        try {
            const response = (await loginApi(userData, userData.method)) as ApiResponse<AuthTokenResponse>
            setJwtToken(response.data.access_token)

            const userStore = useUserStore()
            userStore.setUser(getUserData.value)

            // Dispatch event to trigger settings initialization in App.vue
            window.dispatchEvent(new Event('logged-in'))
            return response
        } catch (error) {
            clearJwtToken()
            throw error
        }
    }

    async function logout(): Promise<void> {
        // Start the authenticated request before removing the local token, but
        // invalidate the browser session immediately. A slow or failed server
        // logout must never leave protected UI mounted with stale credentials.
        const logoutRequest = logoutApi()
        clearSession()
        await logoutRequest
    }

    async function refreshToken(): Promise<ApiResponse<AuthTokenResponse>> {
        try {
            const response = (await refresh()) as ApiResponse<AuthTokenResponse>
            setJwtToken(response.data.access_token)

            const userStore = useUserStore()
            userStore.setUser(getUserData.value)

            return response
        } catch (error) {
            clearSession()
            throw error
        }
    }

    function setToken(access_token: string): void {
        setJwtToken(access_token)

        const userStore = useUserStore()
        userStore.setUser(getUserData.value)

        // Don't dispatch logged-in event here - it's handled after cookie processing in App.vue
    }

    async function loadLoginMethods(): Promise<LoginMethod[]> {
        loginMethodsError.value = false
        try {
            const response = (await getLoginMethods()) as ApiResponse<LoginMethodsResponse>
            loginMethods.value = response.data?.items || []
            passkeyEnabled.value = !!response.data?.passkey_enabled
        } catch (error) {
            console.error('[Auth] Failed to load login methods:', error)
            loginMethods.value = []
            passkeyEnabled.value = false
            loginMethodsError.value = true
        } finally {
            loginMethodsLoaded.value = true
        }
        return loginMethods.value
    }

    // Complete a multi-step login (MFA / passkey) with the received access token.
    function finishLogin(access_token: string): void {
        setJwtToken(access_token)

        const userStore = useUserStore()
        userStore.setUser(getUserData.value)

        window.dispatchEvent(new Event('logged-in'))
    }

    return {
        // State
        jwt,
        loginMethods,
        loginMethodsLoaded,
        loginMethodsError,
        passkeyEnabled,

        // Getters
        getUserData,
        getSubjectName,
        hasExternalLoginUrl,
        getLoginURL,
        hasExternalLogoutUrl,
        getLogoutURL,
        getExternalCallbackURL,
        getJWT,
        isAuthenticated,

        // Actions
        login,
        refreshToken,
        setToken,
        logout,
        setJwtToken,
        clearJwtToken,
        loadLoginMethods,
        finishLogin
    }
})
