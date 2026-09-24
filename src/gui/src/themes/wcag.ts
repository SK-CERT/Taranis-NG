/**
 * WCAG relative luminance and contrast ratio.
 *
 * Shared by the theme contract test and the custom-theme editor's readability
 * warnings, so the two cannot drift apart. Thresholds used in both places:
 * body text on its grounds at AAA (7), chrome and primary-as-text at AA (4.5).
 */

export const AAA_BODY_TEXT = 7
export const AA_TEXT = 4.5

const channel = (value: number): number => (value <= 0.03928 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4)

/** Accepts #RGB, #RRGGBB and #RRGGBBAA; alpha is ignored, as it cannot be judged without a backdrop. */
export const luminance = (hex: string): number => {
    const digits = hex.replace('#', '')
    const full = digits.length === 3 ? [...digits].map((digit) => digit + digit).join('') : digits
    const linear = [0, 2, 4].map((offset) => channel(parseInt(full.slice(offset, offset + 2), 16) / 255))

    return 0.2126 * (linear[0] ?? 0) + 0.7152 * (linear[1] ?? 0) + 0.0722 * (linear[2] ?? 0)
}

export const contrastRatio = (a: string, b: string): number => {
    const [lighter, darker] = [luminance(a), luminance(b)].sort((x, y) => y - x)

    return ((lighter ?? 0) + 0.05) / ((darker ?? 0) + 0.05)
}
