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

        <!-- Render exactly one panel. Keeping every panel in a v-window allowed an
             outgoing panel to remain visible during/after a tab transition. The key
             also guarantees that stateful panels are unmounted when their tab closes. -->
        <component
            :is="activeTabDefinition.component"
            v-if="activeTabDefinition"
            :key="activeTabDefinition.value"
        />
    </v-container>
</template>

<script setup lang="ts">
    import { computed, type Component } from 'vue'
    import { useI18n } from 'vue-i18n'
    import { usePermissionTabs } from '@/composables/usePermissionTabs'
    import { ICONS } from '@/config/ui-constants'
    import type { PermissionKey } from '@/types/permissions'
    import UsersTab from '@/components/config/access-management/UsersTab.vue'
    import RolesTab from '@/components/config/access-management/RolesTab.vue'
    import ACLTab from '@/components/config/access-management/ACLTab.vue'
    import OrganizationsTab from '@/components/config/access-management/OrganizationsTab.vue'
    import AuthProvidersTab from '@/components/config/access-management/AuthProvidersTab.vue'
    import SecurityTab from '@/components/config/access-management/SecurityTab.vue'

    type AccessTab = {
        value: string
        title: string
        icon: string
        description: string
        component: Component
        permission: PermissionKey
    }

    const { t } = useI18n()

    const tabs: AccessTab[] = [
        {
            value: 'users',
            title: 'nav_menu.users',
            icon: ICONS.ACCOUNT_GROUP,
            description: 'access_management.users.tab_description',
            component: UsersTab,
            permission: 'CONFIG_USER_ACCESS'
        },
        {
            value: 'roles',
            title: 'nav_menu.roles',
            icon: ICONS.ACCOUNT_ARROW_RIGHT,
            description: 'access_management.roles.tab_description',
            component: RolesTab,
            permission: 'CONFIG_ROLE_ACCESS'
        },
        {
            value: 'acls',
            title: 'nav_menu.acls',
            icon: ICONS.LOCK_CHECK,
            description: 'access_management.acls.tab_description',
            component: ACLTab,
            permission: 'CONFIG_ACL_ACCESS'
        },
        {
            value: 'organizations',
            title: 'nav_menu.organizations',
            icon: ICONS.OFFICE_BUILDING,
            description: 'access_management.organizations.tab_description',
            component: OrganizationsTab,
            permission: 'CONFIG_ORGANIZATION_ACCESS'
        },
        {
            value: 'login-methods',
            title: 'nav_menu.login_methods',
            icon: 'mdi-login-variant',
            description: 'auth_provider.tab_description',
            component: AuthProvidersTab,
            permission: 'CONFIG_AUTH_PROVIDER_ACCESS'
        },
        {
            value: 'security',
            title: 'nav_menu.security',
            icon: 'mdi-shield-key',
            description: 'access_management.security.tab_description',
            component: SecurityTab,
            permission: 'CONFIG_AUTH_PROVIDER_ACCESS'
        }
    ]

    const { availableTabs, activeTab } = usePermissionTabs(tabs)
    const activeTabDefinition = computed(() => availableTabs.value.find((tab) => tab.value === activeTab.value))
</script>
