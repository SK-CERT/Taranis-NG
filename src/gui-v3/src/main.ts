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
import { consumeJwtCookie } from './services/jwt_cookie'

// Import i18n locale messages (JSON format for Weblate compatibility)
import en from './i18n/en.json'
import cs from './i18n/cs.json'
import sk from './i18n/sk.json'

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
let defaultLocale = import.meta.env.VITE_APP_TARANIS_NG_LOCALE as string | undefined
if (!defaultLocale) {
    defaultLocale = navigator.language.split('-')[0] || 'en'
}

// Create Vuetify instance.
const vuetify = createVuetify({
    components,
    directives,
    theme: {
        defaultTheme: 'light',
        themes: {
            light: {
                colors: {
                    'background': '#ECEEF4',
                    'surface': '#FAFAFA',
                    'surface-variant': '#F0F0F0',
                    'on-surface': '#212121',
                    'outline': '#C7C7C7',
                    'primary': '#4092DD',
                    'on-primary': '#FFFFFF',
                    'secondary': '#00677F',
                    'on-secondary': '#FFFFFF',
                    'tertiary': '#4E55B0',
                    'on-tertiary': '#FFFFFF',
                    'error': '#FF5252',
                    'on-error': '#FFFFFF',
                    'info': '#2196F3',
                    'on-info': '#FFFFFF',
                    'success': '#4CAF50',
                    'on-success': '#FFFFFF',
                    'warning': '#FB8C00',
                    'on-warning': '#FFFFFF',
                    'accent': '#82B1FF'
                }
            },
            dark: {
                colors: {
                    'background': '#121212',
                    'surface': '#212121',
                    'surface-variant': '#2D2D2D',
                    'on-surface': '#E1E2E7',
                    'outline': '#4A4A4A',
                    'primary': '#4092DD',
                    'on-primary': '#FFFFFF',
                    'secondary': '#64D4F8',
                    'on-secondary': '#003543',
                    'tertiary': '#BEC2FF',
                    'on-tertiary': '#1D2380',
                    'error': '#CF6679',
                    'on-error': '#690005',
                    'info': '#2196F3',
                    'success': '#4CAF50',
                    'warning': '#FB8C00'
                }
            }
        }
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
    messages: {
        en,
        cs,
        sk
    }
})

// Create Pinia store.
const pinia = createPinia()

// Create Vue app instance (but defer mounting until styles are ready).
const app = createApp(App)

app.use(pinia)

// Before the router runs: a redirect login lands here with the JWT in a cookie, and
// the auth guard would otherwise treat that arrival as anonymous.
consumeJwtCookie(pinia)

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
