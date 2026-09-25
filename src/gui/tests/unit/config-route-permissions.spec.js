import { describe, expect, it } from 'vitest'
import router from '@/router'
import { configLinks, filterConfigLinks } from '@/config/config-nav-links'

const groupedRoutes = {
    access_management: [
        'CONFIG_USER_ACCESS',
        'CONFIG_ROLE_ACCESS',
        'CONFIG_ACL_ACCESS',
        'CONFIG_ORGANIZATION_ACCESS',
        'CONFIG_AUTH_PROVIDER_ACCESS'
    ],
    collectors: ['CONFIG_OSINT_SOURCE_ACCESS', 'CONFIG_OSINT_SOURCE_GROUP_ACCESS', 'CONFIG_COLLECTORS_NODE_ACCESS'],
    presenters: ['CONFIG_PRODUCT_TYPE_ACCESS', 'CONFIG_PRESENTERS_NODE_ACCESS'],
    publishers: ['CONFIG_PUBLISHER_PRESET_ACCESS', 'CONFIG_PUBLISHERS_NODE_ACCESS'],
    bots: ['CONFIG_BOT_PRESET_ACCESS', 'CONFIG_BOTS_NODE_ACCESS'],
    remote: ['CONFIG_REMOTE_ACCESS_ACCESS', 'CONFIG_REMOTE_NODE_ACCESS'],
    reports: ['CONFIG_REPORT_TYPE_ACCESS', 'CONFIG_ATTRIBUTE_ACCESS'],
    data_providers: ['CONFIG_DATA_PROVIDER_ACCESS', 'CONFIG_AI_ACCESS']
}

describe('grouped configuration route permissions', () => {
    it.each(Object.entries(groupedRoutes))('%s requires any child access permission', (routeName, permissions) => {
        const route = router.getRoutes().find(({ name }) => name === routeName)

        expect(route).toBeDefined()
        expect(route.meta.requiresPerm).toEqual(permissions)
    })

    it.each(Object.entries(groupedRoutes))('%s navigation declares the same child permissions', (routeName, permissions) => {
        const route = router.getRoutes().find(({ name }) => name === routeName)
        const link = configLinks.find(({ route: path }) => path === route.path)

        expect(link).toBeDefined()
        expect(link.permissions).toEqual(permissions)
    })

    it.each(Object.entries(groupedRoutes).flatMap(([routeName, permissions]) => permissions.map((permission) => [routeName, permission])))(
        'shows %s navigation to a user with only %s',
        (routeName, permission) => {
            const route = router.getRoutes().find(({ name }) => name === routeName)
            const visibleRoutes = filterConfigLinks((candidate) => candidate === permission).map(({ route: path }) => path)

            expect(visibleRoutes).toContain(route.path)
        }
    )
})
