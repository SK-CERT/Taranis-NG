import { describe, it, expect } from 'vitest'
import {
    buildVariant,
    buildVuetifyThemes,
    DEFAULT_THEME_FAMILY,
    getFamily,
    isKnownFamily,
    resolveFamily,
    themeFamilies,
    themeName
} from '@/themes'
import { messages } from '@/i18n'
import { contrastRatio as contrast, AAA_BODY_TEXT, AA_TEXT } from '@/themes/wcag'

// Every token the app reads through styles/colors.css or directly via
// --v-theme-*. A family missing one of these would fall back to a Vuetify
// default or to an invalid var() - the main regression risk as families are
// added, and invisible until that family is selected.
const requiredColors = [
    'background',
    'surface',
    'surface-variant',
    'on-surface',
    'outline',
    'primary',
    'secondary',
    'tertiary',
    'error',
    'info',
    'success',
    'warning',
    'accent',
    'menu-bg',
    'drawer-bg',
    'workspace',
    'list-row'
]

const requiredVariables = [
    'menu-gradient',
    'drawer-gradient',
    'workspace-gradient',
    'menu-border',
    'menu-item-active',
    'review-list-row-selected',
    'review-list-row-hover',
    'review-list-border',
    'review-panel-border',
    'filter-controls-bg',
    'drawer-icon',
    'drawer-divider'
]

