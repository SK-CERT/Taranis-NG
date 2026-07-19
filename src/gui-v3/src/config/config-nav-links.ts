import type { PermissionKey } from '@/types/permissions'

export type ConfigLink = {
    id: number
    icon?: string
    title?: string
    route?: string
    permission?: PermissionKey
    // If set, the link is shown when the user has ANY of these permissions.
    permissions?: PermissionKey[]
    translate?: boolean
    separator?: boolean
    color?: string
}

// Shared list of configuration navigation links used by both the config
// sidebar (ConfigNav) and the router redirect for `/config`.
export const configLinks: ConfigLink[] = [
    {
        id: 1,
        icon: 'mdi-account-key',
        title: 'nav_menu.access_management',
        route: '/config/access-management',
        permissions: [
            'CONFIG_USER_ACCESS',
            'CONFIG_ROLE_ACCESS',
            'CONFIG_ACL_ACCESS',
            'CONFIG_ORGANIZATION_ACCESS',
            'CONFIG_AUTH_PROVIDER_ACCESS'
        ],
        translate: true
    },
    {
        id: 2,
        icon: 'mdi-download-network',
        title: 'nav_menu.collectors',
        route: '/config/collectors',
        translate: true
    },
    {
        id: 3,
        icon: 'mdi-presentation',
        title: 'nav_menu.presenters',
        route: '/config/presenters',
        translate: true
    },
    {
        id: 4,
        icon: 'mdi-upload-network',
        title: 'nav_menu.publishers',
        route: '/config/publishers',
        translate: true
    },
    {
        id: 5,
        icon: 'mdi-file-table',
        title: 'nav_menu.reports',
        route: '/config/reports',
        permissions: ['CONFIG_REPORT_TYPE_ACCESS', 'CONFIG_ATTRIBUTE_ACCESS'],
        translate: true
    },
    { id: 7, icon: 'mdi-robot', title: 'nav_menu.bots', route: '/config/bots', translate: true },
    {
        id: 8,
        icon: 'mdi-remote',
        title: 'nav_menu.remote',
        route: '/config/remote',
        translate: true
    },
    {
        id: 13,
        icon: 'mdi-web',
        title: 'nav_menu.public_web',
        route: '/config/public-web',
        permission: 'CONFIG_PUBLIC_WEB_NODE_ACCESS',
        translate: true
    },
    {
        id: 9,
        icon: 'mdi-application-cog-outline',
        title: 'nav_menu.settings',
        route: '/config/settings',
        permission: 'CONFIG_SETTINGS_ACCESS',
        translate: true
    },
    {
        id: 10,
        icon: 'mdi-format-list-text',
        title: 'nav_menu.word_lists',
        route: '/config/wordlists',
        permission: 'CONFIG_WORD_LIST_ACCESS',
        translate: true
    },
    {
        id: 11,
        icon: 'mdi-state-machine',
        title: 'nav_menu.workflow',
        route: '/config/workflow',
        permission: 'CONFIG_WORKFLOW_ACCESS',
        translate: true
    },
    {
        id: 12,
        icon: 'mdi-cloud-arrow-down',
        title: 'nav_menu.data_providers',
        route: '/config/data-providers',
        permission: 'CONFIG_DATA_PROVIDER_ACCESS',
        translate: true
    }
]

// Filter links based on permissions and remove leading/trailing/adjacent separators.
export function filterConfigLinks(checkPermission: (permission: PermissionKey) => boolean): ConfigLink[] {
    const filtered: ConfigLink[] = []

    for (let i = 0; i < configLinks.length; i++) {
        const link = configLinks[i]
        if (!link) {
            continue
        }

        if (link.separator) {
            // Only add separator if there are items before it and it's not the first item
            const lastFiltered = filtered[filtered.length - 1]
            if (filtered.length > 0 && lastFiltered && !lastFiltered.separator) {
                filtered.push(link)
            }
        } else {
            const allowed = link.permissions
                ? link.permissions.some((permission) => checkPermission(permission))
                : !link.permission || checkPermission(link.permission)
            if (allowed) {
                filtered.push(link)
            }
        }
    }

    // Remove leading separator
    const firstFiltered = filtered[0]
    if (filtered.length > 0 && firstFiltered && firstFiltered.separator) {
        filtered.shift()
    }

    // Remove trailing separator
    const lastFiltered = filtered[filtered.length - 1]
    if (filtered.length > 0 && lastFiltered && lastFiltered.separator) {
        filtered.pop()
    }

    return filtered
}

// Return the route of the first accessible (non-separator) config link, if any.
export function getFirstConfigRoute(checkPermission: (permission: PermissionKey) => boolean): string | undefined {
    const firstLink = filterConfigLinks(checkPermission).find((link) => !link.separator && link.route)
    return firstLink?.route
}
