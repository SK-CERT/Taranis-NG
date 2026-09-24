import type { ThemeFamily, VariantSpec } from './types'
import { taranis } from './taranis'
import { effectiveVariables, type VariableTokenKey } from './variables'

export const CUSTOM_THEME_FAMILY = 'custom'

export type TokenGroup = 'brand' | 'status' | 'surfaces' | 'chrome' | 'details'

/**
 * The slots the theme editor exposes. Everything else in VariantSpec keeps
 * deriving from these, exactly as it does for the built-in families, which is
 * what keeps the editor a readable list rather than 35 pickers.
 *
 * The five `details` entries are emitted as Vuetify theme *variables* and may
 * carry alpha; the other seventeen are Vuetify *colors* and must stay opaque,
 * because a color has to decompose into an "r, g, b" triplet.
 */
export interface EditableToken {
    key: keyof VariantSpec
    group: TokenGroup
    allowsAlpha: boolean
}

export const EDITABLE_TOKENS: EditableToken[] = [
    { key: 'primary', group: 'brand', allowsAlpha: false },
    { key: 'secondary', group: 'brand', allowsAlpha: false },
    { key: 'tertiary', group: 'brand', allowsAlpha: false },
    { key: 'accent', group: 'brand', allowsAlpha: false },

    { key: 'error', group: 'status', allowsAlpha: false },
    { key: 'info', group: 'status', allowsAlpha: false },
    { key: 'success', group: 'status', allowsAlpha: false },
    { key: 'warning', group: 'status', allowsAlpha: false },

    { key: 'background', group: 'surfaces', allowsAlpha: false },
    { key: 'surface', group: 'surfaces', allowsAlpha: false },
    { key: 'surfaceVariant', group: 'surfaces', allowsAlpha: false },
    { key: 'onSurface', group: 'surfaces', allowsAlpha: false },
    { key: 'outline', group: 'surfaces', allowsAlpha: false },

    { key: 'menuBg', group: 'chrome', allowsAlpha: false },
    { key: 'drawerBg', group: 'chrome', allowsAlpha: false },
    { key: 'workspace', group: 'chrome', allowsAlpha: false },
    { key: 'listRow', group: 'chrome', allowsAlpha: false },

    { key: 'listRowSelected', group: 'details', allowsAlpha: true },
    { key: 'listBorder', group: 'details', allowsAlpha: true },
    { key: 'panelBorder', group: 'details', allowsAlpha: true },
    { key: 'filterControlsBg', group: 'details', allowsAlpha: true },
    { key: 'menuItemActive', group: 'details', allowsAlpha: true }
]

export const TOKEN_GROUPS: TokenGroup[] = ['brand', 'status', 'surfaces', 'chrome', 'details']

const OPAQUE_HEX = /^#([\da-f]{3}|[\da-f]{6})$/i
const ALPHA_HEX = /^#([\da-f]{3}|[\da-f]{6}|[\da-f]{8})$/i

/** Custom themes are stored per user; a stored value is untrusted input that ends up in CSS. */
export const isValidTokenValue = (value: unknown, allowsAlpha: boolean): value is string =>
    typeof value === 'string' && (allowsAlpha ? ALPHA_HEX : OPAQUE_HEX).test(value.trim())

const variableTokenKeys = new Set<string>(EDITABLE_TOKENS.filter((token) => token.allowsAlpha).map((token) => token.key))

const expand = (digits: string): string => (digits.length === 3 ? [...digits].map((digit) => digit + digit).join('') : digits)

const toHex = (r: number, g: number, b: number, alpha?: number): string => {
    const pair = (value: number) =>
        Math.max(0, Math.min(255, Math.round(value)))
            .toString(16)
            .padStart(2, '0')
    const rgb = `#${pair(r)}${pair(g)}${pair(b)}`

    return alpha === undefined || alpha >= 1 ? rgb.toUpperCase() : `${rgb}${pair(alpha * 255)}`.toUpperCase()
}

/**
 * Turn whatever a family pins into something a colour picker can show.
 *
 * Families legitimately hold values the picker cannot represent - `rgba(...)`
 * literals, and references like `rgba(var(--v-theme-primary), 0.22)` - so those
 * are resolved against the spec they came from before seeding the editor.
 */
const CSS_COLOR_SOURCES: Record<string, keyof VariantSpec> = {
    'primary': 'primary',
    'accent': 'accent',
    'outline': 'outline',
    'on-drawer-bg': 'onDrawerBg',
    'on-menu-bg': 'onMenuBg',
    'surface-variant': 'surfaceVariant'
}

