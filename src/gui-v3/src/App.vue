<template>
    <v-app
        class="taranis"
        :data-theme="theme.global.name.value"
    >
        <!-- Main Menu (top bar) - only shown when authenticated -->
        <MainMenu
            v-if="isAuth"
            :show-nav-toggle="showNavigation"
        />

        <!-- Side navigation drawer - only shown when authenticated -->
        <v-navigation-drawer
            v-if="showNavigation"
            v-model="navVisible"
            width="160"
            color="cx-drawer-bg"
            class="app-navigation"
        >
            <router-view name="nav" />
        </v-navigation-drawer>

        <v-main :class="{ 'configuration-view': isConfigurationRoute }">
            <!-- Never retain a protected view after local credentials disappear. -->
            <router-view v-if="isAuth || route.path === '/login'" />
        </v-main>

        <!-- Notification component -->
        <NotificationSnackbar />
    </v-app>
</template>

<script setup lang="ts">
    import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
    import { useI18n } from 'vue-i18n'
    import { useTheme } from 'vuetify'
    import { useRouter } from 'vue-router'
    import { useAuthStore } from '@/stores/auth'
    import { useUserStore } from '@/stores/user'
    import { useSettingsStore } from '@/stores/settings'
    import { Settings } from '@/types/settings'
    import { useAuth } from '@/composables/useAuth'
    import { useSSE } from '@/composables/useSSE'
    import MainMenu from '@/components/MainMenu.vue'
    import NotificationSnackbar from '@/components/common/NotificationSnackbar.vue'

    const { locale } = useI18n()
    const theme = useTheme()
    const router = useRouter()
    const route = computed(() => router.currentRoute?.value ?? { name: undefined, path: '' })
    const authStore = useAuthStore()
    const userStore = useUserStore()
    const settingsStore = useSettingsStore()
    const { isAuthenticated, needTokenRefresh } = useAuth()

    const navVisible = ref(true)
    const isAuth = computed(() => authStore.isAuthenticated)
    const showNavigation = computed(() => isAuth.value && route.value.name !== 'publish' && route.value.name !== 'dashboard')
    const isConfigurationRoute = computed(() => route.value.path === '/config' || route.value.path.startsWith('/config/'))

    // Watch theme changes and apply dark-mode/light-mode classes to HTML element.
    // These override the prefers-color-scheme CSS fallback once the user's preference is known.
    watch(
        () => theme.global.name.value,
        (newTheme) => {
            if (newTheme === 'dark') {
                document.documentElement.classList.add('dark-mode')
                document.documentElement.classList.remove('light-mode')
            } else {
                document.documentElement.classList.remove('dark-mode')
                document.documentElement.classList.add('light-mode')
            }
            console.log('[App] Theme changed to:', newTheme, 'HTML classes:', document.documentElement.className)
        },
        { immediate: true }
    )

    // SSE connection
    const { connect, disconnect, reconnect, subscribe, onResync } = useSSE()

    // Events published while this tab had no stream are not replayed, so anything showing
    // live data has to re-read it once the stream is back. Registered once for the app.
    onResync(() => {
        console.log('[SSE] Stream restored - requesting resync')
        window.dispatchEvent(new CustomEvent('sse-resync'))
    })

    const applyTheme = (themeName: string): void => {
        if (typeof theme.change === 'function') {
            theme.change(themeName)
        } else {
            theme.global.name.value = themeName
        }
    }

    const initializeSSE = async (): Promise<void> => {
        // Register the handlers first: they are kept by the composable and re-attached on
        // every (re)connect, so they survive a failed first attempt too.
        setupSSEListeners()

        try {
            await connect()
        } catch {
            console.info('[App] SSE not available - retrying in the background')
        }
    }

    /**
     * Initialize user settings after login
     */
    const initUserSettings = async (): Promise<void> => {
        try {
            // Load all settings
            await settingsStore.loadSettings({ search: '' })
            // console.log('[App] Settings loaded:', settingsStore.getSettings.length, 'items')

            // Defer UI updates to avoid forcing layout before styles load
            requestAnimationFrame(async () => {
                await nextTick()

                // Apply dark theme setting
                const darkThemeSetting = settingsStore.getSettingBoolean(Settings.DARK_THEME, false)
                applyTheme(darkThemeSetting ? 'dark' : 'light')

                // Apply spellcheck setting
                const spellcheckSetting = settingsStore.getSettingBoolean(Settings.SPELLCHECK, true)
                settingsStore.spellcheck = spellcheckSetting

                // Apply language setting
                if (settingsStore.getProfileLanguage) {
                    locale.value = settingsStore.getProfileLanguage
                }
            })

            // Load additional user data (non-blocking)
            await settingsStore.loadUserWordLists()
            await settingsStore.loadUserHotkeys()
            // console.log('[App] User settings initialized successfully')
        } catch (error) {
            console.error('[App] Error initializing user settings:', error)
        }
    }

    const initializeAuthenticatedSession = async (): Promise<void> => {
        await initUserSettings()
        await initializeSSE()
    }

    /**
     * Setup SSE event listeners
     */
    const setupSSEListeners = (): void => {
        subscribe('news-items-updated', (data) => {
            console.log('[SSE] News items updated:', data)
            window.dispatchEvent(new CustomEvent('news-items-updated', { detail: data }))
        })

        subscribe('report-items-updated', (data) => {
            console.log('[SSE] Report items updated:', data)
            window.dispatchEvent(new CustomEvent('report-items-updated', { detail: data }))
        })

        subscribe('report-item-updated', (data) => {
            console.log('[SSE] Report item updated:', data)
            window.dispatchEvent(new CustomEvent('report-item-updated', { detail: data }))
        })

        subscribe('report-item-locked', (data) => {
            console.log('[SSE] Report item locked:', data)
            window.dispatchEvent(new CustomEvent('report-item-locked', { detail: data }))
        })

        subscribe('report-item-unlocked', (data) => {
            console.log('[SSE] Report item unlocked:', data)
            window.dispatchEvent(new CustomEvent('report-item-unlocked', { detail: data }))
        })
    }

    /**
     * Handle JWT from cookie (e.g., from external auth)
     */
    const handleJWTFromCookie = async (): Promise<boolean> => {
        const testingToken = import.meta.env.VITE_APP_TARANIS_NG_TESTING_TOKEN
        if (testingToken && typeof testingToken === 'string') {
            document.cookie = `jwt=${testingToken}; path=/`
        }

        const cookies = document.cookie.split(';').reduce<Record<string, string>>((acc, cookie) => {
            const [key, value] = cookie.trim().split('=')
            if (!key) {
                return acc
            }
            acc[key] = value ?? ''
            return acc
        }, {})

        if (cookies['jwt']) {
            authStore.setToken(cookies['jwt'])
            document.cookie = 'jwt=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT'

            await initializeAuthenticatedSession()
            return true
        }

        return false
    }

    const handleLoggedIn = (): void => {
        initializeAuthenticatedSession()
    }

    const handleLoggedOut = (): void => {
        disconnect()
    }

    const handleNavClicked = (): void => {
        navVisible.value = !navVisible.value
    }

    const navigateToLogin = (): void => {
        if (route.value.path !== '/login') {
            void router.replace('/login')
        }
    }

    /**
     * Token refresh interval
     */
    let refreshInterval: ReturnType<typeof setInterval> | null = null

    /**
     * Start token refresh checking
     */
    const startTokenRefresh = (): void => {
        refreshInterval = setInterval(() => {
            if (isAuthenticated()) {
                if (needTokenRefresh()) {
                    console.log('[App] Refreshing token...')
                    authStore
                        .refreshToken()
                        .then(() => {
                            reconnect().catch(() => {
                                console.info('[App] SSE reconnect failed - real-time updates disabled')
                            })
                        })
                        .catch((error) => {
                            console.error('[App] Token refresh failed:', error)
                            navigateToLogin()
                        })
                }
            } else if (authStore.jwt) {
                console.log('[App] Token expired, logging out...')
                const logoutRequest = authStore.logout()
                navigateToLogin()
                logoutRequest.catch((error) => {
                    console.error('[App] Logout after token expiry failed:', error)
                })
            }
        }, 5000)
    }

    /**
     * Component mount
     */
    onMounted(async () => {
        console.log('[App] API:', import.meta.env.VITE_APP_TARANIS_NG_CORE_API)
        console.log('[App] SSE:', import.meta.env.VITE_APP_TARANIS_NG_CORE_SSE)

        // Initialize from stored token if available
        if (authStore.jwt && !userStore.user.id) {
            // Token exists but user data not loaded - restore from JWT
            const userData = authStore.getUserData
            if (userData) {
                userStore.setUser(userData)
                console.log('[App] Restored user session from stored token')
            }
        }

        const initializedFromCookie = await handleJWTFromCookie()

        if (!initializedFromCookie && isAuthenticated()) {
            await initializeAuthenticatedSession()
        }

        // Start token refresh checking
        startTokenRefresh()

        window.addEventListener('logged-in', handleLoggedIn)
        window.addEventListener('logged-out', handleLoggedOut)
        window.addEventListener('nav-clicked', handleNavClicked)
    })

    /**
     * Component unmount
     */
    onUnmounted(() => {
        disconnect()

        if (refreshInterval) {
            clearInterval(refreshInterval)
        }

        window.removeEventListener('logged-in', handleLoggedIn)
        window.removeEventListener('logged-out', handleLoggedOut)
        window.removeEventListener('nav-clicked', handleNavClicked)
    })
