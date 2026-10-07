import { createI18n } from 'vue-i18n'
import { describe, expect, it } from 'vitest'
import { mountWithPlugins } from '../helpers/mount-helpers'
import NewsItemSourcePane from '@/components/assess/NewsItemSourcePane.vue'

const createMessages = () =>
    createI18n({
        legacy: false,
        locale: 'de',
        messages: {
            de: {
                card_item: {
                    collected_at: '{date} wurde erfasst',
                    published_at: '{date} wurde veröffentlicht',
                    source_with_value: '{source} ist die Quelle',
                    author_with_value: '{author} ist der Autor',
                    link_with_url: 'Quelle öffnen: {url}',
                    not_available: 'Nicht verfügbar'
                },
                assess: {
                    superseded_at: 'Am {date} ersetzt'
                }
            }
        }
    })

const formatGerman = (value: string) => new Intl.DateTimeFormat('de', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value))

const mountPane = (props: Record<string, unknown>) => mountWithPlugins(NewsItemSourcePane, { props, global: { plugins: [createMessages()] } })

describe('NewsItemSourcePane', () => {
    it('shows one revision: its metadata, content and link', () => {
        const wrapper = mountPane({
            collected: '2026-09-01T10:00:00Z',
            published: '2026-09-01T09:00:00Z',
            source: 'https://example.com/csaf',
            author: 'Example PSIRT',
            content: '<p>Advisory text</p>',
            link: 'https://example.com/advisory'
        })

        const header = wrapper.get('.source-header')
        expect(header.text()).toContain(`${formatGerman('2026-09-01T10:00:00Z')} wurde erfasst`)
        expect(header.text()).toContain('Example PSIRT ist der Autor')
        // Sanitizing itself is covered by sanitizeNewsItemHtml.spec.ts, which needs jsdom.
        expect(wrapper.get('.source-body').text()).toContain('Advisory text')
        expect(wrapper.get('.source-footer a').attributes('href')).toBe('https://example.com/advisory')
    })

    it('says when a newer version replaced an older one', () => {
        const wrapper = mountPane({ content: '<p>Old</p>', superseded: '2026-09-10T08:00:00Z' })
        expect(wrapper.get('[data-test="superseded-notice"]').text()).toBe(`Am ${formatGerman('2026-09-10T08:00:00Z')} ersetzt`)
    })

    it('shows no notice for the current version, and no footer without a link', () => {
        const wrapper = mountPane({ content: '<p>Current</p>' })
        expect(wrapper.find('[data-test="superseded-notice"]').exists()).toBe(false)
        expect(wrapper.find('.source-footer').exists()).toBe(false)
        expect(wrapper.get('.source-header').text()).toContain('Nicht verfügbar ist die Quelle')
    })
})
