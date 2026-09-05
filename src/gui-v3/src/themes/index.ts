import type { ThemeDefinition } from 'vuetify'
import type { ThemeFamily, VariantSpec } from './types'
import { taranis } from './taranis'
import { slate } from './slate'
import { forest } from './forest'
import { amber } from './amber'
import { contrast } from './contrast'
import { doll } from './doll'
import { bubblegum } from './bubblegum'
import { autumn } from './autumn'
import { retro } from './retro'
import { valentine } from './valentine'
import { summer } from './summer'
import { vintage } from './vintage'
import { cesnet } from './cesnet'
import { skcert } from './skcert'
import { lavender } from './lavender'

export type { ThemeFamily, VariantSpec } from './types'

/**
 * Every selectable theme family. Registering a new one is this list plus the
 * file it imports - no migration, no CSS, no changes to the settings UI.
 */
export const themeFamilies: ThemeFamily[] = [
    taranis,
    slate,
    forest,
    amber,
    contrast,
    doll,
    bubblegum,
    autumn,
    retro,
    valentine,
    summer,
    vintage,
    cesnet,
    skcert,
    lavender
]

export const DEFAULT_THEME_FAMILY = taranis.id

/** Vuetify has no notion of families, so a family + variant collapses to a name. */
export const themeName = (family: string, dark: boolean): string => `${family}-${dark ? 'dark' : 'light'}`

export const isKnownFamily = (id?: string | null): boolean => themeFamilies.some((family) => family.id === id)

/** Guards against a stored setting naming a family that no longer ships. */
export const resolveFamily = (id?: string | null): string => (isKnownFamily(id) ? (id as string) : DEFAULT_THEME_FAMILY)

export const getFamily = (id?: string | null): ThemeFamily => themeFamilies.find((family) => family.id === resolveFamily(id)) as ThemeFamily

/**
 * Vuetify rewrites any theme *variable* whose value starts with '#' into a bare
 * "r, g, b" triplet - useful for its own colour variables, but it would turn a
 * plain background into an invalid `background: 216, 227, 235`. Handing it an
 * rgb()/rgba() string instead makes it pass the value through untouched, so
 * families can still be written in hex.
 */
const asCssColor = (value: string): string => {
    const hex = /^#([\da-f]{3}|[\da-f]{6})$/i.exec(value.trim())
    if (!hex) return value

    const digits = hex[1] ?? ''
    const full = digits.length === 3 ? [...digits].map((digit) => digit + digit).join('') : digits
    const [r, g, b] = [0, 2, 4].map((offset) => parseInt(full.slice(offset, offset + 2), 16))

    return `rgb(${r}, ${g}, ${b})`
}

/** Only emit a key when the family actually pins it, so Vuetify's own default survives. */
const optional = (key: string, value?: string): Record<string, string> => (value ? { [key]: value } : {})

const mapValues = (source: Record<string, string>, transform: (value: string) => string): Record<string, string> =>
    Object.fromEntries(Object.entries(source).map(([key, value]) => [key, transform(value)]))

const buildVariant = (spec: VariantSpec, dark: boolean): ThemeDefinition => ({
    dark,
    colors: {
        'background': spec.background,
        'surface': spec.surface,
        'surface-variant': spec.surfaceVariant,
        'on-surface': spec.onSurface,
        'outline': spec.outline,
        'primary': spec.primary,
        'secondary': spec.secondary,
        'tertiary': spec.tertiary,
        'error': spec.error,
        'info': spec.info,
        'success': spec.success,
        'warning': spec.warning,
        'accent': spec.accent,
        // Extended surfaces. Vuetify generates --v-theme-<name>, .bg-<name>,
        // .text-<name>, .border-<name> and a contrasting on-<name> for each.
        'menu-bg': spec.menuBg,
        'drawer-bg': spec.drawerBg,
        'workspace': spec.workspace,
        'list-row': spec.listRow,
        ...optional('surface-bright', spec.surfaceBright),
        ...optional('surface-light', spec.surfaceLight),
        ...optional('on-surface-variant', spec.onSurfaceVariant),
        ...optional('on-primary', spec.onPrimary),
        ...optional('on-secondary', spec.onSecondary),
        ...optional('on-tertiary', spec.onTertiary),
        ...optional('on-error', spec.onError),
        ...optional('on-info', spec.onInfo),
        ...optional('on-success', spec.onSuccess),
        ...optional('on-warning', spec.onWarning),
        ...optional('on-menu-bg', spec.onMenuBg),
        ...optional('on-drawer-bg', spec.onDrawerBg)
    },
    // Values carrying alpha cannot be Vuetify colors (a color must decompose
    // into an opaque "r, g, b" triplet), so they ride along as theme variables.
    // The keys match the legacy custom-property names consumed across the app;
    // styles/colors.css maps --v-<key> back onto --<key> in one place.
    variables: mapValues(
        {
            'menu-border': spec.menuBorder ?? '1px solid rgba(var(--v-theme-on-menu-bg), 0.13)',
            'menu-item-active': spec.menuItemActive ?? 'rgba(var(--v-theme-accent), 0.22)',
            'review-list-row-selected': spec.listRowSelected ?? (dark ? 'rgba(var(--v-theme-primary), 0.22)' : '#FFF3CD'),
            'review-list-row-hover': spec.listRowHover ?? `rgba(var(--v-theme-primary), ${dark ? 0.14 : 0.07})`,
            'review-list-border': spec.listBorder ?? 'rgba(var(--v-theme-outline), 0.34)',
            'review-panel-border': spec.panelBorder ?? 'rgba(var(--v-theme-outline), 0.58)',
            'filter-controls-bg': spec.filterControlsBg ?? spec.surfaceVariant,
            'drawer-icon': spec.drawerIcon ?? 'rgb(var(--v-theme-on-drawer-bg))',
            'drawer-divider': spec.drawerDivider ?? 'rgba(var(--v-theme-on-drawer-bg), 0.2)'
        },
        asCssColor
    )
})

/**
 * Expand every family into the flat `{ [name]: ThemeDefinition }` map Vuetify
 * expects.
 *
 * `light` and `dark` are additionally aliased onto the default family. Vuetify 4
 * ships built-in themes under those names and defaults `defaultTheme` to
 * 'system' (which resolves to them), so without the aliases any stale
 * `theme.change('dark')` would silently drop the app onto the stock Vuetify
 * palette instead of ours.
 */
export const buildVuetifyThemes = (): Record<string, ThemeDefinition> => {
    const themes: Record<string, ThemeDefinition> = {}

    for (const family of themeFamilies) {
        themes[themeName(family.id, false)] = buildVariant(family.light, false)
        themes[themeName(family.id, true)] = buildVariant(family.dark, true)
    }

    const fallback = getFamily(DEFAULT_THEME_FAMILY)
    themes['light'] = buildVariant(fallback.light, false)
    themes['dark'] = buildVariant(fallback.dark, true)

    return themes
}
