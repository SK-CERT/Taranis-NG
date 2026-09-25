import { createI18n } from 'vue-i18n'
import { describe, expect, it } from 'vitest'
import en from '@/i18n/en.json'

const getMessage = (path) => path.split('.').reduce((value, key) => value?.[key], en)

const dynamicContracts = [
    'analyze.updated_at',
    'analyze.updated_at_by',
    'publish.updated_at',
    'publish.updated_at_by',
    'dashboard.metrics.news_items_summary',
    'dashboard.metrics.report_items_summary',
    'dashboard.metrics.products_summary',
    'word_cloud.label',
    'word_cloud.word_action_count',
    'attribute.tlp_description_clear',
    'attribute.tlp_description_green',
    'attribute.tlp_description_amber',
    'attribute.tlp_description_amber_strict',
    'attribute.tlp_description_red',
    'attribute.tlp_description_unknown',
    'common.publish',
    'common.lock',
    'common.open',
    'common.open_source',
    'common.fetching_items',
    'common.no_items_to_select',
    'common.select_at_least_two_to_group',
    'common.no_grouped_items_selected',
    'common.processing_items',
    'common.deleting_items'
]

const collectStrings = (value, path = [], result = []) => {
    if (typeof value === 'string') result.push([path.join('.'), value])
    else if (value && typeof value === 'object') {
        for (const [key, child] of Object.entries(value)) collectStrings(child, [...path, key], result)
    }
    return result
}

describe('canonical English translation contracts', () => {
    it('contains source contracts that static key analysis cannot enumerate', () => {
        for (const path of dynamicContracts) expect(getMessage(path), path).toEqual(expect.any(String))
    })

    it('uses valid pipe variants and semantic named placeholders', () => {
        const strings = collectStrings(en)
        const pluralMessages = strings.filter(([, message]) => message.includes('|'))

        expect(pluralMessages.length).toBeGreaterThan(40)
        for (const [path, message] of pluralMessages) {
            expect(
                message.split('|').every((variant) => variant.trim().length > 0),
                path
            ).toBe(true)
        }
        for (const [path, message] of strings) {
            expect(message, path).not.toMatch(/\b[\p{L}\p{N}_-]+\(s\)/u)
            expect(
                [...message.matchAll(/\{([^}]+)\}/g)].map((match) => match[1]),
                path
            ).not.toContainEqual(expect.stringMatching(/^\d+$/))
        }

        const dynamicToolbarCounts = strings.filter(([path]) => path.endsWith('.total_count') || path.endsWith('.selected_count'))
        for (const [path, message] of dynamicToolbarCounts) {
            expect(message, path).toContain('|')
            expect(message, path).toContain('{count}')
        }
    })

    it('selects English zero, singular and plural messages with named values intact', () => {
        const { t } = createI18n({ legacy: false, locale: 'en', messages: { en } }).global

        expect(t('dashboard.metrics.news_items_summary', { count: '0' }, 0)).toBe('No news items')
        expect(t('dashboard.metrics.news_items_summary', { count: '1' }, 1)).toBe('1 news item in total')
        expect(t('dashboard.metrics.news_items_summary', { count: '2' }, 2)).toBe('2 news items in total')
        expect(t('auth_provider.idp_metadata_loaded', { count: '1' }, 1)).toContain('1 signing certificate.')
        expect(t('auth_provider.idp_metadata_loaded', { count: '2' }, 2)).toContain('2 signing certificates.')
        expect(t('auth_provider.delete_message_linked', { name: 'Example IdP', count: '2' }, 2)).toBe(
            'Example IdP: 2 linked user identities will lose this login method'
        )
    })
})
