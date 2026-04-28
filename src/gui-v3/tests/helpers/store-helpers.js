/**
 * Pinia store helpers for unit tests.
 *
 * Provides helpers to create pre-seeded stores with mocked API layers.
 */
import { createPinia, setActivePinia } from 'pinia'

/**
 * Initialise a fresh Pinia instance and return a store created by `useStore`.
 *
 * @param {Function} useStore — Pinia `defineStore` composable (e.g. `useAuthStore`)
 * @param {Object} [initialState={}] — partial state to patch onto the store after creation
 * @returns {{ store: ReturnType<useStore>, pinia: Pinia }}
 *
 * @example
 *   const { store } = createTestStore(useAuthStore, { jwt: 'tok' })
 */
export function createTestStore(useStore, initialState = {}) {
  const pinia = createPinia()
  setActivePinia(pinia)
  const store = useStore()
  if (initialState && Object.keys(initialState).length > 0) {
    store.$patch(initialState)
  }
  return { store, pinia }
}

/**
 * Reset Pinia between tests.  Call in `beforeEach`.
 */
export function resetPinia() {
  setActivePinia(createPinia())
}
