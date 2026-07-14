<template>
    <v-app
        class="taranis"
        :data-theme="theme.global.name.value"
    >
        <!-- Main Menu (top bar) - only shown when authenticated -->
        <MainMenu v-if="isAuth" />

        <!-- Side navigation drawer - only shown when authenticated -->
        <v-navigation-drawer
            v-if="isAuth"
            v-model="navVisible"
            width="100"
            rail
            rail-width="100"
            color="cx-drawer-bg"
        >
            <router-view name="nav" />
        </v-navigation-drawer>

        <v-main>
            <router-view />
        </v-main>

        <!-- Notification component -->
        <NotificationSnackbar />
    </v-app>
</template>

<script setup lang="ts">
    import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
    import { useI18n } from 'vue-i18n'
    import { useTheme } from 'vuetify'
    import { useAuthStore } from '@/stores/auth'
    import { useUserStore } from '@/stores/user'
    import { useSettingsStore } from '@/stores/settings'
    import { useAuth } from '@/composables/useAuth'
    import { useSSE } from '@/composables/useSSE'
    import MainMenu from '@/components/MainMenu.vue'
    import NotificationSnackbar from '@/components/common/NotificationSnackbar.vue'

    const { locale } = useI18n()
    const theme = useTheme()
    const authStore = useAuthStore()
    const userStore = useUserStore()
    const settingsStore = useSettingsStore()
    const { isAuthenticated, needTokenRefresh } = useAuth()

    const navVisible = ref(true)
    const isAuth = computed(() => authStore.isAuthenticated)

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
    const { connect, disconnect, reconnect, subscribe } = useSSE()

    const applyTheme = (themeName: string): void => {
        if (typeof theme.change === 'function') {
            theme.change(themeName)
        } else {
            theme.global.name.value = themeName
        }
    }

    // On startup, before the user's saved DARK_THEME preference is loaded (which
    // happens in initUserSettings after login), follow the browser's
    // prefers-color-scheme so the pre-login Login page renders in the OS theme.
    // Once initUserSettings runs, the saved preference overrides this. The
    // listener keeps the Login page in sync if the user changes the OS theme
    // while sitting on it.
    const browserDarkMedia = window.matchMedia('(prefers-color-scheme: dark)')
    const applyBrowserTheme = (): void => {
        // Only follow the browser if the user hasn't already pinned a preference
        // this session (authStore.isAuthenticated becomes true after login, at
        // which point initUserSettings owns the theme).
        if (!authStore.isAuthenticated) {
            applyTheme(browserDarkMedia.matches ? 'dark' : 'light')
        }
    }
    browserDarkMedia.addEventListener('change', applyBrowserTheme)
    applyBrowserTheme()

    const initializeSSE = async (): Promise<void> => {
        try {
            await connect()
            setupSSEListeners()
        } catch {
            console.info('[App] SSE not available - real-time updates disabled')
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
                const darkThemeSetting = settingsStore.getSetting('DARK_THEME')
                if (darkThemeSetting) {
                    applyTheme(darkThemeSetting.value === 'true' ? 'dark' : 'light')
                }

                // Apply spellcheck setting
                const spellcheckSetting = settingsStore.getSetting('SPELLCHECK')
                if (spellcheckSetting) {
                    settingsStore.spellcheck = spellcheckSetting.value === 'true'
                }

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

    const handleLoggedIn = (): void => {
        initializeAuthenticatedSession()
    }

    const handleLoggedOut = (): void => {
        disconnect()
        // After logout, fall back to the browser's prefers-color-scheme for the
        // pre-login Login screen, so a user who picked "light" in-app (against a
        // dark OS) gets the OS theme back rather than dragging their in-app
        // choice onto the unauthenticated page.
        applyBrowserTheme()
    }

    const handleNavClicked = (): void => {
        navVisible.value = !navVisible.value
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
                        })
                }
            } else if (authStore.jwt) {
                console.log('[App] Token expired, logging out...')
                authStore.logout()
            }
        }, 5000)
    }

    /**
     * Component mount
     */
    onMounted(async () => {
        console.log('[App] API:', import.meta.env.VITE_APP_TARANIS_NG_CORE_API)
        console.log('[App] SSE:', import.meta.env.VITE_APP_TARANIS_NG_CORE_SSE)

        // Initialize from the stored token, which main.ts has already seeded from the
        // "jwt" cookie when we arrived here from a redirect login.
        if (authStore.jwt && !userStore.user.id) {
            // Token exists but user data not loaded - restore from JWT
            const userData = authStore.getUserData
            if (userData) {
                userStore.setUser(userData)
                console.log('[App] Restored user session from stored token')
            }
        }

        if (isAuthenticated()) {
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

        browserDarkMedia.removeEventListener('change', applyBrowserTheme)

        window.removeEventListener('logged-in', handleLoggedIn)
        window.removeEventListener('logged-out', handleLoggedOut)
        window.removeEventListener('nav-clicked', handleNavClicked)
    })
</script>

<style>
    @import './styles/colors.css';

    /* Global styles */
    .taranis {
        font-family: 'Roboto', sans-serif;
        height: 100vh;
    }

    .v-main {
        height: 100%;
        display: flex;
        flex-direction: column;
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

    /* Selected tab: primary text and icon. */
    .v-tab.v-tab--selected,
    .v-tab.v-tab--selected .v-icon {
        color: rgb(var(--v-theme-primary)) !important;
    }

    /* Selected tab slider bar (its background defaults to a faint on-surface grey). */
    .v-tab.v-tab--selected .v-tab__slider {
        background-color: rgb(var(--v-theme-primary)) !important;
    }
</style>
