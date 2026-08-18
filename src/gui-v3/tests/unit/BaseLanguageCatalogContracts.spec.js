import { createI18n } from 'vue-i18n'
import { describe, expect, it } from 'vitest'
import ar from '@/i18n/ar.json'
import cs from '@/i18n/cs.json'
import en from '@/i18n/en.json'
import ru from '@/i18n/ru.json'
import sk from '@/i18n/sk.json'
import th from '@/i18n/th.json'
import tr from '@/i18n/tr.json'
import uk from '@/i18n/uk.json'
import { pluralRules } from '@/i18n'

const collectStrings = (value, path = [], result = []) => {
    if (typeof value === 'string') result.push([path.join('.'), value])
    else if (value && typeof value === 'object') {
        for (const [key, child] of Object.entries(value)) collectStrings(child, [...path, key], result)
    }
    return result
}

const placeholderNames = (message) => [...new Set([...message.matchAll(/\{([^}]+)\}/g)].map((match) => match[1]))].sort()
const placeholderOccurrences = (message) => [...message.matchAll(/\{([^}]+)\}/g)].map((match) => match[1]).sort()

describe('Arabic production catalog contracts', () => {
    const englishStrings = collectStrings(en)
    const arabicStrings = collectStrings(ar)
    const arabicByPath = new Map(arabicStrings)

    it('matches the post-cleanup canonical English leaf order', () => {
        expect(englishStrings).toHaveLength(1804)
        expect(arabicStrings).toHaveLength(1804)
        expect(arabicStrings.map(([path]) => path)).toEqual(englishStrings.map(([path]) => path))
    })

    it('preserves exact named-placeholder multiplicity for every semantic branch', () => {
        for (let index = 0; index < englishStrings.length; index += 1) {
            const [path, englishMessage] = englishStrings[index]
            const arabicMessage = arabicStrings[index][1]
            const englishForms = englishMessage.split('|')
            const arabicForms = arabicMessage.split('|')

            if (englishForms.length === 1) {
                expect(placeholderOccurrences(arabicMessage), path).toEqual(placeholderOccurrences(englishMessage))
                continue
            }

            expect(arabicForms, path).toHaveLength(6)
            const sourceFormForArabic =
                englishForms.length === 3
                    ? [englishForms[0], englishForms[1], englishForms[2], englishForms[2], englishForms[2], englishForms[2]]
                    : [englishForms[1], englishForms[0], englishForms[1], englishForms[1], englishForms[1], englishForms[1]]
            for (let formIndex = 0; formIndex < arabicForms.length; formIndex += 1) {
                expect(placeholderOccurrences(arabicForms[formIndex]), `${path} form ${formIndex}`).toEqual(
                    placeholderOccurrences(sourceFormForArabic[formIndex])
                )
            }
        }
    })

    it('provides six nonempty forms for all 55 canonical count messages', () => {
        const pluralMessages = englishStrings.filter(([, message]) => message.includes('|'))
        expect(pluralMessages).toHaveLength(55)

        for (const [path] of pluralMessages) {
            const forms = arabicByPath.get(path).split('|')
            expect(forms, path).toHaveLength(6)
            expect(
                forms.every((form) => form.trim().length > 0),
                path
            ).toBe(true)
        }
    })

    it('preserves protocol and machine literals in their canonical messages', () => {
        const literals = [
            'LDAP',
            'OpenID Connect',
            'OAuth',
            'SAML',
            'PKCE',
            'TOTP',
            'WebAuthn',
            'CVSS',
            'CPE',
            'CVE',
            'CWE',
            'URL',
            'URI',
            'API',
            'ACL',
            'OSINT',
            'PEM',
            'DN',
            'RDN',
            'TLS',
            'HTTP',
            'XML',
            'SSO',
            'WAYF',
            'eduGAIN',
            'InCommon',
            'DFN-AAI',
            'S256',
            'TLP'
        ]

        for (let index = 0; index < englishStrings.length; index += 1) {
            const [path, englishMessage] = englishStrings[index]
            const arabicMessage = arabicStrings[index][1]
            const englishForms = englishMessage.split('|')
            const arabicForms = arabicMessage.split('|')
            const sourceForms =
                englishForms.length === 3
                    ? [englishForms[0], englishForms[1], englishForms[2], englishForms[2], englishForms[2], englishForms[2]]
                    : englishForms.length === 2
                      ? [englishForms[1], englishForms[0], englishForms[1], englishForms[1], englishForms[1], englishForms[1]]
                      : englishForms
            for (const literal of literals) {
                for (let formIndex = 0; formIndex < sourceForms.length; formIndex += 1) {
                    const expected = sourceForms[formIndex].split(literal).length - 1
                    if (expected > 0) {
                        expect(arabicForms[formIndex].split(literal).length - 1, `${path} form ${formIndex}: ${literal}`).toBe(expected)
                    }
                }
            }
        }
    })

    it('does not resurrect the proven obsolete keys or use pseudo-plurals', () => {
        const obsoletePaths = [
            'assess.author',
            'assess.collected',
            'assess.link',
            'assess.published',
            'card_item.analyzed',
            'card_item.collected',
            'card_item.in_analyze',
            'card_item.published',
            'card_item.source',
            'card_item.updated',
            'auth_provider.saml_acs_url',
            'auth_provider.saml_disco_url',
            'auth_provider.saml_metadata_url',
            'drop_zone.last_updated',
            'report_item.id',
            'settings.default_value',
            'settings.press_key'
        ]

        const arabicPaths = new Set(arabicStrings.map(([path]) => path))
        for (const path of obsoletePaths) expect(arabicPaths.has(path), path).toBe(false)
        for (const [path, message] of arabicStrings) expect(message, path).not.toMatch(/\b[\p{L}\p{N}_-]+\(s\)/u)
    })

    it('contains no unchanged English fallback outside reviewed machine labels', () => {
        const machineOnlyPaths = new Set([
            'access_management.organizations.zip',
            'nav_menu.acls',
            'card_item.source_with_type',
            'card_item.url',
            'attribute.tlp_clear',
            'attribute.tlp_green',
            'attribute.tlp_amber',
            'attribute.tlp_amber_strict',
            'attribute.tlp_red',
            'collectors.nodes.api_url',
            // Protocol and web-standard names: the HSTS response header, and the
            // favicon, are spelled the same wherever they appear.
            'public_web.webs.hsts',
            'public_web.webs.image_favicon',
            'routing.hsts_title',
            'presenters.nodes.url',
            'presenters.nodes.api_url',
            'publishers.nodes.url',
            'publishers.nodes.api_url',
            'bots.nodes.url',
            'bots.nodes.api_url',
            'data_providers.data.api_url',
            'data_providers.data.user_agent',
            'data_providers.ai.api_url',
            'word_lists.link',
            'auth_provider.id',
            'auth_provider.kinds.oidc',
            'auth_provider.kinds.oauth2',
            'auth_provider.kinds.ldap',
            'auth_provider.kinds.saml',
            'attribute.binary_description_with_details',
            'analyze.title_with_prefix',
            'settings.language_name_with_code',
            'auth_provider.delete_message'
        ])

        for (let index = 0; index < englishStrings.length; index += 1) {
            const [path, englishMessage] = englishStrings[index]
            if (!machineOnlyPaths.has(path)) expect(arabicStrings[index][1], path).not.toBe(englishMessage)
        }
    })
})