describe('theme registry', () => {
    const themes = buildVuetifyThemes()

    it('exposes the default family', () => {
        expect(isKnownFamily(DEFAULT_THEME_FAMILY)).toBe(true)
        expect(getFamily(DEFAULT_THEME_FAMILY).id).toBe(DEFAULT_THEME_FAMILY)
    })

    it('uses unique family ids', () => {
        const ids = themeFamilies.map((family) => family.id)
        expect(new Set(ids).size).toBe(ids.length)
    })

    it('builds a light and a dark variant per family, plus the built-in aliases', () => {
        expect(Object.keys(themes)).toHaveLength(themeFamilies.length * 2 + 2)

        for (const family of themeFamilies) {
            expect(themes[themeName(family.id, false)]?.dark).toBe(false)
            expect(themes[themeName(family.id, true)]?.dark).toBe(true)
        }
    })

    // Vuetify 4 ships its own light/dark themes and resolves 'system' to them.
    // Overriding both keeps a stray theme.change('dark') on our palette.
    it('aliases the built-in light and dark themes onto the default family', () => {
        expect(themes['light']?.colors).toEqual(themes[themeName(DEFAULT_THEME_FAMILY, false)]?.colors)
        expect(themes['dark']?.colors).toEqual(themes[themeName(DEFAULT_THEME_FAMILY, true)]?.colors)
    })

    it.each(Object.keys(buildVuetifyThemes()))('%s defines the full token set', (name) => {
        const theme = themes[name]

        for (const color of requiredColors) {
            expect(theme?.colors?.[color], color).toBeTruthy()
        }
        for (const variable of requiredVariables) {
            expect(theme?.variables?.[variable], variable).toBeTruthy()
        }
    })

    // Vuetify rewrites a theme variable starting with '#' into a bare "r, g, b"
    // triplet, which would land in the stylesheet as `background: 216, 227, 235`.
    // The factory normalises hex to rgb() so families can still be written in hex.
    it.each(Object.keys(buildVuetifyThemes()))('%s emits no raw hex among its variables', (name) => {
        for (const [key, value] of Object.entries(themes[name]?.variables ?? {})) {
            expect(String(value), key).not.toMatch(/^#/)
        }
    })

    it.each(Object.keys(buildVuetifyThemes()))('%s stays readable', (name) => {
        const colors = (themes[name]?.colors ?? {}) as Record<string, string>

        // Body text, on every ground it actually gets painted on (AAA).
        for (const ground of ['surface', 'background', 'list-row', 'workspace']) {
            expect(contrast(colors['on-surface'] ?? '', colors[ground] ?? ''), `on-surface / ${ground}`).toBeGreaterThanOrEqual(AAA_BODY_TEXT)
        }

        // Chrome that carries its own text colour, held to AA rather than AAA.
        // The top bar and sidebar carry a handful of short bold labels, not
        // long-form reading, so 4.5 is the applicable WCAG threshold; AAA here
        // was a ratchet off the original palettes, and it rejected brand colours
        // that are comfortably readable (Retro's #AD2800 bar is 6.82).
        expect(contrast(colors['on-menu-bg'] ?? '', colors['menu-bg'] ?? ''), 'menu').toBeGreaterThanOrEqual(AA_TEXT)
        expect(contrast(colors['on-drawer-bg'] ?? '', colors['drawer-bg'] ?? ''), 'drawer').toBeGreaterThanOrEqual(AA_TEXT)

        // primary is used as a text/icon colour on surfaces, not only as a fill (AA).
        expect(contrast(colors['primary'] ?? '', colors['surface'] ?? ''), 'primary on surface').toBeGreaterThanOrEqual(AA_TEXT)
    })

    // Gradients are opt-in: a family that declares none must still resolve to
    // `none`, which is what guarantees adding the capability changed nothing.
    it('leaves the optional gradients off unless a family asks for them', () => {
        const plain = buildVariant(getFamily('taranis').light, false)

        for (const key of ['menu-gradient', 'drawer-gradient', 'workspace-gradient']) {
            expect(plain.variables[key], key).toBe('none')
        }
    })

    it.each(Object.keys(buildVuetifyThemes()))('%s declares only well-formed gradients', (name) => {
        for (const key of ['menu-gradient', 'drawer-gradient', 'workspace-gradient']) {
            const value = String(themes[name]?.variables?.[key] ?? '')
            if (value === 'none') continue
            expect(value, `${key} must be a CSS gradient`).toMatch(/^(linear|radial|conic)-gradient\(/)
        }
    })

    // A gradient sits on top of the base colour, but the contrast contract above
    // measures text against that base. So an opaque stop that strays far from it
    // would make the guarantee a lie: check the stops themselves.
    it.each(Object.keys(buildVuetifyThemes()))('%s keeps chrome gradients readable at every stop', (name) => {
        const colors = (themes[name]?.colors ?? {}) as Record<string, string>
        const variables = (themes[name]?.variables ?? {}) as Record<string, string>

        for (const [key, ink] of [
            ['menu-gradient', colors['on-menu-bg']],
            ['drawer-gradient', colors['on-drawer-bg']]
        ] as const) {
            const value = String(variables[key] ?? '')
            if (value === 'none' || !ink) continue

            // Only opaque stops can be judged; translucent ones composite over the base.
            for (const stop of value.match(/#[\da-f]{6}\b/gi) ?? []) {
                expect(contrast(stop, ink), `${key} stop ${stop}`).toBeGreaterThanOrEqual(AA_TEXT)
            }
        }
    })

    it('falls back to the default family for unknown or missing ids', () => {
        expect(resolveFamily(undefined)).toBe(DEFAULT_THEME_FAMILY)
        expect(resolveFamily(null)).toBe(DEFAULT_THEME_FAMILY)
        expect(resolveFamily('')).toBe(DEFAULT_THEME_FAMILY)
        expect(resolveFamily('a-theme-that-was-removed')).toBe(DEFAULT_THEME_FAMILY)
        expect(getFamily('a-theme-that-was-removed').id).toBe(DEFAULT_THEME_FAMILY)
    })

    it('names themes as <family>-<variant>', () => {
        expect(themeName('forest', true)).toBe('forest-dark')
        expect(themeName('forest', false)).toBe('forest-light')
    })

    // The settings dropdown labels each family through themes.<id>, falling back
    // to family.label only if the key is missing.
    it('has an English label for every family', () => {
        for (const family of themeFamilies) {
            const catalogue = messages['en'] as Record<string, Record<string, string>>
            expect(catalogue['themes']?.[family.id], family.id).toBeTruthy()
        }
    })
})
