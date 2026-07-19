import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useUserStore } from '@/stores/user'
import AuthService from '@/services/auth_service'
import Permissions from '@/services/permissions'
import { getFirstConfigRoute } from '@/config/config-nav-links'
import type { PermissionKey } from '@/types/permissions'

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
        path: '/analyze',
        redirect: '/analyze/local'
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
        meta: { requiresAuth: true }
    },
    {
        path: '/config/presenters',
        name: 'presenters',
        components: {
            default: () => import('./views/admin/PresentersView.vue'),
            nav: () => import('./views/nav/ConfigNav.vue')
        },
        meta: { requiresAuth: true }
    },
    {
        path: '/config/publishers',
        name: 'publishers',
        components: {
            default: () => import('./views/admin/PublishersView.vue'),
            nav: () => import('./views/nav/ConfigNav.vue')
        },
        meta: { requiresAuth: true }
    },
    {
        path: '/config/remote',
        name: 'remote',
        components: {
            default: () => import('./views/admin/RemoteView.vue'),
            nav: () => import('./views/nav/ConfigNav.vue')
        },
        meta: { requiresAuth: true }
    },
    {
        path: '/config/public-web',
        name: 'public-web',
        components: {
            default: () => import('./views/admin/PublicWebNodesView.vue'),
            nav: () => import('./views/nav/ConfigNav.vue')
        },
        meta: { requiresAuth: true }
    },
    {
        path: '/config/bots',
        name: 'bots',
        components: {
            default: () => import('./views/admin/BotsView.vue'),
            nav: () => import('./views/nav/ConfigNav.vue')
        },
        meta: { requiresAuth: true }
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
        meta: { requiresAuth: true, requiresPerm: [Permissions.CONFIG_DATA_PROVIDER_ACCESS] }
    },
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
            if (!authStore.hasExternalLoginUrl) {
                // A failed redirect login comes back to the app route it started from,
                // carrying ?login_error=; hand that to the login page so it can report it.
                const loginError = to.query['login_error']
                return {
                    path: '/login',
                    query:
                        typeof loginError === 'string' && loginError ? { redirect: to.path, login_error: loginError } : { redirect: to.path }
                }
            }
            window.location.href = authStore.getLoginURL
            return false
        }

        if (to.path === '/') {
            // Redirect root to appropriate default page based on permissions.
            if (AuthService.hasPermission(Permissions.ASSESS_ACCESS)) {
                return { path: '/dashboard' }
            }
            if (AuthService.hasPermission(Permissions.CONFIG_ACCESS)) {
                return { path: '/config' }
            }
            return true
        }

        // Check permissions for the route.
        const requiredPermissions = (to.meta as RouteMetaAuth).requiresPerm
        if (requiredPermissions && requiredPermissions.length > 0) {
            if (AuthService.hasAnyPermission(requiredPermissions)) {
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