describe.each([
    ['cs', cs],
    ['sk', sk],
    ['ru', ru],
    ['uk', uk]
])('%s base-language catalog contracts', (locale, catalog) => {
    const englishStrings = collectStrings(en)
    const localizedStrings = collectStrings(catalog)

    it('matches the canonical English key order and placeholder names', () => {
        expect(englishStrings).toHaveLength(1804)
        expect(localizedStrings).toHaveLength(1804)
        expect(localizedStrings.map(([path]) => path)).toEqual(englishStrings.map(([path]) => path))

        for (let index = 0; index < englishStrings.length; index += 1) {
            const [path, englishMessage] = englishStrings[index]
            const localizedMessage = localizedStrings[index][1]
            expect(placeholderNames(localizedMessage), path).toEqual(placeholderNames(englishMessage))
        }
    })

    it('provides four nonempty forms for every canonical count message', () => {
        const localizedByPath = new Map(localizedStrings)
        const pluralMessages = englishStrings.filter(([, message]) => message.includes('|'))

        for (const [path] of pluralMessages) {
            const forms = localizedByPath.get(path).split('|')
            expect(forms, path).toHaveLength(4)
            expect(
                forms.every((form) => form.trim().length > 0),
                path
            ).toBe(true)
        }
    })

    it('does not use English pseudo-plurals', () => {
        for (const [path, message] of localizedStrings) expect(message, path).not.toMatch(/\b[\p{L}\p{N}_-]+\(s\)/u)
    })
})

describe.each([
    ['tr', tr],
    ['th', th]
])('%s invariant-plural catalog contracts', (locale, catalog) => {
    const englishStrings = collectStrings(en)
    const localizedStrings = collectStrings(catalog)

    it('matches the canonical English leaf order and placeholder names', () => {
        expect(englishStrings).toHaveLength(1804)
        expect(localizedStrings).toHaveLength(1804)
        expect(localizedStrings.map(([path]) => path)).toEqual(englishStrings.map(([path]) => path))

        for (let index = 0; index < englishStrings.length; index += 1) {
            const [path, englishMessage] = englishStrings[index]
            expect(placeholderNames(localizedStrings[index][1]), path).toEqual(placeholderNames(englishMessage))
        }
    })

    it('provides natural zero, one and invariant-other forms for every canonical count message', () => {
        const localizedByPath = new Map(localizedStrings)
        for (const [path] of englishStrings.filter(([, message]) => message.includes('|'))) {
            const forms = localizedByPath.get(path).split('|')
            expect(forms, path).toHaveLength(3)
            expect(
                forms.every((form) => form.trim().length > 0),
                path
            ).toBe(true)
        }
    })
})

