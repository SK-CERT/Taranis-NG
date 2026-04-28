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

// Singleton Vuetify instance (stateless, safe to share)
const vuetify = createVuetify({ components, directives })

/**
 * Create a fresh i18n instance for tests.
 * Uses real English messages so translated labels can be asserted on.
 */
export function createTestI18n() {
  return createI18n({
    legacy: false,
    locale: 'en',
    fallbackLocale: 'en',
    messages: { en }
  })
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
  const i18n = createTestI18n()

  const globalOptions = options.global || {}
  const existingPlugins = globalOptions.plugins || []

  return mount(component, {
    ...options,
    global: {
      ...globalOptions,
      plugins: [vuetify, i18n, pinia, ...existingPlugins],
      stubs: {
        // Prevent router-link from causing errors in unit tests
        'router-link': true,
        'router-view': true,
        ...globalOptions.stubs
      }
    }
  })
}
