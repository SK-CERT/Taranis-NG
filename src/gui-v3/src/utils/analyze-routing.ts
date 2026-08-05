import type { RouteLocationNormalized, RouteLocationNormalizedLoaded, RouteLocationRaw } from 'vue-router'

const LOCAL_SCOPE = 'local'
const REMOTE_SCOPE_PREFIX = 'group-'

type AnalyzeRoute = Pick<RouteLocationNormalizedLoaded, 'params'>

const routeScope = (route: AnalyzeRoute): string => {
    const scope = route.params['scope']
    if (typeof scope === 'string') return scope
    if (Array.isArray(scope)) return scope[0] || LOCAL_SCOPE
    return LOCAL_SCOPE
}

export const createRemoteAnalyzeScope = (groupName: string): string => `${REMOTE_SCOPE_PREFIX}${groupName}`

export const createRemoteAnalyzePath = (groupName: string): string => {
    return `/analyze/${encodeURIComponent(createRemoteAnalyzeScope(groupName))}`
}

export const isRemoteAnalyzeRoute = (route: AnalyzeRoute): boolean => routeScope(route) !== LOCAL_SCOPE

export const getAnalyzeGroupName = (route: AnalyzeRoute): string => {
    const scope = routeScope(route)
    if (scope === LOCAL_SCOPE) return ''
    return scope.startsWith(REMOTE_SCOPE_PREFIX) ? scope.slice(REMOTE_SCOPE_PREFIX.length) : scope
}

// Vue 2 replaced spaces with dashes when it generated these bookmarks. Preserve
// that historical interpretation while new links retain the exact group name.
export const getLegacyAnalyzeGroupName = (groupName: string): string => groupName.replaceAll('-', ' ')

export const createLegacyAnalyzeRedirect = (route: Pick<RouteLocationNormalized, 'params' | 'query' | 'hash'>): RouteLocationRaw => ({
    name: 'analyze',
    params: {
        scope: createRemoteAnalyzeScope(getLegacyAnalyzeGroupName(String(route.params['groupName'])))
    },
    query: route.query,
    hash: route.hash
})