describe('base-language plural rendering', () => {
    it('renders real Arabic zero, one, two, few, many and other forms through Vue-I18n', () => {
        const { t } = createI18n({ legacy: false, locale: 'ar', messages: { ar }, pluralRules }).global
        const counts = [0, 1, 2, 3, 5, 10, 11, 12, 21, 99, 100, 102, 103]

        expect(counts.map((count) => t('asset.total_count', { count: String(count) }, count))).toEqual([
            'لا توجد أصول (0)',
            'أصل واحد (1)',
            'أصلان (2)',
            '3 أصول',
            '5 أصول',
            '10 أصول',
            '11 أصلًا',
            '12 أصلًا',
            '21 أصلًا',
            '99 أصلًا',
            '100 أصل',
            '102 أصل',
            '103 أصول'
        ])

        expect(t('presenters.nodes.total_count', { count: '2' }, 2)).toBe('عقدتا عرض (2)')
        expect(t('auth_provider.idp_metadata_loaded', { count: '0' }, 0)).toBe(
            'حُمّلت البيانات الوصفية من دون شهادات توقيع (0). راجع الحقول أدناه واحفظ.'
        )
        expect(t('auth_provider.idp_metadata_loaded', { count: '2' }, 2)).toBe(
            'حُمّلت البيانات الوصفية مع شهادتي توقيع (2). راجع الحقول أدناه واحفظ.'
        )
        expect(t('auth_provider.idp_metadata_loaded', { count: '11' }, 11)).toBe(
            'حُمّلت البيانات الوصفية مع 11 شهادة توقيع. راجع الحقول أدناه واحفظ.'
        )
        expect(t('analyze.news_items_count', { count: '102' }, 102)).toBe('102 عنصر إخباري')
    })

    it.each([
        ['cs', cs, ['Žádné kódy CPE', '1 kód CPE', '2 kódy CPE', '5 kódů CPE', '21 kódů CPE']],
        ['sk', sk, ['Žiadne kódy CPE', '1 kód CPE', '2 kódy CPE', '5 kódov CPE', '21 kódov CPE']]
    ])('renders %s zero, one, few and many forms', (locale, messages, expected) => {
        const { t } = createI18n({ legacy: false, locale, messages: { [locale]: messages }, pluralRules }).global

        expect([0, 1, 2, 5, 21].map((count) => t('asset.cpe_count', { count: String(count) }, count))).toEqual(expected)
        expect(t('asset.cpe_count', { count: '12' }, 12)).toBe(expected[3].replace('5', '12'))
    })

    it.each([
        [
            'ru',
            ru,
            [
                'Нет кодов CPE',
                '1 код CPE',
                '2 кода CPE',
                '5 кодов CPE',
                '11 кодов CPE',
                '12 кодов CPE',
                '21 код CPE',
                '22 кода CPE',
                '25 кодов CPE'
            ]
        ],
        [
            'uk',
            uk,
            [
                'Немає кодів CPE',
                '1 код CPE',
                '2 коди CPE',
                '5 кодів CPE',
                '11 кодів CPE',
                '12 кодів CPE',
                '21 код CPE',
                '22 коди CPE',
                '25 кодів CPE'
            ]
        ]
    ])('renders %s teen and compound count forms', (locale, messages, expected) => {
        const { t } = createI18n({ legacy: false, locale, messages: { [locale]: messages }, pluralRules }).global
        const counts = [0, 1, 2, 5, 11, 12, 21, 22, 25]

        expect(counts.map((count) => t('asset.cpe_count', { count: String(count) }, count))).toEqual(expected)
    })

    it.each([
        ['tr', tr, ['CPE kodu yok', '1 CPE kodu', '2 CPE kodu', '5 CPE kodu', '21 CPE kodu']],
        ['th', th, ['ไม่มีรหัส CPE', 'รหัส CPE 1 รายการ', 'รหัส CPE 2 รายการ', 'รหัส CPE 5 รายการ', 'รหัส CPE 21 รายการ']]
    ])('renders %s natural zero and invariant number forms', (locale, messages, expected) => {
        const { t } = createI18n({ legacy: false, locale, messages: { [locale]: messages }, pluralRules }).global
        const counts = [0, 1, 2, 5, 21]

        expect(counts.map((count) => t('asset.cpe_count', { count: String(count) }, count))).toEqual(expected)
    })
})
