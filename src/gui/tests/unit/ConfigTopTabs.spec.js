/**
 * Every configuration page's top tab row stays in view: it sticks under the app bar while the
 * page scrolls. On a narrow screen it still scrolls sideways, so it must not be made to wrap.
 *
 * The behaviour comes from the global `.config-tabs` rules in App.vue, so each view has to
 * carry the class on its top `<v-tabs>`. The views are read from the source, so a new
 * configuration page with tabs is covered the day it is written.
 */
import { describe, expect, it } from 'vitest'

const views = import.meta.glob('/src/views/admin/*.vue', { query: '?raw', import: 'default', eager: true })
const appSource = import.meta.glob('/src/App.vue', { query: '?raw', import: 'default', eager: true })['/src/App.vue']

const topTabs = Object.entries(views)
    .map(([path, source]) => [path.split('/').pop(), source.match(/<v-tabs\b[^>]*>/u)?.[0]])
    .filter(([, tag]) => tag)

describe('configuration top tabs', () => {
    it('finds the tabbed configuration views', () => {
        expect(topTabs.map(([name]) => name)).toContain('AccessManagementView.vue')
    })

    it.each(topTabs)('%s marks its top tabs as configuration tabs', (_name, tag) => {
        expect(tag).toMatch(/class="[^"]*\bconfig-tabs\b/u)
    })

    it('keeps the tab row under the app bar while the page scrolls', () => {
        expect(appSource).toMatch(/\.config-tabs\.v-tabs \{[^}]*position: sticky;[^}]*top: var\(--v-layout-top/u)
    })

    it('still scrolls sideways on a narrow screen and lets configuration pages grow with their content', () => {
        expect(appSource).not.toMatch(/\.config-tabs[^{]*\{[^}]*flex-wrap/u)
        expect(appSource).not.toMatch(/\.config-tabs \.v-slide-group/u)
        expect(appSource).toMatch(/\.v-main\.configuration-view \{[^}]*height: auto;/u)
    })
})
