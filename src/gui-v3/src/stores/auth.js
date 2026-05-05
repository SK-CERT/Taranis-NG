import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import ApiService from '@/services/api_service'
import { authenticate, refresh } from '@/api/auth'
import { useUserStore } from './user'

export const useAuthStore = defineStore('auth', () => {
  // State - Initialize from localStorage if available
  const jwt = ref(localStorage.ACCESS_TOKEN || '')

  // Getters
  const getUserData = computed(() => {
    if (!jwt.value) return null
    try {
      const data = JSON.parse(atob(jwt.value.split('.')[1]))
      return data.user_claims
    } catch (error) {
      console.error('Error parsing JWT:', error)
      return null
    }
  })

  const getSubjectName = computed(() => {
    if (!jwt.value) return ''
    try {
      const data = JSON.parse(atob(jwt.value.split('.')[1]))
      return data.sub
    } catch (error) {
      console.error('Error parsing JWT:', error)
      return ''
    }
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
    try {
      const data = JSON.parse(atob(jwt.value.split('.')[1]))
      const exp = new Date(data.exp * 1000)
      const now = new Date()
      return now < exp
    } catch (error) {
      return false
    }
  })

  // Actions
  function setJwtToken(access_token) {
    localStorage.ACCESS_TOKEN = access_token
    ApiService.setHeader()
    jwt.value = access_token
  }

  function clearJwtToken() {
    localStorage.ACCESS_TOKEN = ''
    jwt.value = ''
  }

  async function login(userData) {
    try {
      const response = await authenticate(userData, userData.method)
      setJwtToken(response.data.access_token)

      const userStore = useUserStore()
      userStore.setUser(getUserData.value)

      // Dispatch event to trigger settings initialization in App.vue
      window.dispatchEvent(new CustomEvent('logged-in'))

      return response
    } catch (error) {
      clearJwtToken()
      throw error
    }
  }

  async function refreshToken() {
    try {
      const response = await refresh()
      setJwtToken(response.data.access_token)

      const userStore = useUserStore()
      userStore.setUser(getUserData.value)

      return response
    } catch (error) {
      clearJwtToken()
      throw error
    }
  }

  function setToken(access_token) {
    setJwtToken(access_token)

    const userStore = useUserStore()
    userStore.setUser(getUserData.value)

    // Don't dispatch logged-in event here - it's handled after cookie processing in App.vue
  }

  function logout() {
    clearJwtToken()
    const userStore = useUserStore()
    userStore.clearUser()
  }

  return {
    // State
    jwt,

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
    clearJwtToken
  }
})
