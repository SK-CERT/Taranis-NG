import { describe, expect, it } from 'vitest'
import { messages, supportedLocales } from '@/i18n'
import exactCopyReviewed from '../fixtures/exact-copy-reviewed.json'

const auditedAuthRoots = [
    'access_management.users',
    'access_management.acls',
    'access_management.organizations',
    'access_management.security',
    'auth_provider',
    'security',
    'login'
]

const collectLeafPaths = (value, path, result = []) => {
    if (typeof value === 'string') result.push(path)
    else if (value && typeof value === 'object') {
        for (const [key, child] of Object.entries(value)) collectLeafPaths(child, `${path}.${key}`, result)
    }
    return result
}

const getMessage = (catalog, path) => path.split('.').reduce((value, segment) => value?.[segment], catalog)

const auditedAuthPaths = auditedAuthRoots.flatMap((root) => collectLeafPaths(getMessage(messages.en, root), root))

// These values are identifiers, protocol/product names, or a deliberately
// content-free interpolation template in every locale.
const universalExactCopyAllowlist = new Set([
    'auth_provider.id',
    'auth_provider.kinds.oidc',
    'auth_provider.kinds.oauth2',
    'auth_provider.kinds.ldap',
    'auth_provider.kinds.saml',
    'auth_provider.delete_message'
])

// Exact spelling can still be the correct translation. Keep these exceptions
// path-specific and locale-specific so an English sentence cannot hide behind
// a broad word/value allowlist.
const localeExactCopyAllowlists = {
    'cs': new Set([
        'access_management.users.email',
        'access_management.security.passkeys_title',
        'access_management.security.rp_id',
        'auth_provider.slug',
        'auth_provider.issuer_url',
        'auth_provider.client_id',
        'auth_provider.scopes',
        'auth_provider.pkce_method_plain',
        'auth_provider.secret',
        'auth_provider.token_url',
        'auth_provider.userinfo_url',
        'auth_provider.bind_dn',
        'auth_provider.search_base',
        'security.passkeys_title',
        'login.enroll_passkey_name'
    ]),
    'de': new Set([
        'access_management.users.name',
        'access_management.users.status',
        'access_management.acls.name',
        'access_management.acls.total_count',
        'access_management.organizations.name',
        'access_management.security.passkeys_title',
        'auth_provider.name',
        'auth_provider.scopes',
        'auth_provider.role_name',
        'security.passkeys_title',
        'security.passkey_name',
        'security.default_passkey_name',
        'login.enroll_passkey_name'
    ]),
    'es': new Set([
        'access_management.users.roles',
        'access_management.users.local_password',
        'access_management.acls.roles',
        'auth_provider.saml_tab_general',
        'login.enroll_passkey_name'
    ]),
    'fr': new Set([
        'access_management.users.email',
        'access_management.users.local_password',
        'access_management.acls.description',
        'access_management.organizations.description',
        'auth_provider.kind',
        'auth_provider.role_description'
    ]),
    'hi': new Set(['auth_provider.idp_sso_url']),
    'it': new Set([
        'access_management.users.password',
        'access_management.users.email',
        'security.default_passkey_name',
        'login.password',
        'login.enroll_passkey_name'
    ]),
    'ja': new Set(['auth_provider.idp_sso_url']),
    'ko': new Set(['auth_provider.idp_sso_url']),
    'nl': new Set([
        'access_management.users.email',
        'access_management.users.status',
        'access_management.users.identity_provider',
        'access_management.acls.item',
        'access_management.security.passkeys_title',
        'auth_provider.kind',
        'auth_provider.scopes',
        'security.passkeys_title',
        'security.default_passkey_name',
        'login.enroll_passkey_name'
    ]),
    'pl': new Set(['access_management.users.email', 'access_management.users.status']),
    'pt-BR': new Set([
        'access_management.users.email',
        'access_management.users.status',
        'access_management.users.local_password',
        'access_management.acls.item',
        'access_management.acls.total_count'
    ]),
    'sk': new Set([
        'access_management.users.email',
        'access_management.security.passkeys_title',
        'access_management.security.rp_id',
        'auth_provider.slug',
        'auth_provider.issuer_url',
        'auth_provider.client_id',
        'auth_provider.scopes',
        'auth_provider.pkce_method_plain',
        'auth_provider.secret',
        'auth_provider.token_url',
        'auth_provider.userinfo_url',
        'auth_provider.bind_dn',
        'auth_provider.search_base',
        'auth_provider.search_filter',
        'security.passkeys_title',
        'login.enroll_passkey_name'
    ]),
    'zh-CN': new Set(['auth_provider.idp_sso_url'])
}

const exactCopyIsReviewed = (locale, path) => universalExactCopyAllowlist.has(path) || localeExactCopyAllowlists[locale]?.has(path) === true

const reviewedExactCopyPaths = (locale) => new Set([...universalExactCopyAllowlist, ...(localeExactCopyAllowlists[locale] ?? [])])

// Every leaf in the English catalogue, which is the canonical set every other
// catalogue must cover. Built per top-level root so a string root yields its own
// path rather than a leading-dot one.
const allEnglishPaths = Object.keys(messages.en).flatMap((root) => collectLeafPaths(messages.en[root], root))

const auditedAuthPathSet = new Set(auditedAuthPaths)

// Arabic is deliberately excluded: BaseLanguageCatalogContracts.spec.js already holds
// the whole `ar` catalogue to a stricter form of this contract (leaf-order parity,
// plural forms, placeholder multiplicity and its own machine-label allowlist).
// Auditing it here too would only split that bookkeeping across two files.
const wholeCatalogueLocales = supportedLocales.filter((locale) => locale !== 'en' && locale !== 'ar')

