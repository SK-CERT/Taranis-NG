import { readdirSync, readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'
import { mergeWordListEntries, parseDelimitedRecords, parseWordListCsv } from '@/utils/word-list-csv'

describe('word-list CSV import', () => {
    it('parses the GUI semicolon format with a header', () => {
        expect(parseWordListCsv('value;description\nthe;English article\nand;Conjunction\n')).toEqual([
            { value: 'the', description: 'English article' },
            { value: 'and', description: 'Conjunction' }
        ])
    })

    it('auto-detects commas and preserves quoted delimiters and escaped quotes', () => {
        expect(parseWordListCsv('description,value\n"common, word",the\n"said ""often""",and\n')).toEqual([
            { value: 'the', description: 'common, word' },
            { value: 'and', description: 'said "often"' }
        ])
    })

    it('supports files without a header', () => {
        expect(parseWordListCsv('the;article\nand;conjunction\n', false)).toEqual([
            { value: 'the', description: 'article' },
            { value: 'and', description: 'conjunction' }
        ])
    })

    it('rejects unterminated quoted fields', () => {
        expect(() => parseDelimitedRecords('value;description\n"broken;entry')).toThrow('Unterminated quoted CSV field')
    })

    it('deduplicates by value while appending and lets imported descriptions win', () => {
        const existing = [
            { value: 'the', description: 'old' },
            { value: 'of', description: '' }
        ]
        const incoming = [
            { value: 'the', description: 'new' },
            { value: 'and', description: '' }
        ]

        expect(mergeWordListEntries(existing, incoming)).toEqual([
            { value: 'the', description: 'new' },
            { value: 'of', description: '' },
            { value: 'and', description: '' }
        ])
        expect(mergeWordListEntries(existing, incoming, true)).toEqual(incoming)
    })

    it('parses every shipped language CSV', () => {
        const resourceDir = resolve(process.cwd(), '../../resources/wordlists')
        const files = readdirSync(resourceDir).filter((name) => name.endsWith('_complete.csv'))
        const entries = files.flatMap((name) => parseWordListCsv(readFileSync(`${resourceDir}/${name}`, 'utf8')))

        expect(files).toHaveLength(24)
        expect(entries).toHaveLength(12_438)
        expect(entries.some((entry) => entry.value === 'the')).toBe(true)
    })
})
