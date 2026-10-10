import { describe, expect, it } from 'vitest'
import {
    citedKeys,
    generateLinkKey,
    insertAtCaret,
    isHttpUrl,
    isLinkKey,
    linkToken,
    numberLinks,
    shortUrl,
    splitReferences
} from '@/utils/linkReferences'

const link = (value: string, key: string) => ({ value, value_description: key })

describe('link keys and tokens', () => {
    it('generates valid keys that avoid the taken ones', () => {
        const taken = new Set<string>()
        for (let round = 0; round < 50; round += 1) {
            const key = generateLinkKey(taken)
            expect(isLinkKey(key)).toBe(true)
            expect(taken.has(key)).toBe(false)
            taken.add(key)
        }
    })

    it('writes and finds citation tokens', () => {
        expect(linkToken('k3f9a2')).toBe('[#k3f9a2]')
        expect(citedKeys('See [#aaaaaa], then [#bbbbbb] and [#aaaaaa]; [1] is plain text.')).toEqual(['aaaaaa', 'bbbbbb', 'aaaaaa'])
        expect(citedKeys('[#UPPER1] [#ab] none')).toEqual([])
        expect(citedKeys(null)).toEqual([])
    })
})

describe('numberLinks', () => {
    it('numbers links in order, skipping empty ones and sharing a number for equal URLs', () => {
        const numbered = numberLinks([
            link('https://a.example', 'aaaaaa'),
            link('  ', 'emptyy'),
            link('https://b.example', 'bbbbbb'),
            link(' https://a.example ', 'cccccc'),
            link('https://c.example', 'not a key')
        ])

        expect(numbered).toEqual([
            { key: 'aaaaaa', url: 'https://a.example', number: 1 },
            { key: 'bbbbbb', url: 'https://b.example', number: 2 },
            { key: 'cccccc', url: 'https://a.example', number: 1 }
        ])
    })
})

describe('insertAtCaret', () => {
    it('inserts at the caret, separated from the preceding word', () => {
        expect(insertAtCaret('Fixed upstream.', '[#aaaaaa]', 14, 14)).toEqual({ text: 'Fixed upstream [#aaaaaa].', caret: 24 })
    })

    it('does not add a space after whitespace or at the start', () => {
        expect(insertAtCaret('Fixed ', '[#aaaaaa]', 6, 6).text).toBe('Fixed [#aaaaaa]')
        expect(insertAtCaret('', '[#aaaaaa]').text).toBe('[#aaaaaa]')
    })

    it('replaces a selection and appends when no caret is known', () => {
        expect(insertAtCaret('See X here', '[#aaaaaa]', 4, 5).text).toBe('See [#aaaaaa] here')
        expect(insertAtCaret('Text', '[#aaaaaa]').text).toBe('Text [#aaaaaa]')
    })
})

describe('splitReferences', () => {
    it('splits text into plain runs and resolved or missing citations', () => {
        const resolve = (key: string) => (key === 'aaaaaa' ? { key, url: 'https://a.example', number: 3 } : undefined)

        expect(splitReferences('Patch [#aaaaaa], see [#gone00].', resolve)).toEqual([
            { text: 'Patch ' },
            { key: 'aaaaaa', link: { key: 'aaaaaa', url: 'https://a.example', number: 3 } },
            { text: ', see ' },
            { key: 'gone00', link: undefined },
            { text: '.' }
        ])
        expect(splitReferences('', resolve)).toEqual([])
    })
})

describe('URL helpers', () => {
    it('accepts only http(s) URLs', () => {
        expect(isHttpUrl(' https://example.com/x ')).toBe(true)
        expect(isHttpUrl('javascript:alert(1)')).toBe(false)
        expect(isHttpUrl('example.com')).toBe(false)
        expect(isHttpUrl(null)).toBe(false)
    })

    it('shortens a URL to host and path', () => {
        expect(shortUrl('https://www.example.com/a/b/')).toBe('example.com/a/b')
    })
})
