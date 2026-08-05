type LocaleMessageValue = string | LocaleMessageDictionary | LocaleMessageValue[]
interface LocaleMessageDictionary {
    [key: string]: LocaleMessageValue
}
type LocaleMessages = LocaleMessageDictionary

export type LocaleOption = {
    id: string
    txt: string
}

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

function getLocaleName(locale: string): string {
    try {
        return new Intl.DisplayNames(['en'], { type: 'language' }).of(locale) || locale
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
