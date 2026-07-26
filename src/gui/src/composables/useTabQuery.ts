import { ref, watch, type Ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

/**
 * Keeps a tab selection in sync with the `?tab=` URL query so tabs are
 * deep-linkable and survive reloads / back-forward navigation.
 *
 * @param validTabs the set of allowed tab values for this view
 * @param defaultTab the tab to use when the query is missing or invalid
 */
export function useTabQuery(validTabs: readonly string[], defaultTab: string): Ref<string> {
    const route = useRoute()
    const router = useRouter()

    const isValidTab = (value: unknown): value is string => typeof value === 'string' && validTabs.includes(value)

    // Initialise from the ?tab= query param when valid, otherwise the default tab.
    const activeTab = ref(isValidTab(route.query['tab']) ? (route.query['tab'] as string) : defaultTab)

    // Keep the URL query in sync with the active tab.
    watch(activeTab, (value) => {
        if (route.query['tab'] !== value) {
            router.replace({ query: { ...route.query, tab: value } })
        }
    })

    // React to external query changes (deep links, back/forward navigation).
    watch(
        () => route.query['tab'],
        (value) => {
            activeTab.value = isValidTab(value) ? value : defaultTab
        }
    )

    return activeTab
}
