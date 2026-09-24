import { describe, it, expect } from 'vitest'
import {
    EDITABLE_TOKENS,
    isValidTokenValue,
    parseCustomTheme,
    readBasedOn,
    seedFromFamily,
    serializeCustomTheme,
    applyTokens
} from '@/themes/custom'
import { getFamily, buildVariant } from '@/themes'

const seed = { basedOn: 'forest', ...seedFromFamily(getFamily('forest')) }

describe('custom theme storage', () => {
    it('seeds every editable token as a concrete hex the picker can bind to', () => {
        for (const variant of ['light', 'dark'] as const) {
            for (const token of EDITABLE_TOKENS) {
                const value = seed[variant][token.key]
                expect(value, `${variant}.${token.key}`).toMatch(/^#([\dA-F]{6}|[\dA-F]{8})$/)
            }
        }
    })

    // Families legitimately store `rgba(var(--v-theme-primary), 0.22)` and rgba()
    // literals, which a colour picker cannot show, so seeding must resolve them.
    it('resolves theme-variable references and rgba literals when seeding', () => {
        const taranisSeed = seedFromFamily(getFamily('taranis'))

        // taranis dark pins listRowSelected as rgba(var(--v-theme-primary), 0.22)
        expect(taranisSeed.dark['listRowSelected']).toMatch(/^#58A7E8/)
        // ...and listBorder as an rgba() literal: rgba(52, 82, 104, 0.34)
        expect(taranisSeed.light['listBorder']).toBe('#34526857')
    })

    it('round-trips a serialised theme', () => {
        const edited = { ...seed, light: { ...seed.light, primary: '#123456' } }
        const parsed = parseCustomTheme(serializeCustomTheme(edited), seed)

        expect(parsed.light['primary']).toBe('#123456')
        expect(parsed.basedOn).toBe('forest')
        expect(parsed.dark).toEqual(seed.dark)
    })

    it('falls back to the seed for empty, malformed or non-object input', () => {
        for (const input of ['', '   ', 'not json', '[]', 'null', '"a string"', '42']) {
            expect(parseCustomTheme(input, seed), input).toEqual(seed)
        }
    })

    // The stored value is per-user input that ends up in a stylesheet, and
    // nothing validates setting values on the way in.
    it('rejects any value that is not a plain hex colour', () => {
        const hostile = ['red', '#12', 'url(x)', 'red; } body { display: none', 'rgb(0,0,0)', '#GGGGGG', 'var(--x)', 12, null, {}]

        for (const value of hostile) {
            const parsed = parseCustomTheme(JSON.stringify({ light: { primary: value } }), seed)
            expect(parsed.light['primary'], String(value)).toBe(seed.light['primary'])
        }
    })

    it('accepts 8-digit hex only for the alpha-capable tokens', () => {
        const parsed = parseCustomTheme(JSON.stringify({ light: { primary: '#11223344', listBorder: '#11223344' } }), seed)

        expect(parsed.light['primary']).toBe(seed.light['primary'])
        expect(parsed.light['listBorder']).toBe('#11223344')
    })

    it('drops unknown keys rather than passing them through to the theme', () => {
        const parsed = parseCustomTheme(JSON.stringify({ light: { 'nonsense': '#ffffff', 'a; }': '#000' } }), seed)

        expect(parsed.light['nonsense']).toBeUndefined()
        expect(Object.keys(parsed.light).sort()).toEqual(EDITABLE_TOKENS.map((token) => token.key).sort())
    })

    // The seed a rejected value falls back to has to be the family the user
    // started from, not the default one.
    it('exposes the seed family without needing to parse the whole theme', () => {
        expect(readBasedOn(JSON.stringify({ basedOn: 'forest', light: {}, dark: {} }))).toBe('forest')
        expect(readBasedOn('')).toBeUndefined()
        expect(readBasedOn('not json')).toBeUndefined()
        expect(readBasedOn(JSON.stringify({ basedOn: 42 }))).toBeUndefined()
        expect(readBasedOn(null)).toBeUndefined()
    })

    it('validates alpha only where the token allows it', () => {
        expect(isValidTokenValue('#AABBCC', false)).toBe(true)
        expect(isValidTokenValue('#AABBCCDD', false)).toBe(false)
        expect(isValidTokenValue('#AABBCCDD', true)).toBe(true)
    })

    it('overlays edited tokens onto a base spec and leaves derived tokens alone', () => {
        const base = getFamily('forest').light
        const spec = applyTokens(base, { primary: '#ABCDEF', bogus: '#000000' })

        expect(spec.primary).toBe('#ABCDEF')
        expect(spec.surfaceBright).toBe(base.surfaceBright)
        expect((spec as unknown as Record<string, unknown>)['bogus']).toBeUndefined()
    })

    it('produces a theme Vuetify can consume, with alpha surviving as rgba()', () => {
        const parsed = parseCustomTheme(JSON.stringify({ light: { listBorder: '#11223380' } }), seed)
        const built = buildVariant(applyTokens(getFamily('forest').light, parsed.light), false)

        expect(built.variables['review-list-border']).toBe('rgba(17, 34, 51, 0.5)')
        for (const value of Object.values(built.variables)) {
            expect(String(value)).not.toMatch(/^#/)
        }
    })
})
