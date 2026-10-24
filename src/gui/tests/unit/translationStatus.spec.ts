import { describe, expect, it } from 'vitest'
import { translationStatus } from '@/utils/translationStatus'
import { tagFilterQuery } from '@/api/tags'

// The same rule as core (src/core/managers/translation_status.py): missing, outdated, partly
// translated, translated by AI and not reviewed, done - the first that applies.

const field = (row: object | null) => ({ original: 'Original', row })

describe('translationStatus', () => {
    it('takes the first state that applies', () => {
        expect(translationStatus([field(null), field({ value: '' })])).toBe('translation_missing')
        expect(translationStatus([field({ value: 'a', outdated: true }), field(null)])).toBe('translation_outdated')
        expect(translationStatus([field({ value: 'a' }), field(null)])).toBe('translation_partial')
        expect(translationStatus([field({ value: 'a', origin: 'ai' }), field({ value: 'b', origin: 'manual' })])).toBe('translation_ai')
        expect(translationStatus([field({ value: 'a', origin: 'manual' })])).toBe('translation_done')
    })
})

describe('tagFilterQuery', () => {
    it('sends tags and one translation filter that can be applied', () => {
        expect(tagFilterQuery({ tags: [3, 5], translation: 'needs', translation_language: 'sk' })).toBe(
            '&tags=3%2C5&translation=needs&translation_language=sk'
        )
        expect(tagFilterQuery({ translation: 'not_set', translation_language: 'sk' })).toBe('&translation=not_set')
        // Without a language, "needs translation" cannot be applied yet.
        expect(tagFilterQuery({ translation: 'needs', translation_language: null })).toBe('')
        expect(tagFilterQuery({})).toBe('')
    })
})