// A value identical to English outside the audited scopes must be a deliberate choice:
// spec terminology (CVSS metric names, TLP codes), a technical token (URL, User-Agent),
// a pure interpolation template, or a word that genuinely spells the same in that
// language (fr "Description", de "Name"). `universal` holds the paths that apply to
// every catalogue; `byLocale` the rest.
const reviewedCopyFor = (locale) => new Set([...exactCopyReviewed.universal, ...(exactCopyReviewed.byLocale[locale] ?? [])])

describe('translated authentication and security content', () => {
    it('audits every leaf in the complete authentication and security scopes', () => {
        expect(auditedAuthPaths).toHaveLength(333)
        expect(new Set(auditedAuthPaths).size).toBe(auditedAuthPaths.length)
    })

    it('provides a string for every audited path in every catalog', () => {
        const invalidValues = []

        for (const locale of supportedLocales) {
            for (const path of auditedAuthPaths) {
                const value = getMessage(messages[locale], path)
                if (typeof value !== 'string') invalidValues.push(`${locale}: ${path} (${typeof value})`)
            }
        }

        expect(
            invalidValues,
            `Missing or non-string authentication messages (${invalidValues.length}):\n${invalidValues.map((entry) => `  - ${entry}`).join('\n')}`
        ).toEqual([])
    })

    it('keeps every exact-copy exception necessary and current', () => {
        const staleExceptions = []

        for (const locale of supportedLocales.filter((candidate) => candidate !== 'en')) {
            for (const path of reviewedExactCopyPaths(locale)) {
                if (getMessage(messages[locale], path) !== getMessage(messages.en, path)) {
                    staleExceptions.push(`${locale}: ${path}`)
                }
            }
        }

        expect(
            staleExceptions,
            `Stale exact-copy allowlist entries (${staleExceptions.length}):\n${staleExceptions.map((entry) => `  - ${entry}`).join('\n')}`
        ).toEqual([])
    })

    it('does not silently copy English UI text into non-English catalogs', () => {
        const unexpectedCopies = []

        for (const locale of supportedLocales.filter((candidate) => candidate !== 'en')) {
            for (const path of auditedAuthPaths) {
                const localizedValue = getMessage(messages[locale], path)
                if (typeof localizedValue !== 'string') continue

                if (localizedValue === getMessage(messages.en, path) && !exactCopyIsReviewed(locale, path)) {
                    unexpectedCopies.push(`${locale}: ${path}`)
                }
            }
        }

        expect(
            unexpectedCopies,
            `Unexpected exact English copies (${unexpectedCopies.length}):\n${unexpectedCopies.map((entry) => `  - ${entry}`).join('\n')}`
        ).toEqual([])
    })
})

// The block above holds the authentication and security scopes to a fully reviewed
// contract. These extend the same guarantee to the remaining ~1300 leaves, with the
// deliberate exact copies listed in tests/fixtures/exact-copy-reviewed.json.
describe('whole-catalogue translation contracts', () => {
    it('provides a string for every English path in every catalog', () => {
        const invalidValues = []

        for (const locale of supportedLocales.filter((candidate) => candidate !== 'en')) {
            for (const path of allEnglishPaths) {
                const value = getMessage(messages[locale], path)
                if (typeof value !== 'string') invalidValues.push(`${locale}: ${path} (${typeof value})`)
            }
        }

        expect(
            invalidValues,
            `Catalogs missing an English path (${invalidValues.length}):\n${invalidValues.map((entry) => `  - ${entry}`).join('\n')}`
        ).toEqual([])
    })

    it('keeps the reviewed exact-copy list within the scopes it covers', () => {
        const misplaced = []

        for (const [locale, paths] of Object.entries(exactCopyReviewed.byLocale)) {
            if (!wholeCatalogueLocales.includes(locale)) misplaced.push(`${locale}: not an audited catalogue`)
            for (const path of paths) {
                if (auditedAuthPathSet.has(path)) misplaced.push(`${locale}: ${path} belongs to the reviewed auth scopes`)
                else if (!allEnglishPaths.includes(path)) misplaced.push(`${locale}: ${path} is not an English path`)
            }
        }

        expect(
            misplaced,
            `Misplaced reviewed entries (${misplaced.length}):\n${misplaced.map((entry) => `  - ${entry}`).join('\n')}`
        ).toEqual([])
    })

    it('keeps every reviewed exact copy current', () => {
        const staleEntries = []

        for (const locale of wholeCatalogueLocales) {
            for (const path of reviewedCopyFor(locale)) {
                if (getMessage(messages[locale], path) !== getMessage(messages.en, path)) staleEntries.push(`${locale}: ${path}`)
            }
        }

        expect(
            staleEntries,
            `These are translated now — delete them from tests/fixtures/exact-copy-reviewed.json (${staleEntries.length}):\n${staleEntries
                .map((entry) => `  - ${entry}`)
                .join('\n')}`
        ).toEqual([])
    })

    it('adds no unreviewed English copy outside the audited scopes', () => {
        const newCopies = []

        for (const locale of wholeCatalogueLocales) {
            const reviewed = reviewedCopyFor(locale)
            for (const path of allEnglishPaths) {
                if (auditedAuthPathSet.has(path) || reviewed.has(path) || exactCopyIsReviewed(locale, path)) continue

                const localizedValue = getMessage(messages[locale], path)
                if (typeof localizedValue === 'string' && localizedValue === getMessage(messages.en, path)) {
                    newCopies.push(`${locale}: ${path}`)
                }
            }
        }

        expect(
            newCopies,
            `Untranslated English copies not in the reviewed list (${newCopies.length}):\n${newCopies
                .map((entry) => `  - ${entry}`)
                .join('\n')}`
        ).toEqual([])
    })
})
