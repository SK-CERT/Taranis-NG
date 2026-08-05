const catalogContext = require.context('./', true, /^\.\/[^/]+\/messages\.js$/);

const messages = {};

catalogContext.keys().forEach(path => {
    const locale = path.split('/')[1];
    const catalogModule = catalogContext(path);
    messages[locale] = catalogModule.default || catalogModule;
});

export const supportedLocales = Object.freeze(Object.keys(messages).sort());

const localeLookup = supportedLocales.reduce((lookup, locale) => {
    lookup[locale.toLowerCase()] = locale;
    return lookup;
}, {});

/** Resolve configured and browser locale values to an available catalog. */
export function resolveLocale(candidate) {
    const requested = String(candidate || '').trim().replace(/_/g, '-');
    if (!requested) {
        return 'en';
    }

    let canonical = requested;
    try {
        if (typeof Intl !== 'undefined' && Intl.getCanonicalLocales) {
            canonical = Intl.getCanonicalLocales(requested)[0] || requested;
        }
    } catch (e) {
        // Invalid locale values fall through to the English fallback.
    }

    const exactMatch = localeLookup[canonical.toLowerCase()];
    if (exactMatch) {
        return exactMatch;
    }

    const language = canonical.split('-')[0].toLowerCase();
    if (localeLookup[language]) {
        return localeLookup[language];
    }

    const regionalMatch = supportedLocales.find(locale => locale.toLowerCase().indexOf(language + '-') === 0);
    return regionalMatch || 'en';
}

export default messages;
