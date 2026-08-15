/**
 * Shared mount helpers for Vitest component tests.
 *
 * Provides a pre-configured `mountWithPlugins` that sets up
 * Vuetify, vue-i18n, and Pinia so individual tests stay DRY.
 */
import { mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import { createI18n } from 'vue-i18n'
import { createPinia, setActivePinia } from 'pinia'
import en from '@/i18n/en.json'
import { pluralRules } from '@/i18n'

// Singleton Vuetify instance (stateless, safe to share)
const vuetify = createVuetify({ components, directives })

/**
 * Create a fresh i18n instance for tests.
 * Uses real English messages so translated labels can be asserted on.
 *
 * Only `en` is loaded, so the specs that exercise Intl formatting or bidi handling by
 * switching `$i18n.locale` to 'ar' / 'de-DE' resolve every key through fallback. That
 * is the intended path, but vue-i18n warns twice per key for it, which buries real
 * output. Silencing costs no coverage: a key genuinely absent from en.json is an
 * eslint error (`@intlify/vue-i18n/no-missing-keys`), and the catalogues have their
 * own contract specs (EnglishCatalogContracts, BaseLanguageCatalogContracts).
 */
export function createTestI18n() {
    return createI18n({
        legacy: false,
        locale: 'en',
        fallbackLocale: 'en',
        messages: { en },
        missingWarn: false,
        fallbackWarn: false,
        pluralRules
    })
}

/**
 * Whether a `global.plugins` entry is a vue-i18n instance.
 *
 * vue-i18n instances are the only plugins carrying both `mode` and `global`
 * alongside `install`, which distinguishes them from the router/pinia/vuetify
 * plugins specs also pass.
 *
 * @param {unknown} plugin — candidate entry from `global.plugins`
 * @returns {boolean}
 */
function isI18nPlugin(plugin) {
    return Boolean(plugin) && typeof plugin === 'object' && typeof plugin.install === 'function' && 'mode' in plugin && 'global' in plugin
}

/**
 * Mount a component with Vuetify + i18n + Pinia already wired in.
 *
 * @param {import('vue').Component} component — component under test
 * @param {import('@vue/test-utils').MountingOptions} [options={}] — extra mount options
 * @returns {import('@vue/test-utils').VueWrapper}
 *
 * @example
 *   const wrapper = mountWithPlugins(MyComponent, {
 *     props: { title: 'Hello' },
 *   })
 */
export function mountWithPlugins(component, options = {}) {
    const pinia = createPinia()
    setActivePinia(pinia)

    const globalOptions = options.global || {}
    const existingPlugins = globalOptions.plugins || []

    // Specs that assert on message composition install their own i18n through
    // `global.plugins`. Adding the default one as well installs vue-i18n twice into
    // the same app, and Vue reports every re-registered component and directive
    // ("Component i18n-t has already been registered in target app").
    const suppliedI18n = existingPlugins.find(isI18nPlugin)
    if (suppliedI18n) {
        // Those catalogues are deliberately partial — typically a handful of keys in
        // the locale under test plus `fallbackLocale: 'en'` — so falling back IS the
        // behaviour being asserted, and warning about it on every key is pure noise.
        // Scoped to caller-supplied instances: createTestI18n() above still warns.
        suppliedI18n.global.missingWarn = false
        suppliedI18n.global.fallbackWarn = false
    }
    const i18n = globalOptions.i18n ?? (suppliedI18n ? null : createTestI18n())

    return mount(component, {
        ...options,
        global: {
            ...globalOptions,
            plugins: [vuetify, ...(i18n ? [i18n] : []), pinia, ...existingPlugins],
            stubs: {
                // Prevent router-link from causing errors in unit tests
                'router-link': true,
                'router-view': true,
                ...globalOptions.stubs
            }
        }
    })
}
