import { describe, it, expect } from 'vitest'
import { buildVuetifyThemes, themeFamilies, themeName } from '@/themes'
import { tagPalette, TAG_PALETTE_SOURCES } from '@/themes/tagPalette'
import { contrastRatio } from '@/themes/wcag'

const variants = themeFamilies.flatMap((family) =>
    [false, true].map((dark) => ({
        name: themeName(family.id, dark),
        dark,
        colors: buildVuetifyThemes()[themeName(family.id, dark)]?.colors as Record<string, string>
    }))
)

describe('tag cloud palette', () => {
    // Tag words are clickable text, and feeding a theme's raw slots in fails
    // badly - Taranis light's accent is 2.11:1 on its surface, Bubblegum's
    // 1.15:1. Every entry must be readable in every theme.
    it.each(variants.map((v) => [v.name, v] as const))('%s is legible on its own surface', (_name, variant) => {
        const ground = variant.colors['surface'] ?? ''
        const palette = tagPalette(variant.colors, ground, variant.dark)

        expect(palette.length).toBeGreaterThan(0)
        for (const colour of palette) {
            expect(contrastRatio(colour, ground), colour).toBeGreaterThanOrEqual(4.5)
        }
    })

    it('draws only on the identity colours, never on the reserved status ones', () => {
        expect([...TAG_PALETTE_SOURCES]).toEqual(['primary', 'secondary', 'tertiary', 'accent'])
        for (const reserved of ['error', 'info', 'success', 'warning']) {
            expect(TAG_PALETTE_SOURCES).not.toContain(reserved)
        }
    })

    it('keeps a fixed order rather than cycling', () => {
        const colors = { primary: '#123456', secondary: '#654321', tertiary: '#2E7D32', accent: '#8A2BE2' }
        const first = tagPalette(colors, '#FFFFFF', false)
        const second = tagPalette(colors, '#FFFFFF', false)

        expect(first).toEqual(second)
        expect(first[0]).toBe('#123456')
    })

    it('collapses to a single hue when colourful tags are off', () => {
        const colors = { primary: '#123456', secondary: '#654321', tertiary: '#2E7D32', accent: '#8A2BE2' }

        expect(tagPalette(colors, '#FFFFFF', false, false)).toHaveLength(1)
    })

    it('corrects an unreadable colour rather than dropping it', () => {
        // Bubblegum light's accent against white: 1.15:1
        const palette = tagPalette({ primary: '#B0F9FA' }, '#FFFFFF', false)

        expect(palette).toHaveLength(1)
        expect(palette[0]).not.toBe('#B0F9FA')
        expect(contrastRatio(palette[0] ?? '', '#FFFFFF')).toBeGreaterThanOrEqual(4.5)
    })

    it('always returns something legible, even for a theme with no usable colours', () => {
        const palette = tagPalette({}, '#FFFFFF', false)

        expect(palette).toHaveLength(1)
        expect(contrastRatio(palette[0] ?? '', '#FFFFFF')).toBeGreaterThanOrEqual(4.5)
    })
})
