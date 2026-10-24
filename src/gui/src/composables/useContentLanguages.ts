import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useSettingsStore } from '@/stores/settings'
import { Settings } from '@/types/settings'

/**
 * Languages of report content: the ISO 639-1 codes the "Default language for reports/products"
 * setting offers, their names in the GUI's language, and which name of a report or product to
 * show for the GUI's language.
 */

// Attribute types whose values a report translates (when its report type ticks Translate).
export const TRANSLATABLE_TYPES = ['STRING', 'TEXT', 'RICH_TEXT'] as const

// Tried after the requested language, before the text's own.
export const FALLBACK_LANGUAGE = 'en'

export type LanguageOption = {
    id: string
    txt: string
}

/**
 * The name of a language, in `displayLocale` (or in the language itself when `native`).
 * Falls back to `defaultName`, then to the code, where the browser has no names.
 */
export function getLanguageName(code: string, displayLocale: string, defaultName?: string, native = false): string {
    try {
        if (typeof Intl !== 'undefined' && Intl.DisplayNames) {
            // Without fallback 'none', a code the browser has no name for comes back as the code.
            const displayNames = new Intl.DisplayNames(native ? [code, 'en'] : [displayLocale, 'en'], { type: 'language', fallback: 'none' })
            return displayNames.of(code) || defaultName || code
        }
    } catch {
        // An unknown code or locale: use the fallback below.
    }
    return defaultName || code
}

/** The content language of a GUI locale: its primary subtag (`pt-BR` -> `pt`), if it is a two-letter code. */
export function contentLanguageOf(locale: string | null | undefined): string | null {
    const primary = (String(locale ?? '').split(/[-_]/)[0] ?? '').toLowerCase()
    return /^[a-z]{2}$/.test(primary) ? primary : null
}

/** The languages to look in, in order: requested, English, then the text's own. */
export function languageChain(requested: string | null | undefined, source: string | null | undefined): string[] {
    const chain: string[] = []
    for (const language of [requested, FALLBACK_LANGUAGE, source]) {
        if (language && !chain.includes(language)) chain.push(language)
    }
    return chain
}

export type TitledItem = {
    title?: string | null
    title_prefix?: string | null
    language?: string | null
    title_translations?: Record<string, { title?: string; title_prefix?: string }> | null
}

/**
 * The name and prefix of a report (or product) to show in `locale`: the translation into the
 * GUI's language, else English, else the item's own text. A language that *is* the item's own
 * gives its own text, so an English translation never replaces the original. Each field is
 * resolved on its own.
 */
export function localizedTitle(item: TitledItem, locale: string | null | undefined): { title: string; title_prefix: string } {
    const chain = languageChain(contentLanguageOf(locale), item.language)
    const pick = (field: 'title' | 'title_prefix'): string => {
        const own = String(item[field] ?? '')
        for (const language of chain) {
            if (language === item.language) return own
            const translated = item.title_translations?.[language]?.[field]
            if (translated) return translated
        }
        return own
    }
    return { title: pick('title'), title_prefix: pick('title_prefix') }
}

export function useContentLanguages() {
    const { locale } = useI18n()
    const settingsStore = useSettingsStore()

    const contentSetting = computed(() => {
        const settings = Array.isArray(settingsStore.getSettings) ? settingsStore.getSettings : []
        return settings.find((entry) => entry?.key === Settings.CONTENT_DEFAULT_LANGUAGE) as { value?: string; options?: string } | undefined
    })

    const configuredNames = computed<Record<string, string>>(() => {
        const setting = contentSetting.value
        try {
            const options = JSON.parse(setting?.options || '[]') as Array<{ id: string; txt: string }>
            return Object.fromEntries(options.map((option) => [String(option.id), String(option.txt)]))
        } catch {
            return {}
        }
    })

    const languageName = (code: string | null | undefined): string => {
        if (!code) return ''
        return getLanguageName(code, String(locale.value), configuredNames.value[code])
    }

    /**
     * Every content language, named in the GUI's language and sorted by that name. Codes the
     * browser names alike (ak and tw are both "Akan") are told apart by their code.
     */
    const languageOptions = computed<LanguageOption[]>(() => {
        const options = Object.keys(configuredNames.value).map((id) => ({ id, txt: languageName(id) }))
        const named = new Map<string, number>()
        for (const option of options) named.set(option.txt, (named.get(option.txt) ?? 0) + 1)
        return options
            .map((option) => ((named.get(option.txt) ?? 0) > 1 ? { ...option, txt: `${option.txt} (${option.id})` } : option))
            .sort((left, right) => left.txt.localeCompare(right.txt, String(locale.value)))
    })

    const titleOf = (item: TitledItem) => localizedTitle(item, String(locale.value))

    /** The user's "Default language for reports/products", the one new content is written in; null while not set. */
    const defaultContentLanguage = computed<string | null>(() => contentSetting.value?.value || null)

    return { languageOptions, languageName, titleOf, defaultContentLanguage }
}
