import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createVuetify } from 'vuetify'
import { createI18n } from 'vue-i18n'
import PrimeVue from 'primevue/config'
import Material from '@primeuix/themes/material'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import '@mdi/font/css/materialdesignicons.css'
import 'vuetify/styles'
import 'primeicons/primeicons.css'

import App from './App.vue'
import router from './router'
import ApiService from './services/api_service'
import { messages, pluralRules, resolveLocale, synchronizeLocalePresentation, vuetifyMessages, vuetifyRtlLocales } from './i18n'
import { bootstrapTestingToken } from './services/testing_auth'
import { buildVuetifyThemes, DEFAULT_THEME_FAMILY, themeName } from './themes'

// Wait for stylesheets to be applied before mounting.
// This prevents "Layout was forced before page fully loaded" warnings.
async function waitForStylesReady(): Promise<void> {
    return new Promise((resolve) => {
        if (document.readyState === 'complete') {
            resolve()
            return
        }

        let attempts = 0
        const maxAttempts = 100

        function checkStylesReady() {
            attempts++
            const appDiv = document.getElementById('app')

            // Check if styles are applied by looking for computed styles.
            if (appDiv && document.fonts && document.fonts.ready) {
                Promise.resolve(document.fonts.ready)
                    .then(() => {
                        // Wait for next frame to ensure paint has occurred.
                        requestAnimationFrame(() => {
                            resolve()
                        })
                    })
                    .catch(() => resolve())
                return
            }

            if (attempts < maxAttempts) {
                requestAnimationFrame(checkStylesReady)
            } else {
                resolve()
            }
        }

        // Also wait for DOMContentLoaded.
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => {
                requestAnimationFrame(checkStylesReady)
            })
        } else {
            requestAnimationFrame(checkStylesReady)
        }
    })
}

// Initialize API service with base URL.
const baseURL = import.meta.env.VITE_APP_TARANIS_NG_CORE_API || '/api/v1'
ApiService.init(baseURL)

// Get default locale from environment or browser.
const configuredLocale = import.meta.env.VITE_APP_TARANIS_NG_LOCALE as string | undefined
const defaultLocale = resolveLocale(configuredLocale || navigator.language)

// Apply language metadata before mounting so an RTL catalog never flashes in LTR.
synchronizeLocalePresentation(defaultLocale)

// Create Vuetify instance.
const vuetify = createVuetify({
    components,
    directives,
    locale: {
        locale: defaultLocale,
        fallback: 'en',
        messages: vuetifyMessages,
        rtl: vuetifyRtlLocales
    },
    theme: {
        // Vuetify 4 defaults to 'system', which can only resolve to the built-in
        // light/dark themes - it cannot pick a family variant - so pin the default.
        defaultTheme: themeName(DEFAULT_THEME_FAMILY, false),
        themes: buildVuetifyThemes()
    },
    icons: {
        defaultSet: 'mdi'
    }
})

// Create i18n instance.
const i18n = createI18n({
    legacy: false,
    locale: defaultLocale,
    fallbackLocale: 'en',
    messages,
    pluralRules
})

// Create Pinia store.
const pinia = createPinia()

// Create Vue app instance (but defer mounting until styles are ready).
const app = createApp(App)

app.use(pinia)

// Keep the explicit E2E-only token hook without placing credentials in cookies.
// Redirect authentication itself is completed by Login.vue through /auth/redeem.
bootstrapTestingToken(pinia)

app.use(router)
app.use(vuetify)
app.use(i18n)
app.use(PrimeVue, {
    theme: {
        preset: Material,
        options: {
            darkModeSelector: '.dark-mode'
        }
    }
})

// Wait for styles to be ready, then mount.
waitForStylesReady().then(() => {
    app.mount('#app')

    // Log environment info in development.
    if (import.meta.env.DEV) {
        console.log('Environment:', {
            mode: import.meta.env.MODE,
            baseURL: import.meta.env.BASE_URL,
            apiURL: baseURL,
            locale: defaultLocale
        })
    }
})
