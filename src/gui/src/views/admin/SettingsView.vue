<template>
    <v-container
        fluid
        class="pa-0"
    >
        <v-tabs
            v-model="activeTab"
            bg-color="transparent"
            color="primary"
        >
            <v-tab
                v-for="tab in availableTabs"
                :key="tab.value"
                :value="tab.value"
                :title="t(tab.description)"
            >
                <v-icon
                    :icon="tab.icon"
                    start
                />
                {{ t(tab.title) }}
            </v-tab>
        </v-tabs>

        <v-window v-model="activeTab">
            <v-window-item
                v-for="tab in availableTabs"
                :key="tab.value"
                :value="tab.value"
            >
                <component
                    :is="tab.component"
                    v-if="activeTab === tab.value"
                    v-bind="tab.props"
                />
            </v-window-item>
        </v-window>
    </v-container>
</template>

<script setup lang="ts">
    import { ref, computed, watch } from 'vue'
    import type { Component } from 'vue'
    import { useRoute, useRouter } from 'vue-router'
    import { useI18n } from 'vue-i18n'
    import { useAuth } from '@/composables/useAuth'
    import type { PermissionKey } from '@/types/permissions'
    import SettingsTable from '@/components/config/SettingsTable.vue'
    import RoutingTlsTab from '@/components/config/RoutingTlsTab.vue'

    type SettingsTab = {
        value: string
        title: string
        icon: string
        description: string
        component: Component
        permission: PermissionKey
        props?: Record<string, unknown>
    }

    const { t } = useI18n()
    const { checkPermission } = useAuth()
    const route = useRoute()
    const router = useRouter()

    const tabs: SettingsTab[] = [
        {
            value: 'general',
            title: 'nav_menu.settings',
            icon: 'mdi-application-cog-outline',
            description: 'settings.tab_description',
            component: SettingsTable,
            permission: 'CONFIG_SETTINGS_ACCESS',
            props: { globalSetting: true }
        },
        {
            // Instance-wide routing: the TLS floor, the default certificate, the
            // HSTS policy and the resolver default. Per-hostname overrides live
            // on each public web, in its own dialog - host-scoped settings
            // belong to the host.
            value: 'routing',
            title: 'routing.tab_title',
            icon: 'mdi-router-network',
            description: 'routing.tab_description',
            component: RoutingTlsTab,
            permission: 'CONFIG_TRAEFIK_ACCESS'
        }
    ]

    // Only show tabs the user is allowed to access.
    const availableTabs = computed(() => tabs.filter((tab) => checkPermission(tab.permission)))

    const isValidTab = (value: unknown): value is string =>
        typeof value === 'string' && availableTabs.value.some((tab) => tab.value === value)

    const defaultTab = (): string => availableTabs.value[0]?.value ?? 'general'

    // Initialise from the ?tab= query param when valid, otherwise the first accessible tab.
    const activeTab = ref(isValidTab(route.query['tab']) ? (route.query['tab'] as string) : defaultTab())

    // Keep the URL query in sync with the active tab so tabs are deep-linkable.
    watch(activeTab, (value) => {
        if (route.query['tab'] !== value) {
            router.replace({ query: { ...route.query, tab: value } })
        }
    })

    // React to external query changes (deep links, back/forward navigation).
    watch(
        () => route.query['tab'],
        (value) => {
            activeTab.value = isValidTab(value) ? value : defaultTab()
        }
    )
</script>
