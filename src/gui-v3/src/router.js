import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useUserStore } from '@/stores/user'
import AuthService from '@/services/auth_service'
import Permissions from '@/services/permissions'

const routes = [
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
    path: '/myassets',
    redirect: '/myassets/group/all'
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
    path: '/config/external',
    name: 'external',
    components: {
      default: () => import('./views/admin/ExternalView.vue'),
      nav: () => import('./views/nav/ConfigNav.vue')
    },
    meta: { requiresAuth: true, requiresPerm: [Permissions.MY_ASSETS_CONFIG] }
  },
  {
    path: '/config',
    name: 'config',
    components: {
      default: () => import('./views/admin/ConfigView.vue'),
      nav: () => import('./views/nav/ConfigNav.vue')
    },
    meta: { requiresAuth: true, requiresPerm: [Permissions.CONFIG_ACCESS] }
  },
  {
    path: '/config/organizations',
    name: 'organization',
    components: {
      default: () => import('./views/admin/OrganizationsView.vue'),
      nav: () => import('./views/nav/ConfigNav.vue')
    },
    meta: { requiresAuth: true, requiresPerm: [Permissions.CONFIG_ORGANIZATION_ACCESS] }
  },
  {
    path: '/config/roles',
    name: 'roles',
    components: {
      default: () => import('./views/admin/RolesView.vue'),
      nav: () => import('./views/nav/ConfigNav.vue')
    },
    meta: { requiresAuth: true, requiresPerm: [Permissions.CONFIG_ROLE_ACCESS] }
  },
  {
    path: '/config/acls',
    name: 'acls',
    components: {
      default: () => import('./views/admin/ACLEntriesView.vue'),
      nav: () => import('./views/nav/ConfigNav.vue')
    },
    meta: { requiresAuth: true, requiresPerm: [Permissions.CONFIG_ACL_ACCESS] }
  },
  {
    path: '/config/users',
    name: 'users',
    components: {
      default: () => import('./views/admin/UsersView.vue'),
      nav: () => import('./views/nav/ConfigNav.vue')
    },
    meta: { requiresAuth: true, requiresPerm: [Permissions.CONFIG_USER_ACCESS] }
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
    path: '/config/bots',
    name: 'bots',
    components: {
      default: () => import('./views/admin/BotsView.vue'),
      nav: () => import('./views/nav/ConfigNav.vue')
    },
    meta: { requiresAuth: true }
  },

  {
    path: '/config/reportitems/attributes',
    name: 'attributes',
    components: {
      default: () => import('./views/admin/AttributesView.vue'),
      nav: () => import('./views/nav/ConfigNav.vue')
    },
    meta: { requiresAuth: true, requiresPerm: [Permissions.CONFIG_ATTRIBUTE_ACCESS] }
  },
  {
    path: '/config/reportitems/types',
    name: 'report_types',
    components: {
      default: () => import('./views/admin/ReportTypesView.vue'),
      nav: () => import('./views/nav/ConfigNav.vue')
    },
    meta: { requiresAuth: true, requiresPerm: [Permissions.CONFIG_SETTINGS_ACCESS] }
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
  }
]

const router = createRouter({
  history: createWebHistory('/v2/'),
  routes
})

// Global navigation guard for authentication and permissions
router.beforeEach((to) => {
  // Initialize user from JWT if not already done
  const authStore = useAuthStore()
  const userStore = useUserStore()
  if (authStore.jwt && !userStore.user.id) {
    const userData = authStore.getUserData
    if (userData) {
      userStore.setUser(userData)
    }
  }

  if (to.matched.some((record) => record.meta.requiresAuth)) {
    if (!AuthService.isAuthenticated()) {
      if (!authStore.externalLoginUrl) {
        return {
          path: '/login',
          query: { redirect: to.path }
        }
      }
      window.location = authStore.externalLoginUrl
      return false
    } else if (to.path === '/') {
      // Redirect root to appropriate default page based on permissions
      if (AuthService.hasPermission(Permissions.ASSESS_ACCESS)) {
        return { path: '/dashboard' }
      } else if (AuthService.hasPermission(Permissions.CONFIG_ACCESS)) {
        return { path: '/config' }
      } else if (AuthService.hasPermission(Permissions.MY_ASSETS_ACCESS)) {
        return { path: '/myassets' }
      }
      return true
    } else {
      // Check permissions for the route
      if (to.meta.requiresPerm && to.meta.requiresPerm.length > 0) {
        if (AuthService.hasAnyPermission(to.meta.requiresPerm)) {
          return true
        }
        return { path: '/' }
      }
      return true
    }
  }

  return true
})

// Set page title after navigation
router.afterEach((to) => {
  document.title = to.meta.title || 'Taranis NG'
})

export default router
