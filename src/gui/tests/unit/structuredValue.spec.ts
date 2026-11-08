import { describe, expect, it } from 'vitest'
import {
    isStructuredType,
    parseStructured,
    referenceUrl,
    serializeStructured,
    structuredSummary
} from '@/components/common/attribute/structuredValue'

describe('structured attribute values', () => {
    it('knows the six structured types and nothing else', () => {
        for (const type of ['AFFECTED', 'CREDIT', 'TIMELINE', 'RELATIONSHIP', 'REFERENCE', 'JSON']) {
            expect(isStructuredType(type)).toBe(true)
        }
        expect(isStructuredType('LINK')).toBe(false)
        expect(isStructuredType(undefined)).toBe(false)
    })

    it('reads an object, and an empty one from anything else', () => {
        expect(parseStructured('{"url": "https://example.org"}')).toEqual({ url: 'https://example.org' })
        for (const notAnObject of ['', '  ', '[1, 2]', '"text"', '{broken', null, undefined, 42]) {
            expect(parseStructured(notAnObject)).toEqual({})
        }
    })

    it('writes sorted keys and leaves out what holds nothing, so an untouched value sends nothing', () => {
        expect(
            serializeStructured({
                vendor: 'ExampleVendor',
                product: 'ExampleProduct',
                cpes: [],
                repo: ' ',
                versions: [{ version: '1.0', lessThan: '' }]
            })
        ).toBe('{"product":"ExampleProduct","vendor":"ExampleVendor","versions":[{"version":"1.0"}]}')
        expect(serializeStructured({ b: 1, a: { d: 'x', c: null } })).toBe('{"a":{"d":"x"},"b":1}')
        expect(serializeStructured({ url: '', tags: [] })).toBe('')
        // The same object typed in another order is the same value.
        expect(serializeStructured({ type: 'finder', value: 'Researcher' })).toBe(
            serializeStructured({ value: 'Researcher', type: 'finder' })
        )
    })

    it('sums each type up in one line', () => {
        const affected = JSON.stringify({
            vendor: 'ExampleVendor',
            product: 'ExampleProduct',
            versions: [
                { version: '0', lessThan: '2.1', status: 'affected' },
                { version: '3.0', lessThanOrEqual: '3.4', status: 'affected' },
                { version: '2.1', status: 'unaffected' }
            ]
        })
        expect(structuredSummary('AFFECTED', affected)).toBe(
            'ExampleVendor ExampleProduct: < 2.1 (affected), 3.0 – ≤ 3.4 (affected), 2.1 (unaffected)'
        )
        expect(
            structuredSummary(
                'AFFECTED',
                JSON.stringify({
                    product: 'ExampleProduct',
                    versions: [{ version: '1.0', lessThan: '2.0', status: 'affected', changes: [{ at: '1.4.2', status: 'unaffected' }] }]
                })
            )
        ).toBe('ExampleProduct: 1.0 – < 2.0 (affected; unaffected from 1.4.2)')
        expect(structuredSummary('AFFECTED', '{"packageName": "example-package"}')).toBe('example-package')
        expect(structuredSummary('CREDIT', '{"value": "Example Researcher", "type": "finder"}')).toBe('Example Researcher (finder)')
        expect(structuredSummary('TIMELINE', '{"time": "2026-11-01T09:30:00", "value": "Reported"}')).toBe('2026-11-01 09:30:00: Reported')
        expect(structuredSummary('RELATIONSHIP', '{"type": "equal", "destId": "CVE-2026-0001"}')).toBe('equal CVE-2026-0001')
        expect(structuredSummary('REFERENCE', '{"url": "https://example.org/a", "name": "Advisory"}')).toBe(
            'Advisory <https://example.org/a>'
        )
        expect(structuredSummary('REFERENCE', '{"url": "https://example.org/a"}')).toBe('https://example.org/a')
        expect(structuredSummary('JSON', '{"other": {"type": "ssvc"}}')).toBe('{"other":{"type":"ssvc"}}')
        expect(structuredSummary('JSON', '')).toBe('')
    })

    it("gives a reference's URL", () => {
        expect(referenceUrl('{"url": " https://example.org/a "}')).toBe('https://example.org/a')
        expect(referenceUrl('{"name": "no url"}')).toBe('')
        expect(referenceUrl('not json')).toBe('')
    })
})
