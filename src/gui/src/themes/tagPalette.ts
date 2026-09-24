import { contrastRatio } from './wcag'

/**
 * The tag cloud's colours.
 *
 * This is the app's only multi-colour palette, and it is where `secondary`,
 * `tertiary` and `accent` earn their keep - measured against the rest of the
 * app they are referenced 2, 1 and 0 times, so a theme's choice for them was
 * previously invisible.
 *
 * Two rules from the dataviz guidance shape it:
 *
 *  - Status colours (error/info/success/warning) are reserved and never become
 *    palette entries, so only the four identity colours are eligible.
 *  - The order is fixed and never cycled.
 *
 * Colour here encodes nothing - the cloud already encodes frequency as font
 * size - so the categorical separation checks do not apply. Contrast does:
 * every word is clickable text. Feeding a theme's raw slots in fails badly
 * (Taranis light's accent is 2.11:1 against the surface, Bubblegum's 1.15:1),
 * so each entry is stepped toward the readable direction until it clears AA.
 */

/** Tag words are text on the cloud's ground, so they carry the AA text threshold. */
const MIN_CONTRAST = 4.5

/**
 * Correction pulls colours toward the same extreme, so a theme that names the
 * same colour twice (High contrast uses #0033CC for both primary and accent)
 * would repeat it. This drops only near-identical results - it is deliberately
 * tiny, because colour encodes nothing here and two merely similar hues are
 * still worth keeping.
 */
const DUPLICATE_DISTANCE = 24

export const TAG_PALETTE_SOURCES = ['primary', 'secondary', 'tertiary', 'accent'] as const
export const TAG_FIXED_COLORS = ['#2f86c1', '#1e9f9a', '#6b9f3a', '#dc8b21', '#d1606b', '#8a6bb8', '#238f70', '#5577b9'] as const

const HEX = /^#([\da-f]{3}|[\da-f]{6})$/i

const toRgb = (hex: string): [number, number, number] => {
    const digits = hex.replace('#', '')
    const full = digits.length === 3 ? [...digits].map((digit) => digit + digit).join('') : digits

    return [0, 2, 4].map((offset) => parseInt(full.slice(offset, offset + 2), 16)) as [number, number, number]
}

const toHex = (rgb: number[]): string =>
    `#${rgb
        .map((value) =>
            Math.max(0, Math.min(255, Math.round(value)))
                .toString(16)
                .padStart(2, '0')
        )
        .join('')}`.toUpperCase()

/** Move a colour toward black or white in small steps, preserving its hue. */
const step = (rgb: [number, number, number], towardWhite: boolean, amount: number): [number, number, number] =>
    rgb.map((value) => (towardWhite ? value + (255 - value) * amount : value * (1 - amount))) as [number, number, number]

/**
 * Darken (on a light ground) or lighten (on a dark ground) until the colour is
 * readable against it. Returns null if even full black/white cannot clear the
 * threshold, which happens only for pathological grounds.
 */
const correct = (hex: string, ground: string, dark: boolean): string | null => {
    if (!HEX.test(hex) || !HEX.test(ground)) return null
    if (contrastRatio(hex, ground) >= MIN_CONTRAST) return hex.toUpperCase()

    const base = toRgb(hex)
    for (let amount = 0.05; amount <= 1; amount += 0.05) {
        const candidate = toHex(step(base, dark, amount))
        if (contrastRatio(candidate, ground) >= MIN_CONTRAST) return candidate
    }

    return null
}

/**
 * Build the palette for one theme.
 *
 * `colors` is the theme's resolved colour map; `ground` the surface the cloud
 * is painted on. With `colorful` off the cloud uses a single hue, which is the
 * honest default for a decorative encoding - and what the existing TAG_COLOR
 * setting has always meant.
 */
export const tagPalette = (colors: Record<string, string | undefined>, ground: string, dark: boolean, colorful = true): string[] => {
    if (colorful) {
        return [...TAG_FIXED_COLORS]
    }

    const palette: string[] = []
    for (const key of TAG_PALETTE_SOURCES) {
        const corrected = correct(colors[key] ?? '', ground, dark)
        if (!corrected) continue
        if (palette.some((existing) => colourDistance(existing, corrected) < DUPLICATE_DISTANCE)) continue
        palette.push(corrected)
    }

    // A theme whose identity colours all failed still needs something legible.
    return palette.length > 0 ? palette : [correct('#808080', ground, dark) ?? (dark ? '#FFFFFF' : '#000000')]
}

/** Straight RGB distance - enough to recognise the same colour twice. */
const colourDistance = (a: string, b: string): number => {
    const [ar, ag, ab] = toRgb(a)
    const [br, bg, bb] = toRgb(b)

    return Math.sqrt((ar - br) ** 2 + (ag - bg) ** 2 + (ab - bb) ** 2)
}
