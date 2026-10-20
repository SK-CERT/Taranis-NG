import type { PermissionKey } from './permissions'

export interface AppRouteMeta {
    title?: string
    requiresAuth?: boolean
    requiresPerm?: PermissionKey[]
}

export type GroupNavItem = {
    id: string | number
    icon?: string
    color?: string | null
    title: string
    translate?: boolean | null
    route: string
    // Show when the user has ANY of these permissions; empty is unrestricted.
    permissions?: PermissionKey[]
    separator?: boolean
}
