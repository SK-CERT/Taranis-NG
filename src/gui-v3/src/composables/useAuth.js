import { computed } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useUserStore } from '@/stores/user'
import AuthService from '@/services/auth_service'
import Permissions from '@/services/permissions'

/**
 * Composable for authentication utilities
 * Provides common auth methods and permission checking
 */
export function useAuth() {
  const authStore = useAuthStore()
  const userStore = useUserStore()

  /**
   * Logout user and redirect
   */
  const logout = () => {
    return authStore.logout().then(() => {
      if (authStore.hasExternalLogoutUrl) {
        window.location.href = authStore.logoutURL
      } else {
        window.location.reload()
      }
    })
  }

  /**
   * Check if user is authenticated
   */
  const isAuthenticated = () => {
    return AuthService.isAuthenticated()
  }

  /**
   * Check if token needs refresh
   */
  const needTokenRefresh = () => {
    return AuthService.needTokenRefresh()
  }

  /**
   * Check if user has specific permission
   */
  const checkPermission = (permission) => {
    return AuthService.hasPermission(permission)
  }

  /**
   * Check if user has any of the provided permissions
   */
  const checkAnyPermission = (permissions) => {
    return AuthService.hasAnyPermission(permissions)
  }

  /**
   * Check if user has all of the provided permissions
   */
  const checkAllPermissions = (permissions) => {
    return AuthService.hasAllPermissions(permissions)
  }

  const getUserId = () => {
    return userStore.userId
  }

  return {
    // State
    permissions: Permissions,

    // Computed
    user: computed(() => userStore.user),
    isAuth: computed(() => authStore.isAuthenticated),
    hasExternalLogin: computed(() => authStore.hasExternalLoginUrl),
    hasExternalLogout: computed(() => authStore.hasExternalLogoutUrl),

    // Methods
    logout,
    isAuthenticated,
    needTokenRefresh,
    getUserId,
    checkPermission,
    checkAnyPermission,
    checkAllPermissions
  }
}
