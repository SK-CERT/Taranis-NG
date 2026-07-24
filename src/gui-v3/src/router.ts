import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useUserStore } from '@/stores/user'
import AuthService from '@/services/auth_service'
import Permissions from '@/services/permissions'
import { getFirstConfigRoute } from '@/config/config-nav-links'
import type { PermissionKey } from '@/types/permissions'
import { createLegacyAnalyzeRedirect } from '@/utils/analyze-routing'

interface RouteMetaAuth {
    requiresAuth?: boolean
    requiresPerm?: PermissionKey[]
    title?: string
}

const routes: RouteRecordRaw[] = [
    {
        path: '/',
        name: 'home',
        component: () => import('./views/HomeView.vue'),
        meta: { requiresAuth: true, requiresPerm: [] }
    },

    {
        path: '/assess',
        redirect: '/assess/group/all',
        meta: { requiresAuth: true, requiresPerm: [Permissions.ASSESS_ACCESS] }
    },
    {
        path: '/assess/group/:groupId',
        name: 'assess',
        components: {
            default: () => import('./views/users/AssessView.vue'),
            nav: () => import('./views/nav/AssessNav.vue')
        },
        meta: { requiresAuth: true, requiresPerm: [Permissions.ASSESS_ACCESS] }
    },
    {
        path: '/enter/source/:sourceId',
        redirect: (to) => ({
            name: 'assess',
            params: { groupId: 'all' },
            query: { ...to.query, manualSource: String(to.params['sourceId']) }
        })
    },
    {
        path: '/enter',
        redirect: {
            name: 'assess',
            params: { groupId: 'all' },
            query: { manualEntry: 'true' }
        }
    },
    {
        path: '/analyze',
        redirect: '/analyze/local'
    },
    {
        path: '/analyze/group/:groupName',
        redirect: createLegacyAnalyzeRedirect
    },
    {
        path: '/analyze/:scope',
        name: 'analyze',
        components: {
            default: () => import('./views/users/AnalyzeView.vue'),
            nav: () => import('./views/nav/AnalyzeNav.vue')
        },
        meta: { requiresAuth: true, requiresPerm: [Permissions.ANALYZE_ACCESS] }
    },
    {
        path: '/publish',
        name: 'publish',
        components: {
            default: () => import('./views/users/PublishView.vue'),
            nav: () => import('./views/nav/PublishNav.vue')
        },
        meta: { requiresAuth: true, requiresPerm: [Permissions.PUBLISH_ACCESS] }
    },
    {
        path: '/myassets',
        name: 'myassets_home',
        components: {
            default: () => import('./views/users/MyAssetsView.vue'),
            nav: () => import('./views/nav/MyAssetsNav.vue')
        },
        meta: { requiresAuth: true, requiresPerm: [Permissions.MY_ASSETS_ACCESS] }
    },
    {
        path: '/myassets/group/:groupId',
        name: 'myassets',
        components: {
            default: () => import('./views/users/MyAssetsView.vue'),
            nav: () => import('./views/nav/MyAssetsNav.vue')
        },
        meta: { requiresAuth: true, requiresPerm: [Permissions.MY_ASSETS_ACCESS] }
    },
    {
        path: '/dashboard',
        name: 'dashboard',
        components: {
            default: () => import('./views/users/DashboardView.vue'),
            nav: () => import('./views/nav/DashboardNav.vue')
        },
        meta: { requiresAuth: true, requiresPerm: [Permissions.ASSESS_ACCESS] }
    },
    {
        path: '/config',
        name: 'config',
        // Redirect to the first accessible config menu item.
        redirect: () => {
            // This redirect resolves before the global guard runs, so make sure
            // the user (and its permissions) is hydrated from the JWT first.
            const authStore = useAuthStore()
            const userStore = useUserStore()
            if (authStore.jwt && !userStore.user.id) {
                const userData = authStore.getUserData
                if (userData) {
                    userStore.setUser(userData)
                }
            }

            const firstRoute = getFirstConfigRoute((permission) => AuthService.hasPermission(permission))
            return firstRoute ?? '/'
        },
        meta: { requiresAuth: true, requiresPerm: [Permissions.CONFIG_ACCESS] }
    },
    {
        path: '/config/access-management',
        name: 'access_management',
        components: {
            default: () => import('./views/admin/AccessManagementView.vue'),
            nav: () => import('./views/nav/ConfigNav.vue')
        },
        meta: {
            requiresAuth: true,
            requiresPerm: [
                Permissions.CONFIG_USER_ACCESS,
                Permissions.CONFIG_ROLE_ACCESS,
                Permissions.CONFIG_ACL_ACCESS,
                Permissions.CONFIG_ORGANIZATION_ACCESS
            ]
        }
    },
    {
        path: '/config/collectors',
        name: 'collectors',
        components: {
            default: () => import('./views/admin/CollectorsView.vue'),
            nav: () => import('./views/nav/ConfigNav.vue')
        },
        meta: {
            requiresAuth: true,
            requiresPerm: [
                Permissions.CONFIG_OSINT_SOURCE_ACCESS,
                Permissions.CONFIG_OSINT_SOURCE_GROUP_ACCESS,
                Permissions.CONFIG_COLLECTORS_NODE_ACCESS
            ]
        }
    },
    {
        path: '/config/presenters',
        name: 'presenters',
        components: {
            default: () => import('./views/admin/PresentersView.vue'),
            nav: () => import('./views/nav/ConfigNav.vue')
        },
        meta: {
            requiresAuth: true,
            requiresPerm: [Permissions.CONFIG_PRODUCT_TYPE_ACCESS, Permissions.CONFIG_PRESENTERS_NODE_ACCESS]
        }
    },
    {
        path: '/config/publishers',
        name: 'publishers',
        components: {
            default: () => import('./views/admin/PublishersView.vue'),
            nav: () => import('./views/nav/ConfigNav.vue')
        },
        meta: {
            requiresAuth: true,
            requiresPerm: [Permissions.CONFIG_PUBLISHER_PRESET_ACCESS, Permissions.CONFIG_PUBLISHERS_NODE_ACCESS]
        }
    },
    {
        path: '/config/remote',
        name: 'remote',
        components: {
            default: () => import('./views/admin/RemoteView.vue'),
            nav: () => import('./views/nav/ConfigNav.vue')
        },
        meta: {
            requiresAuth: true,
            requiresPerm: [Permissions.CONFIG_REMOTE_ACCESS_ACCESS, Permissions.CONFIG_REMOTE_NODE_ACCESS]
        }
    },
    {
        path: '/config/bots',
        name: 'bots',
        components: {
            default: () => import('./views/admin/BotsView.vue'),
            nav: () => import('./views/nav/ConfigNav.vue')
        },
        meta: {
            requiresAuth: true,
            requiresPerm: [Permissions.CONFIG_BOT_PRESET_ACCESS, Permissions.CONFIG_BOTS_NODE_ACCESS]
        }
    },

    {
        path: '/config/reports',
        name: 'reports',
        components: {
            default: () => import('./views/admin/ReportsView.vue'),
            nav: () => import('./views/nav/ConfigNav.vue')
        },
        meta: {
            requiresAuth: true,
            requiresPerm: [Permissions.CONFIG_REPORT_TYPE_ACCESS, Permissions.CONFIG_ATTRIBUTE_ACCESS]
        }
    },
    {
        path: '/config/settings',
        name: 'settings',
        components: {
            default: () => import('./views/admin/SettingsView.vue'),
            nav: () => import('./views/nav/ConfigNav.vue')
        },
        meta: { requiresAuth: true, requiresPerm: [Permissions.CONFIG_SETTINGS_ACCESS] }
    },
    {
        path: '/config/wordlists',
        name: 'word_lists',
        components: {
            default: () => import('./views/admin/WordListsView.vue'),
            nav: () => import('./views/nav/ConfigNav.vue')
        },
        meta: { requiresAuth: true, requiresPerm: [Permissions.CONFIG_WORD_LIST_ACCESS] }
    },
    {
        path: '/config/workflow',
        name: 'workflow',
        components: {
            default: () => import('./views/admin/WorkflowView.vue'),
            nav: () => import('./views/nav/ConfigNav.vue')
        },
        meta: { requiresAuth: true, requiresPerm: [Permissions.CONFIG_WORKFLOW_ACCESS] }
    },
    {
        path: '/config/data-providers',
        name: 'data_providers',
        components: {
            default: () => import('./views/admin/DataProviderView.vue'),
            nav: () => import('./views/nav/ConfigNav.vue')
        },
        meta: {
            requiresAuth: true,
            requiresPerm: [Permissions.CONFIG_DATA_PROVIDER_ACCESS, Permissions.CONFIG_AI_ACCESS]
        }
    },
    {
        path: '/config/external',
        name: 'external',
        components: {
            default: () => import('./views/admin/ExternalView.vue'),
            nav: () => import('./views/nav/ConfigNav.vue')
        },
        meta: { requiresAuth: true, requiresPerm: [Permissions.MY_ASSETS_CONFIG] }
    },
    { path: '/config/users', redirect: { path: '/config/access-management', query: { tab: 'users' } } },
    { path: '/config/roles', redirect: { path: '/config/access-management', query: { tab: 'roles' } } },
    { path: '/config/acls', redirect: { path: '/config/access-management', query: { tab: 'acls' } } },
    {
        path: '/config/organizations',
        redirect: { path: '/config/access-management', query: { tab: 'organizations' } }
    },
    { path: '/config/collectors/sources', redirect: { path: '/config/collectors', query: { tab: 'sources' } } },
    { path: '/config/collectors/groups', redirect: { path: '/config/collectors', query: { tab: 'groups' } } },
    { path: '/config/collectors/nodes', redirect: { path: '/config/collectors', query: { tab: 'nodes' } } },
    { path: '/config/presenters/nodes', redirect: { path: '/config/presenters', query: { tab: 'nodes' } } },
    { path: '/config/product/types', redirect: { path: '/config/presenters', query: { tab: 'types' } } },
    { path: '/config/publishers/nodes', redirect: { path: '/config/publishers', query: { tab: 'nodes' } } },
    { path: '/config/publishers/presets', redirect: { path: '/config/publishers', query: { tab: 'presets' } } },
    { path: '/config/bots/nodes', redirect: { path: '/config/bots', query: { tab: 'nodes' } } },
    { path: '/config/bots/presets', redirect: { path: '/config/bots', query: { tab: 'presets' } } },
    { path: '/config/remote/access', redirect: { path: '/config/remote', query: { tab: 'access' } } },
    { path: '/config/remote/nodes', redirect: { path: '/config/remote', query: { tab: 'nodes' } } },
    { path: '/config/reportitems/types', redirect: { path: '/config/reports', query: { tab: 'types' } } },
    {
        path: '/config/reportitems/attributes',
        redirect: { path: '/config/reports', query: { tab: 'attributes' } }
    },
    { path: '/config/external/users', redirect: { path: '/config/external', query: { tab: 'users' } } },
    { path: '/config/external/groups', redirect: { path: '/config/external', query: { tab: 'groups' } } },
    { path: '/config/external/templates', redirect: { path: '/config/external', query: { tab: 'templates' } } },
    {
        path: '/login',
        name: 'login',
        component: () => import('./views/Login.vue')
    },
    {
        // Catch-all for unknown paths (e.g. /config/does-not-exist or /nope): show a 404 page.
        path: '/:pathMatch(.*)*',
        name: 'not_found',
        components: {
            default: () => import('./views/NotFoundView.vue')
        },
        meta: { requiresAuth: true }
    }
]

