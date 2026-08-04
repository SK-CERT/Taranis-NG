import { computed, ref, watch, type ComputedRef, type Ref } from 'vue'
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
export function usePermissionTabs<T extends PermissionTab>(tabs: readonly T[]): { availableTabs: ComputedRef<T[]>; activeTab: Ref<string> } {
    const { checkPermission } = useAuth()
    const route = useRoute()
    const router = useRouter()

    const availableTabs = computed(() => tabs.filter((tab) => checkPermission(tab.permission)))
    const isAvailable = (value: unknown): value is string =>
        typeof value === 'string' && availableTabs.value.some((tab) => tab.value === value)
    const normalize = (value: unknown): string => (isAvailable(value) ? value : (availableTabs.value[0]?.value ?? ''))

    const activeTab = ref(normalize(route.query['tab']))

    watch(activeTab, (value) => {
        const normalized = normalize(value)
        if (value !== normalized) {
            activeTab.value = normalized
            return
        }

        if (normalized && route.query['tab'] !== normalized) {
            void router.replace({ query: { ...route.query, tab: normalized } })
        }
    })

    watch(
        () => route.query['tab'],
        (value) => {
            const normalized = normalize(value)
            if (activeTab.value !== normalized) {
                activeTab.value = normalized
            }
            if (normalized && value !== normalized) {
                void router.replace({ query: { ...route.query, tab: normalized } })
            }
        },
        { immediate: true }
    )

    // Keep the selection authorized if permissions are refreshed in place.
    watch(availableTabs, () => {
        const normalized = normalize(activeTab.value)
        if (activeTab.value !== normalized) {
            activeTab.value = normalized
        }
    })

    return { availableTabs, activeTab }
}