</script>

<style>
    @import './styles/colors.css';

    /* Global styles */
    .taranis {
        font-family:
            'Roboto',
            ui-sans-serif,
            system-ui,
            -apple-system,
            BlinkMacSystemFont,
            sans-serif;
        height: 100vh;
        letter-spacing: 0.005em;
        background: rgb(var(--v-theme-background));
    }

    .v-main {
        height: 100%;
        display: flex;
        flex-direction: column;
        background: rgb(var(--v-theme-background));
    }

    .v-main__wrap {
        flex: 1 1 auto;
        display: flex;
        flex-direction: column;
        min-height: 0;
    }

    .cx-drawer-bg {
        background-color: var(--color-drawer-bg) !important;
    }

    .app-navigation {
        border-right: 1px solid rgba(var(--v-theme-outline), 0.5) !important;
        background: var(--color-drawer-bg) !important;
        box-shadow: 2px 0 7px rgba(20, 42, 68, 0.08);
    }

    .app-navigation .v-navigation-drawer__content {
        padding: 8px 7px;
    }

    /* Filled (flat/elevated) colored buttons should use their themed on-color for the
       label. Vuetify 4's base .v-btn color rule otherwise wins over the .bg-{color}
       rule, leaving dark text on colored backgrounds. Only targets buttons that carry
       a bg-{color} class (filled variants); text/outlined/tonal keep their colored label. */
    .v-btn.bg-primary {
        color: rgb(var(--v-theme-on-primary)) !important;
    }
    .v-btn.bg-secondary {
        color: rgb(var(--v-theme-on-secondary)) !important;
    }
    .v-btn.bg-tertiary {
        color: rgb(var(--v-theme-on-tertiary)) !important;
    }
    .v-btn.bg-success {
        color: rgb(var(--v-theme-on-success)) !important;
    }
    .v-btn.bg-error {
        color: rgb(var(--v-theme-on-error)) !important;
    }
    .v-btn.bg-warning {
        color: rgb(var(--v-theme-on-warning)) !important;
    }
    .v-btn.bg-info {
        color: rgb(var(--v-theme-on-info)) !important;
    }

    /* Keep application tooltips readable and consistent in both themes. */
    .v-tooltip > .v-overlay__content {
        max-width: 320px;
        padding: 5px 12px;
        border-radius: 4px;
        background: rgb(var(--v-theme-on-surface)) !important;
        color: rgb(var(--v-theme-surface)) !important;
        font-size: 0.875rem;
        line-height: 1.25rem;
        overflow-wrap: anywhere;
    }

    /* Selected left-nav item: tint the icon and label with the primary colour. */
    .v-navigation-drawer .v-list-item--active,
    .v-navigation-drawer .v-list-item--active .v-icon {
        color: rgb(var(--v-theme-primary)) !important;
    }

    /* Keep the active highlight grey (the overlay otherwise inherits the primary
       text colour via currentColor and turns blue). */
    .v-navigation-drawer .v-list-item--active > .v-list-item__overlay {
        background-color: rgb(var(--v-theme-on-surface)) !important;
    }

    .v-navigation-drawer .v-list {
        padding: 0;
        background: transparent;
    }

    .v-navigation-drawer .v-list-subheader {
        min-height: 36px;
        padding-inline: 12px;
        color: rgb(var(--v-theme-on-surface));
        font-size: 0.68rem;
        font-weight: 700;
        letter-spacing: 0.11em;
        opacity: 0.52;
        text-transform: uppercase;
    }

    .v-navigation-drawer .v-list-item {
        min-height: 38px;
        margin-bottom: 3px;
        border-radius: 3px;
    }

    .v-navigation-drawer .v-list-item--active {
        background: rgba(var(--v-theme-primary), 0.16);
        box-shadow: inset 3px 0 rgb(var(--v-theme-primary));
    }

    @media (max-width: 900px) {
        .app-navigation {
            width: 152px !important;
        }
    }

    /* Selected tab: primary text and icon. */
    .v-tab.v-tab--selected,
    .v-tab.v-tab--selected .v-icon {
        color: rgb(var(--v-theme-primary)) !important;
    }

    /* Selected tab slider bar (its background defaults to a faint on-surface grey). */
    .v-tab.v-tab--selected .v-tab__slider {
        background-color: rgb(var(--v-theme-primary)) !important;
    }

    /* Configuration is an operational workspace: keep tables dense enough to scan
       without changing the more generous spacing of edit forms and dialogs. */
    .configuration-view .v-data-table .v-data-table__th {
        height: 36px !important;
        padding-inline: 10px !important;
        font-size: 0.74rem;
    }

    .configuration-view .v-data-table .v-data-table__td {
        height: 40px !important;
        padding: 4px 10px !important;
    }

    .configuration-view .v-data-table thead tr {
        height: 36px !important;
    }

    .configuration-view .v-data-table tbody tr {
        height: 40px !important;
    }

    .configuration-view .v-data-table .v-btn--icon {
        width: 30px !important;
        height: 30px !important;
        min-width: 30px !important;
    }

    .configuration-view .v-data-table .v-btn--icon .v-icon {
        font-size: 20px !important;
    }

    .configuration-view .v-data-table .v-input,
    .configuration-view .v-data-table .v-field {
        --v-input-control-height: 32px;
    }

    .configuration-view .v-data-table,
    .settings-table {
        overflow: hidden;
        border: 2px solid var(--review-panel-border) !important;
        border-radius: 4px;
        box-shadow: none !important;
    }

    .configuration-view .v-data-table thead,
    .settings-table thead {
        background: var(--filter-controls-bg);
    }

    .configuration-view .v-data-table tbody tr,
    .settings-table tbody tr {
        background: var(--review-list-row);
    }

    .configuration-view .v-data-table tbody tr:hover,
    .settings-table tbody tr:hover {
        background: var(--review-list-row-hover);
    }
</style>
