import { describe, expect, it } from 'vitest'
import router from '@/router'

const legacyConfigRoutes = [
    ['/config/users', '/config/access-management', 'users'],
    ['/config/roles', '/config/access-management', 'roles'],
    ['/config/acls', '/config/access-management', 'acls'],
    ['/config/organizations', '/config/access-management', 'organizations'],
    ['/config/collectors/sources', '/config/collectors', 'sources'],
    ['/config/collectors/groups', '/config/collectors', 'groups'],
    ['/config/collectors/nodes', '/config/collectors', 'nodes'],
    ['/config/presenters/nodes', '/config/presenters', 'nodes'],
    ['/config/product/types', '/config/presenters', 'types'],
    ['/config/publishers/nodes', '/config/publishers', 'nodes'],
    ['/config/publishers/presets', '/config/publishers', 'presets'],
    ['/config/bots/nodes', '/config/bots', 'nodes'],
    ['/config/bots/presets', '/config/bots', 'presets'],
    ['/config/remote/access', '/config/remote', 'access'],
    ['/config/remote/nodes', '/config/remote', 'nodes'],
    ['/config/reportitems/types', '/config/reports', 'types'],
    ['/config/reportitems/attributes', '/config/reports', 'attributes'],
    ['/config/external/users', '/config/external', 'users'],
    ['/config/external/groups', '/config/external', 'groups'],
    ['/config/external/templates', '/config/external', 'templates']
]

describe('legacy route redirects', () => {
    it.each(legacyConfigRoutes)('%s redirects to %s?tab=%s', (legacyPath, path, tab) => {
        const route = router.getRoutes().find((candidate) => candidate.path === legacyPath)

        expect(route).toBeDefined()
        expect(route.redirect).toEqual({ path, query: { tab } })
    })

    it('maps legacy source entry to the Assess dialog handoff', () => {
        const route = router.getRoutes().find((candidate) => candidate.path === '/enter/source/:sourceId')

        expect(route).toBeDefined()
        expect(typeof route.redirect).toBe('function')
        expect(route.redirect({ params: { sourceId: 'manual-42' }, query: { from: 'bookmark' } })).toEqual({
            name: 'assess',
            params: { groupId: 'all' },
            query: { from: 'bookmark', manualSource: 'manual-42' }
        })
    })
})
