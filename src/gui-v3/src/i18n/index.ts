type LocaleMessageValue = string | LocaleMessageDictionary | LocaleMessageValue[]
interface LocaleMessageDictionary {
    [key: string]: LocaleMessageValue
}
type LocaleMessages = LocaleMessageDictionary

type PluralRule = (choice: number, choicesLength: number, originalRule: (choice: number, choicesLength: number) => number) => number

export type LocaleOption = {
    id: string
    txt: string
}

export type LocaleDirection = 'ltr' | 'rtl'

type VuetifyLocaleTarget = {
    current: {
        value: string
    }
}

const rtlLanguages = Object.freeze(['ar', 'fa', 'he', 'ur'])

const fourFormRule =
    (isOne: (count: number) => boolean, isFew: (count: number) => boolean): PluralRule =>
    (choice, choicesLength, originalRule) => {
        if (choicesLength !== 4) return originalRule(choice, choicesLength)

        const count = Math.abs(choice)
        if (count === 0) return 0
        if (isOne(count)) return 1
        if (isFew(count)) return 2
        return 3
    }

const czechSlovakRule = fourFormRule(
    (count) => count === 1,
    (count) => Number.isInteger(count) && count >= 2 && count <= 4
)
const polishRule = fourFormRule(
    (count) => count === 1,
    (count) => Number.isInteger(count) && count % 10 >= 2 && count % 10 <= 4 && (count % 100 < 12 || count % 100 > 14)
)
const eastSlavicRule = fourFormRule(
    (count) => Number.isInteger(count) && count % 10 === 1 && count % 100 !== 11,
    (count) => Number.isInteger(count) && count % 10 >= 2 && count % 10 <= 4 && (count % 100 < 12 || count % 100 > 14)
)

/** Six forms are ordered as zero | one | two | few | many | other. */
const arabicRule: PluralRule = (choice, choicesLength, originalRule) => {
    if (choicesLength !== 6) return originalRule(choice, choicesLength)

    const count = Math.abs(choice)
    if (count === 0) return 0
    if (count === 1) return 1
    if (count === 2) return 2
    if (!Number.isInteger(count)) return 5

    const remainder = count % 100
    if (remainder >= 3 && remainder <= 10) return 3
    if (remainder >= 11 && remainder <= 99) return 4
    return 5
}

/** Locale-specific contracts use the documented four- or six-form order above. */
export const pluralRules: Readonly<Record<'ar' | 'cs' | 'sk' | 'pl' | 'ru' | 'uk', PluralRule>> = Object.freeze({
    ar: arabicRule,
    cs: czechSlovakRule,
    sk: czechSlovakRule,
    pl: polishRule,
    ru: eastSlavicRule,
    uk: eastSlavicRule
})

const catalogModules = import.meta.glob('./*.json', {
    eager: true,
    import: 'default'
}) as Record<string, LocaleMessages>

export const messages = Object.fromEntries(
    Object.entries(catalogModules).map(([path, catalog]) => {
        const locale = path.match(/\.\/([^/]+)\.json$/)?.[1]
        if (!locale) {
            throw new Error(`Cannot determine locale from catalog path: ${path}`)
        }
        return [locale, catalog]
    })
) as Record<string, LocaleMessages>

export const supportedLocales = Object.freeze(Object.keys(messages).sort((left, right) => left.localeCompare(right, 'en')))

const localeLookup = new Map(supportedLocales.map((locale) => [locale.toLowerCase(), locale]))

const languageAliases: Readonly<Record<string, string>> = Object.freeze({
    pt: 'pt-BR',
    zh: 'zh-CN'
})

/** Resolve settings, environment, and browser locale values to an available catalog. */
export function resolveLocale(candidate?: string | null): string {
    const requested = candidate?.trim().replaceAll('_', '-')
    if (!requested) return 'en'

    let canonical = requested
    try {
        canonical = Intl.getCanonicalLocales(requested)[0] || requested
    } catch {
        // Keep the sanitized value so invalid input simply falls back below.
    }

    const exactMatch = localeLookup.get(canonical.toLowerCase())
    if (exactMatch) return exactMatch

    const language = canonical.split('-')[0]?.toLowerCase()
    if (!language) return 'en'

    const alias = languageAliases[language]
    if (alias && localeLookup.has(alias.toLowerCase())) return alias

    return localeLookup.get(language) || 'en'
}

/** Resolve writing direction by language, independently of the available catalogs. */
export function resolveLocaleDirection(candidate?: string | null): LocaleDirection {
    const requested = candidate?.trim().replaceAll('_', '-')
    if (!requested) return 'ltr'

    let canonical = requested
    try {
        canonical = Intl.getCanonicalLocales(requested)[0] || requested
    } catch {
        // Invalid or unknown locale input uses the safe LTR default below.
    }

    const language = canonical.split('-')[0]?.toLowerCase()
    return language && rtlLanguages.includes(language) ? 'rtl' : 'ltr'
}

/** Keep browser metadata and Vuetify's independent locale state in sync. */
export function synchronizeLocalePresentation(locale: string, vuetifyLocale?: VuetifyLocaleTarget): LocaleDirection {
    const direction = resolveLocaleDirection(locale)

    if (typeof document !== 'undefined') {
        document.documentElement.lang = locale
        document.documentElement.dir = direction
    }

    if (vuetifyLocale) {
        vuetifyLocale.current.value = locale
    }

    return direction
}

/** Exact locale keys consumed by Vuetify's RTL lookup. */
export const vuetifyRtlLocales: Readonly<Record<string, boolean>> = Object.freeze(
    Object.fromEntries(
        [...new Set([...supportedLocales, ...rtlLanguages])].map((locale) => [locale, resolveLocaleDirection(locale) === 'rtl'])
    )
)

/** Framework-owned labels (tables, pagination, dismiss buttons, etc.) for every locale Vuetify provides. */
export const vuetifyMessages = Object.freeze({
    ar,
    cs,
    de,
    en,
    es,
    fr,
    it,
    ja,
    ko,
    nl,
    pl,
    'pt-BR': pt,
    ru,
    sk,
    th,
    tr,
    uk,
    vi,
    'zh-CN': zhHans
})

export function getLocaleName(locale: string): string {
    const DisplayNames = Intl.DisplayNames
    if (typeof DisplayNames !== 'function') return locale

    try {
        if (DisplayNames.supportedLocalesOf([locale]).length > 0) {
            return new DisplayNames([locale], { type: 'language' }).of(locale) || locale
        }
    } catch {
        // Invalid or unsupported display locales continue to the deterministic
        // English fallback below.
    }

    try {
        return new DisplayNames(['en'], { type: 'language' }).of(locale) || locale
    } catch {
        return locale
    }
}

export const localeOptions: ReadonlyArray<LocaleOption> = Object.freeze(
    supportedLocales.map((locale) => ({
        id: locale,
        txt: getLocaleName(locale)
    }))
)
import { ar, cs, de, en, es, fr, it, ja, ko, nl, pl, pt, ru, sk, th, tr, uk, vi, zhHans } from 'vuetify/locale'
