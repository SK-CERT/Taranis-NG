import { useAuthStore } from '@/stores/auth'
import { useUserStore } from '@/stores/user'

const AuthService = {
  /**
   * Check if user is authenticated
   * @returns {boolean}
   */
  isAuthenticated() {
    const authStore = useAuthStore()
    const jwt = authStore.jwt
    if (!jwt || jwt.split('.').length < 3) {
      return false
    }
    try {
      const data = JSON.parse(atob(jwt.split('.')[1]))
      const exp = new Date(data.exp * 1000)
      const now = new Date()
      return now < exp
    } catch (error) {
      return false
    }
  },

  /**
   * Check if token needs refresh (within 5 minutes of expiry)
   * @returns {boolean}
   */
  needTokenRefresh() {
    const authStore = useAuthStore()
    const jwt = authStore.jwt
    if (!jwt || jwt.split('.').length < 3) {
      return false
    }
    try {
      const data = JSON.parse(atob(jwt.split('.')[1]))
      const exp = new Date((data.exp - 300) * 1000) // 300 seconds = 5 minutes
      const now = new Date()
      return now > exp
    } catch (error) {
      return false
    }
  },

  hasPermission(permission) {
    const userStore = useUserStore()
    const permissions = userStore.permissions
    return permissions && permissions.includes(permission)
  },

  hasAnyPermission(permissionList) {
    if (!permissionList || permissionList.length === 0) {
      return true
    }
    return permissionList.some((permission) => this.hasPermission(permission))
  },

  hasAllPermissions(permissionList) {
    if (!permissionList || permissionList.length === 0) {
      return true
    }
    return permissionList.every((permission) => this.hasPermission(permission))
  }
}

export default AuthService
