import { useAuthStore } from '@/stores/auth'
import { useUserStore } from '@/stores/user'
import { parseJwtClaims } from '@/services/jwt'
import type { PermissionKey } from '@/types/permissions'

const AuthService = {
    /**
     * Check if user is authenticated.
     */
    isAuthenticated(): boolean {
        const authStore = useAuthStore()
        const jwt = authStore.jwt
        const data = parseJwtClaims(jwt)

        if (!data || typeof data.exp !== 'number') {
            return false
        }

        const exp = new Date(data.exp * 1000)
        const now = new Date()
        return now < exp
    },

    /**
     * Check if token needs refresh (within 5 minutes of expiry).
     */
    needTokenRefresh(): boolean {
        const authStore = useAuthStore()
        const jwt = authStore.jwt
        const data = parseJwtClaims(jwt)

        if (!data || typeof data.exp !== 'number') {
            return false
        }

        const exp = new Date((data.exp - 300) * 1000)
        const now = new Date()
        return now > exp
    },

    hasPermission(permission: PermissionKey): boolean {
        const userStore = useUserStore()
        const permissions = userStore.permissions
        return Boolean(permissions && permissions.includes(permission))
    },

    hasAnyPermission(permissionList: PermissionKey[] | undefined | null): boolean {
        if (!permissionList || permissionList.length === 0) {
            return true
        }
        return permissionList.some((permission) => this.hasPermission(permission))
    },

    hasAllPermissions(permissionList: PermissionKey[] | undefined | null): boolean {
        if (!permissionList || permissionList.length === 0) {
            return true
        }
        return permissionList.every((permission) => this.hasPermission(permission))
    }
}

export default AuthService
