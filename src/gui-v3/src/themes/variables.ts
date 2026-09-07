import type { VariantSpec } from './types'

/**
 * Spec field -> the Vuetify theme variable it is emitted as. These carry alpha
 * or a border shorthand, so they cannot be Vuetify colors (a color must
 * decompose into an opaque "r, g, b" triplet). The names match the legacy
 * custom-property names consumed across the app; styles/colors.css maps
 * --v-<key> back onto --<key> in one place.
 */
export const VARIABLE_TOKENS = {
    menuGradient: 'menu-gradient',
    drawerGradient: 'drawer-gradient',
    workspaceGradient: 'workspace-gradient',
    menuBorder: 'menu-border',
    menuItemActive: 'menu-item-active',
    listRowSelected: 'review-list-row-selected',
    listRowHover: 'review-list-row-hover',
    listBorder: 'review-list-border',
    panelBorder: 'review-panel-border',
    filterControlsBg: 'filter-controls-bg',
    drawerIcon: 'drawer-icon',
    drawerDivider: 'drawer-divider'
} as const

export type VariableTokenKey = keyof typeof VARIABLE_TOKENS

/** What buildVariant falls back to when a family does not pin one of the above. */
const variableDefaults = (spec: VariantSpec, dark: boolean): Record<VariableTokenKey, string> => ({
    menuGradient: 'none',
    drawerGradient: 'none',
    workspaceGradient: 'none',
    menuBorder: '1px solid rgba(var(--v-theme-on-menu-bg), 0.13)',
    menuItemActive: 'rgba(var(--v-theme-accent), 0.22)',
    listRowSelected: dark ? 'rgba(var(--v-theme-primary), 0.22)' : '#FFF3CD',
    listRowHover: `rgba(var(--v-theme-primary), ${dark ? 0.14 : 0.07})`,
    listBorder: 'rgba(var(--v-theme-outline), 0.34)',
    panelBorder: 'rgba(var(--v-theme-outline), 0.58)',
    filterControlsBg: spec.surfaceVariant,
    drawerIcon: 'rgb(var(--v-theme-on-drawer-bg))',
    drawerDivider: 'rgba(var(--v-theme-on-drawer-bg), 0.2)'
})

/**
 * The value each variable token actually resolves to for a spec - what the
 * family pins, else the fallback. The theme editor seeds its pickers from this,
 * so it shows the same colour the app is really painting.
 */
export const effectiveVariables = (spec: VariantSpec, dark: boolean): Record<VariableTokenKey, string> => {
    const defaults = variableDefaults(spec, dark)
    const keys = Object.keys(VARIABLE_TOKENS) as VariableTokenKey[]

    return Object.fromEntries(keys.map((key) => [key, spec[key] ?? defaults[key]])) as Record<VariableTokenKey, string>
}
