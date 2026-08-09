import { computed, watch, type ComputedRef, type WritableComputedRef } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuth } from '@/composables/useAuth'
import type { PermissionKey } from '@/types/permissions'

export type PermissionTab = {
    value: string
    permission: PermissionKey
}

/**
 * Filters a group of tabs by access permission and keeps the selected tab in
 * sync with the URL. Invalid and forbidden selections are replaced with the
 * first permitted tab.
 */
export function usePermissionTabs<T extends PermissionTab>(
    tabs: readonly T[]
): {
    availableTabs: ComputedRef<T[]>
    activeTab: WritableComputedRef<string>
} {
    const { checkPermission } = useAuth()
    const route = useRoute()
    const router = useRouter()

    const availableTabs = computed(() => tabs.filter((tab) => checkPermission(tab.permission)))
    const isAvailable = (value: unknown): value is string =>
        typeof value === 'string' && availableTabs.value.some((tab) => tab.value === value)
    const normalize = (value: unknown): string => (isAvailable(value) ? value : (availableTabs.value[0]?.value ?? ''))
    // Capture the concrete path that owns this composable. During navigation the
    // old component remains mounted briefly while `route` already points at the
    // destination; it must not normalize the destination's unrelated query.
    const ownerPath = route.path
    const isOwnerRoute = (): boolean => route.path === ownerPath

    const replaceOwnerQuery = (tab: string): void => {
        if (isOwnerRoute() && tab && route.query['tab'] !== tab) {
            // Target the owner path explicitly instead of whichever route happens
            // to be current when this asynchronous replacement is processed.
            void router.replace({ path: ownerPath, query: { ...route.query, tab } })
        }
    }

    // v-tabs writes through this computed; the route remains the single source of
    // truth, avoiding a ref watcher and route watcher racing one another.
    const activeTab = computed<string>({
        get: () => normalize(route.query['tab']),
        set: (value) => replaceOwnerQuery(normalize(value))
    })

    watch(
        [() => route.query['tab'], availableTabs],
        ([value]) => {
            if (isOwnerRoute()) {
                replaceOwnerQuery(normalize(value))
            }
        },
        { immediate: true }
    )

    return { availableTabs, activeTab }
}
