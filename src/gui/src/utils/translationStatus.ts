/**
 * The translation status of one language of an item, as core works it out
 * (src/core/managers/translation_status.py): the first that applies of missing, outdated,
 * partly translated, translated by AI and not reviewed, done. Used where the GUI holds the
 * translations itself, e.g. the language tabs of an open report.
 */

export const TRANSLATION_MISSING = 'translation_missing'
export const TRANSLATION_PARTIAL = 'translation_partial'
export const TRANSLATION_OUTDATED = 'translation_outdated'
export const TRANSLATION_AI = 'translation_ai'
export const TRANSLATION_DONE = 'translation_done'
export const LANGUAGE_NOT_SET = 'language_not_set'

export type TranslationRow = { value?: string | null; outdated?: boolean; origin?: string | null } | null | undefined

/** A field that has something to translate: its original, and its translation into the language (if any). */
export type TranslationField = { original: string | null | undefined; row: TranslationRow }

export function translationStatus(fields: TranslationField[]): string {
    const present = fields.filter((field) => field.row?.value)
    if (present.length === 0) return TRANSLATION_MISSING
    if (present.some((field) => field.row?.outdated)) return TRANSLATION_OUTDATED
    if (present.length < fields.length) return TRANSLATION_PARTIAL
    if (present.some((field) => field.row?.origin === 'ai')) return TRANSLATION_AI
    return TRANSLATION_DONE
}
