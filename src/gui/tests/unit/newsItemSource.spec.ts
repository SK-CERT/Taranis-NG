import { describe, expect, it } from 'vitest'
import { newsItemSourceName } from '@/utils/newsItemSource'
import en from '@/i18n/en.json'

// Enough of vue-i18n's t() for two messages with a {name} placeholder.
const t = (key: string, params: Record<string, unknown> = {}) => {
    const message = key.split('.').reduce<unknown>((node, part) => (node as Record<string, unknown>)?.[part], en) as string
    return message.replace('{name}', String(params['name'] ?? ''))
}

describe('newsItemSourceName', () => {
    it('names the OSINT source of a collected item', () => {
        expect(newsItemSourceName({ osint_source_name: 'CERT feed', source: 'https://x', entered_by: null }, t)).toBe('CERT feed')
    })

    it('falls back on the source text, then on nothing', () => {
        expect(newsItemSourceName({ osint_source_name: '', source: 'https://x' }, t)).toBe('https://x')
        expect(newsItemSourceName({ osint_source_name: '', source: '' }, t)).toBe('')
        expect(newsItemSourceName(undefined, t)).toBe('')
    })

    it('says who entered an item by hand', () => {
        expect(newsItemSourceName({ osint_source_name: '', source: 'phone call', entered_by: 'Alice' }, t)).toBe('Manual entry by Alice')
        expect(newsItemSourceName({ entered_by: '' }, t)).toBe('Manual entry')
    })

    it('keeps the manual source an older item was entered into', () => {
        expect(newsItemSourceName({ osint_source_name: 'Manual - CSIRT', entered_by: 'Alice', source_label: 'Manual - CSIRT' }, t)).toBe(
            'Manual entry by Alice · Manual - CSIRT'
        )
    })
})
