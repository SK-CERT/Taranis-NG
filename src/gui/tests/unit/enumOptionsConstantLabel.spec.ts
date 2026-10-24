import { describe, expect, it } from 'vitest'
import { constantLabel } from '@/components/common/attribute/enumOptions'

// Reports store the original constant; a language tab shows its configured translation.

const severity = {
    attribute: {
        attribute_enums: [
            { id: 1, value: 'High', translations: { cs: { value: 'Vysoká' } } },
            { id: 2, value: 'Low', translations: {} }
        ]
    }
}

describe('constantLabel', () => {
    it('reads a constant in the language asked for', () => {
        expect(constantLabel(severity, 'High', 'cs')).toBe('Vysoká')
    })

    it('keeps the constant when it has no translation, or no language is asked for', () => {
        expect(constantLabel(severity, 'Low', 'cs')).toBe('Low')
        expect(constantLabel(severity, 'High', null)).toBe('High')
        expect(constantLabel(severity, 'Unknown', 'cs')).toBe('Unknown')
    })
})
