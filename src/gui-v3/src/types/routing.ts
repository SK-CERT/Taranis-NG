import type { PermissionKey } from './permissions'

export interface AppRouteMeta {
    title?: string
    requiresAuth?: boolean
    requiresPerm?: PermissionKey[]
}
