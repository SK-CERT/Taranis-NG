import { PERMISSIONS as PERMISSION_VALUES } from '@/types/permissions'
import type { PermissionKey } from '@/types/permissions'

const permissionMap: Record<PermissionKey, PermissionKey> = {} as Record<PermissionKey, PermissionKey>

for (const permission of PERMISSION_VALUES) {
    permissionMap[permission] = permission
}

const Permissions = Object.freeze(permissionMap)

export default Permissions
