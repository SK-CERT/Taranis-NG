import type { Pinia } from 'pinia'
import { useAuthStore } from '@/stores/auth'

/** Install the explicit E2E-only token directly, without exposing it in a cookie. */
export function bootstrapTestingToken(pinia: Pinia): boolean {
    const testingToken = import.meta.env.VITE_APP_TARANIS_NG_TESTING_TOKEN
    if (!testingToken || typeof testingToken !== 'string') {
        return false
    }

    useAuthStore(pinia).setToken(testingToken)
    return true
}
