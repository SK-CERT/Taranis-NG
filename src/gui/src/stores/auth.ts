import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import ApiService from '@/services/api_service'
import { getLoginMethods, login as loginApi, logout as logoutApi, refresh } from '@/api/auth'
import { parseJwtClaims } from '@/services/jwt'
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
        return import.meta.env.VITE_APP_TARANIS_NG_LOGIN_URL != null
    })

    const getLoginURL = computed(() => {
        const own_base_uri = document.URL.replace(/^([^:]*:\/*[^\/]*)\/.*/, '$1') //eslint-disable-line
        let login_uri = '/login'

        if (import.meta.env.VITE_APP_TARANIS_NG_LOGIN_URL != null) {
            login_uri = import.meta.env.VITE_APP_TARANIS_NG_LOGIN_URL
        }

        login_uri = login_uri.replace('TARANIS_GUI_URI', encodeURIComponent(own_base_uri + '/login'))
        return login_uri
    })

    const hasExternalLogoutUrl = computed(() => {
        return import.meta.env.VITE_APP_TARANIS_NG_LOGOUT_URL != null
    })

    const getLogoutURL = computed(() => {
        const own_base_uri = document.URL.replace(/^([^:]*:\/*[^\/]*)\/.*/, '$1') //eslint-disable-line
        let logout_uri = '/logout'

        if (import.meta.env.VITE_APP_TARANIS_NG_LOGOUT_URL != null) {
            logout_uri = import.meta.env.VITE_APP_TARANIS_NG_LOGOUT_URL
        }

        logout_uri = logout_uri.replace('TARANIS_GUI_URI', encodeURIComponent(own_base_uri + '/login'))
        return logout_uri
    })

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
        jwt.value = ''
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
        const userStore = useUserStore()

        try {
            await logoutApi()
            clearJwtToken()
            userStore.clearUser()
            // Dispatch event to trigger SSE closing in App.vue
            window.dispatchEvent(new Event('logged-out'))
        } catch (error) {
            clearJwtToken()
            userStore.clearUser()
            throw error
        }
    }

    async function refreshToken(): Promise<ApiResponse<AuthTokenResponse>> {
        try {
            const response = (await refresh()) as ApiResponse<AuthTokenResponse>
            setJwtToken(response.data.access_token)

            const userStore = useUserStore()
            userStore.setUser(getUserData.value)

            return response
        } catch (error) {
            clearJwtToken()
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
        try {
            const response = (await getLoginMethods()) as ApiResponse<LoginMethodsResponse>
            loginMethods.value = response.data?.items || []
            passkeyEnabled.value = !!response.data?.passkey_enabled
        } catch (error) {
            console.error('[Auth] Failed to load login methods:', error)
            loginMethods.value = []
            passkeyEnabled.value = false
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
        passkeyEnabled,

        // Getters
        getUserData,
        getSubjectName,
        hasExternalLoginUrl,
        getLoginURL,
        hasExternalLogoutUrl,
        getLogoutURL,
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
