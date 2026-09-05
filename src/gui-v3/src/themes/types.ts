/**
 * Theme family contract.
 *
 * A "family" is a pair of Vuetify themes - a light and a dark variant sharing an
 * identity (Taranis-NG, Forest, ...). Vuetify itself has no notion of families:
 * it only knows flat theme names, so a family collapses to `<id>-light` /
 * `<id>-dark` at the `theme.change()` boundary. See `themes/index.ts`.
 *
 * Only the core palette and the four extended surfaces are required. Everything
 * optional is derived by `buildVariant()` from the values above it, so a new
 * family file stays short. Every derived value can still be pinned explicitly.
 */
export interface VariantSpec {
    /* --- Core Vuetify palette --- */
    background: string
    surface: string
    surfaceVariant: string
    onSurface: string
    outline: string
    primary: string
    secondary: string
    tertiary: string
    error: string
    info: string
    success: string
    warning: string
    accent: string

    /* --- Extended surfaces, registered as real Vuetify colors --- */
    /** Application top bar. */
    menuBg: string
    /** Navigation drawer. */
    drawerBg: string
    /** Backdrop behind the review/assess panels. */
    workspace: string
    /** Card and list row background inside those panels. */
    listRow: string

    /* --- Optional: Vuetify derives a contrasting `on-<color>` for every color
       above, so these are only needed where the computed contrast is wrong. --- */
    onPrimary?: string
    onSecondary?: string
    onTertiary?: string
    onError?: string
    onInfo?: string
    onSuccess?: string
    onWarning?: string
    onMenuBg?: string
    onDrawerBg?: string

    /* --- Optional: Vuetify 4 standard surfaces. When omitted, Vuetify's own
       defaults apply (which is what this app shipped before theming). --- */
    surfaceBright?: string
    surfaceLight?: string
    onSurfaceVariant?: string

    /* --- Optional: alpha-carrying or composite values. These become Vuetify
       theme `variables` (--v-<key>) rather than colors, because a Vuetify color
       must be an opaque value it can decompose into an "r, g, b" triplet. --- */
    /** Full `border-bottom` shorthand for the top bar, not just a colour, so a
     *  theme can give it weight as well as hue (SK-CERT's red rule under the
     *  blue nav). Defaults to a hairline in the bar's own text colour. */
    menuBorder?: string
    menuItemActive?: string
    listRowSelected?: string
    listRowHover?: string
    listBorder?: string
    panelBorder?: string
    filterControlsBg?: string
    drawerIcon?: string
    drawerDivider?: string
}

export interface ThemeFamily {
    /** Stable id, persisted as the UI_THEME setting value. Never rename. */
    id: string
    /** Fallback label, used when no `themes.<id>` translation exists. */
    label: string
    light: VariantSpec
    dark: VariantSpec
}
