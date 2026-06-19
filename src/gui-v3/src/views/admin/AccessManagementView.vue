<template>
    <v-container fluid class="pa-0">
        <v-tabs v-model="activeTab" bg-color="transparent" color="primary">
            <v-tab v-for="tab in availableTabs" :key="tab.value" :value="tab.value">
                {{ t(tab.title) }}
            </v-tab>
        </v-tabs>

        <v-window v-model="activeTab">
            <v-window-item v-for="tab in availableTabs" :key="tab.value" :value="tab.value">
                <component :is="tab.component" v-if="activeTab === tab.value" />
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
    import UsersTab from '@/components/config/users/UsersTab.vue'
    import RolesTab from '@/components/config/roles/RolesTab.vue'
    import ACLTab from '@/components/config/acl/ACLTab.vue'
    import OrganizationsTab from '@/components/config/organizations/OrganizationsTab.vue'

    type AccessTab = {
        value: string
        title: string
        component: Component
        permission: PermissionKey
    }

    const { t } = useI18n()
    const { checkPermission } = useAuth()
    const route = useRoute()
    const router = useRouter()

    const tabs: AccessTab[] = [
        { value: 'users', title: 'nav_menu.users', component: UsersTab, permission: 'CONFIG_USER_ACCESS' },
        { value: 'roles', title: 'nav_menu.roles', component: RolesTab, permission: 'CONFIG_ROLE_ACCESS' },
        { value: 'acls', title: 'nav_menu.acls', component: ACLTab, permission: 'CONFIG_ACL_ACCESS' },
        { value: 'organizations', title: 'nav_menu.organizations', component: OrganizationsTab, permission: 'CONFIG_ORGANIZATION_ACCESS' }
    ]

    // Only show tabs the user is allowed to access.
    const availableTabs = computed(() => tabs.filter((tab) => checkPermission(tab.permission)))

    const isValidTab = (value: unknown): value is string =>
        typeof value === 'string' && availableTabs.value.some((tab) => tab.value === value)

    const defaultTab = (): string => availableTabs.value[0]?.value ?? 'users'

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
