import { describe, expect, it } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'
import {
    createRemoteAnalyzePath,
    createRemoteAnalyzeScope,
    createLegacyAnalyzeRedirect,
    getAnalyzeGroupName,
    getLegacyAnalyzeGroupName,
    isRemoteAnalyzeRoute
} from '@/utils/analyze-routing'

describe('Analyze routing', () => {
    it('preserves the exact remote group name and encodes URL-sensitive characters', async () => {
        const groupName = 'Threat Research / EU?#'
        const router = createRouter({
            history: createMemoryHistory(),
            routes: [{ path: '/analyze/:scope', name: 'analyze', component: { template: '<div />' } }]
        })

        await router.push(createRemoteAnalyzePath(groupName))

        expect(router.currentRoute.value.params['scope']).toBe(createRemoteAnalyzeScope(groupName))
        expect(getAnalyzeGroupName(router.currentRoute.value)).toBe(groupName)
        expect(isRemoteAnalyzeRoute(router.currentRoute.value)).toBe(true)
        expect(router.currentRoute.value.path).toContain('%2F')
        expect(router.currentRoute.value.path).toContain('%3F%23')
    })

    it('recognizes local scope from route parameters', () => {
        const route = { params: { scope: 'local' } }

        expect(isRemoteAnalyzeRoute(route)).toBe(false)
        expect(getAnalyzeGroupName(route)).toBe('')
    })

    it('retains the legacy dash-for-space bookmark interpretation', () => {
        expect(getLegacyAnalyzeGroupName('upstream-node')).toBe('upstream node')
    })

    it('redirects a legacy bookmark to the canonical route without losing query or hash', async () => {
        const router = createRouter({
            history: createMemoryHistory(),
            routes: [
                { path: '/analyze/group/:groupName', redirect: createLegacyAnalyzeRedirect },
                { path: '/analyze/:scope', name: 'analyze', component: { template: '<div />' } }
            ]
        })

        await router.push('/analyze/group/upstream-node?search=urgent#results')

        expect(router.currentRoute.value.name).toBe('analyze')
        expect(router.currentRoute.value.params['scope']).toBe('group-upstream node')
        expect(router.currentRoute.value.query).toEqual({ search: 'urgent' })
        expect(router.currentRoute.value.hash).toBe('#results')
    })
})