const seedValue = (spec: VariantSpec, raw: string | undefined, fallback: string): string => {
    const value = (raw ?? '').trim()
    if (!value) return fallback

    const hex = ALPHA_HEX.exec(value)
    if (hex) {
        const digits = expand(hex[1] ?? '')
        return `#${digits}`.toUpperCase()
    }

    const varRef = /^rgba?\(\s*var\(--v-theme-([\w-]+)\)\s*(?:,\s*([\d.]+)\s*)?\)$/i.exec(value)
    if (varRef) {
        const sourceKey = CSS_COLOR_SOURCES[varRef[1] ?? '']
        const source = sourceKey ? (spec[sourceKey] as string | undefined) : undefined
        if (source && OPAQUE_HEX.test(source)) {
            const digits = expand(source.replace('#', ''))
            const [r, g, b] = [0, 2, 4].map((offset) => parseInt(digits.slice(offset, offset + 2), 16))
            return toHex(r ?? 0, g ?? 0, b ?? 0, varRef[2] === undefined ? undefined : Number(varRef[2]))
        }
        return fallback
    }

    const literal = /^rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*(?:,\s*([\d.]+)\s*)?\)$/i.exec(value)
    if (literal) {
        return toHex(Number(literal[1]), Number(literal[2]), Number(literal[3]), literal[4] === undefined ? undefined : Number(literal[4]))
    }

    return fallback
}

/** Every editable slot of a family, resolved to a concrete hex the editor can bind to. */
export const seedFromSpec = (spec: VariantSpec, dark: boolean): Record<string, string> => {
    const variables = effectiveVariables(spec, dark)

    return Object.fromEntries(
        EDITABLE_TOKENS.map((token) => {
            const raw = variableTokenKeys.has(token.key) ? variables[token.key as VariableTokenKey] : (spec[token.key] as string | undefined)

            return [token.key, seedValue(spec, raw, dark ? '#808080' : '#C0C0C0')]
        })
    )
}

export const seedFromFamily = (family: ThemeFamily): { light: Record<string, string>; dark: Record<string, string> } => ({
    light: seedFromSpec(family.light, false),
    dark: seedFromSpec(family.dark, true)
})

export interface CustomThemeData {
    basedOn: string
    light: Record<string, string>
    dark: Record<string, string>
}

/**
 * Read a stored custom theme. Anything unrecognised or malformed is dropped in
 * favour of the seed rather than reaching the stylesheet - the stored value is
 * per-user input and nothing validates it on the way in.
 */
export const parseCustomTheme = (raw: string | null | undefined, seed: CustomThemeData): CustomThemeData => {
    if (!raw || !raw.trim()) return seed

    let parsed: unknown
    try {
        parsed = JSON.parse(raw)
    } catch {
        return seed
    }
    if (!parsed || typeof parsed !== 'object') return seed

    const source = parsed as Partial<Record<'basedOn' | 'light' | 'dark', unknown>>
    const pick = (variant: 'light' | 'dark'): Record<string, string> => {
        const stored = source[variant]
        const values = stored && typeof stored === 'object' ? (stored as Record<string, unknown>) : {}

        return Object.fromEntries(
            EDITABLE_TOKENS.map((token) => {
                const candidate = values[token.key]
                const accepted = isValidTokenValue(candidate, token.allowsAlpha) ? candidate.trim().toUpperCase() : seed[variant][token.key]

                return [token.key, accepted as string]
            })
        )
    }

    return {
        basedOn: typeof source.basedOn === 'string' && source.basedOn ? source.basedOn : seed.basedOn,
        light: pick('light'),
        dark: pick('dark')
    }
}

/**
 * Peek at which family a stored theme was seeded from, before parsing it.
 * Parsing needs a seed to fall back to, and that seed should be the family the
 * user actually started from - otherwise a rejected value silently reverts to
 * the default family's colour instead of theirs.
 */
export const readBasedOn = (raw?: string | null): string | undefined => {
    if (!raw || !raw.trim()) return undefined
    try {
        const parsed: unknown = JSON.parse(raw)
        const value = (parsed as { basedOn?: unknown } | null)?.basedOn

        return typeof value === 'string' && value ? value : undefined
    } catch {
        return undefined
    }
}

export const serializeCustomTheme = (data: CustomThemeData): string => JSON.stringify(data)

/** Plain-object copy. structuredClone cannot take Vue's reactive proxies. */
export const cloneCustomTheme = (data: CustomThemeData): CustomThemeData => ({
    basedOn: data.basedOn,
    light: { ...data.light },
    dark: { ...data.dark }
})

/** Overlay edited slots onto a base spec, leaving every derived token to the factory. */
export const applyTokens = (base: VariantSpec, tokens: Record<string, string>): VariantSpec => {
    const spec = { ...base } as Record<string, unknown>
    for (const token of EDITABLE_TOKENS) {
        const value = tokens[token.key]
        if (isValidTokenValue(value, token.allowsAlpha)) spec[token.key] = value
    }

    return spec as unknown as VariantSpec
}

export const toThemeFamily = (data: CustomThemeData): ThemeFamily => ({
    id: CUSTOM_THEME_FAMILY,
    label: 'Custom',
    light: applyTokens(taranis.light, data.light),
    dark: applyTokens(taranis.dark, data.dark)
})

/**
 * The baked-in Custom family. It is a copy of Taranis-NG so that custom-light
 * and custom-dark are always valid before any user data loads; the saved
 * palette is written over it at runtime via theme.themes.
 */
export const custom: ThemeFamily = {
    id: CUSTOM_THEME_FAMILY,
    label: 'Custom',
    light: { ...taranis.light },
    dark: { ...taranis.dark }
}