const router = createRouter({
    history: createWebHistory('/v2/'),
    routes
})

// Global navigation guard for authentication and permissions.
router.beforeEach((to) => {
    // Initialize user from JWT if not already done.
    const authStore = useAuthStore()
    const userStore = useUserStore()
    if (authStore.jwt && !userStore.user.id) {
        const userData = authStore.getUserData
        if (userData) {
            userStore.setUser(userData)
        }
    }

    const requiresAuth = to.matched.some((record) => Boolean((record.meta as RouteMetaAuth).requiresAuth))
    if (requiresAuth) {
        if (!AuthService.isAuthenticated()) {
            // Always show the chooser. Environment-configured external auth is
            // represented there as one method alongside database-backed methods.
            const loginError = to.query['login_error']
            return {
                path: '/login',
                query:
                    typeof loginError === 'string' && loginError
                        ? { redirect: to.fullPath, login_error: loginError }
                        : { redirect: to.fullPath }
            }
        }

        if (to.path === '/') {
            // Redirect root to appropriate default page based on permissions.
            if (AuthService.hasPermission(Permissions.ASSESS_ACCESS)) {
                return { path: '/dashboard' }
            }
            if (AuthService.hasPermission(Permissions.ASSESS_CREATE)) {
                return { path: '/enter' }
            }
            if (AuthService.hasPermission(Permissions.CONFIG_ACCESS)) {
                return { path: '/config' }
            }
            if (AuthService.hasPermission(Permissions.MY_ASSETS_ACCESS)) {
                return { path: '/myassets' }
            }
            return true
        }

        // Check permissions for the route.
        const requiredPermissions = (to.meta as RouteMetaAuth).requiresPerm
        if (requiredPermissions && requiredPermissions.length > 0) {
            if (AuthService.hasAnyPermission(requiredPermissions)) {
                return true
            }

            // Manual entry deliberately reuses the Assess view, but creating an item has
            // always required ASSESS_CREATE rather than ASSESS_ACCESS. Restrict the exception
            // to the two handoff query parameters so /assess itself remains inaccessible.
            const isManualEntryHandoff =
                to.name === 'assess' && (to.query['manualSource'] !== undefined || to.query['manualEntry'] === 'true')
            if (isManualEntryHandoff && AuthService.hasPermission(Permissions.ASSESS_CREATE)) {
                return true
            }
            return { path: '/' }
        }
        return true
    }

    return true
})

// Set page title after navigation.
router.afterEach((to) => {
    const title = (to.meta as RouteMetaAuth).title
    document.title = typeof title === 'string' ? title : 'Taranis NG'
})

export default router
