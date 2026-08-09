import { describe, expect, it, vi } from 'vitest'
import { createI18n } from 'vue-i18n'
import { mountWithPlugins } from '../helpers/mount-helpers'
import CardAssess from '@/components/assess/CardAssess.vue'

vi.mock('@/composables/useAuth', () => ({
    useAuth: () => ({ checkPermission: () => false })
}))

const createCardMessages = () =>
    createI18n({
        legacy: false,
        locale: 'de',
        messages: {
            de: {
                card_item: {
                    source_with_type: '{source} ({type})',
                    unknown_source: 'Unknown source',
                    published_at: 'Published: {date}',
                    collected_at: 'Collected: {date}',
                    not_available: 'Not available',
                    aggregated_items_count: 'No news items | {count} news item | {count} news items',
                    in_analyze_count: 'No analyses in progress | {count} analysis in progress | {count} analyses in progress',
                    analyzed_count: 'No completed analyses | {count} completed analysis | {count} completed analyses'
                }
            }
        }
    })

const BaseCardStub = {
    name: 'BaseCard',
    template: '<div><slot name="content" /></div>'
}

const formatGermanDateTime = (value: string) =>
    new Intl.DateTimeFormat('de', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value))

const makeNewsItems = (count: number) =>
    Array.from({ length: count }, (_, index) => ({
        id: index + 1,
        news_item_data: index === 0 ? { source: 'Feed' } : {}
    }))

const mountCard = (card: Record<string, unknown>) =>
    mountWithPlugins(CardAssess, {
        props: { card: { id: 1, title: 'Title', description: 'Description', news_items: [], ...card } },
        global: {
            plugins: [createCardMessages()],
            stubs: {
                BaseCard: BaseCardStub,
                AssessItemActions: true,
                CardAssessItem: true,
                HighlightedText: {
                    props: ['text'],
                    template: '<span>{{ text }}</span>'
                },
                Transition: false
            }
        }
    })

describe('CardAssess locale-safe composition', () => {
    it('renders source/type and date rows as complete messages with isolated values', () => {
        const published = formatGermanDateTime('2026-08-08T09:00:00Z')
        const collected = formatGermanDateTime('2026-08-09T10:00:00Z')
        const wrapper = mountCard({
            title: 'عنوان الخبر',
            description: 'وصف الخبر',
            created: '2026-08-09T10:00:00Z',
            news_items: [
                {
                    id: 1,
                    news_item_data: {
                        source: 'مصدر الأخبار',
                        osint_source_type: 'RSS Collector',
                        published: '2026-08-08T09:00:00Z',
                        link: 'https://example.test/item'
                    }
                }
            ]
        })

        expect(wrapper.text()).toContain('مصدر الأخبار (RSS)')
        expect(wrapper.text()).toContain(`Published: ${published}`)
        expect(wrapper.text()).toContain(`Collected: ${collected}`)
        expect(wrapper.findAll('bdi[dir="auto"]').map((node) => node.text())).toEqual(
            expect.arrayContaining(['مصدر الأخبار', 'RSS', published, collected, 'عنوان الخبر', 'وصف الخبر'])
        )
        expect(wrapper.findAll('bdi[dir="ltr"]').map((node) => node.text())).toEqual(['https://example.test/item'])
    })

    it('preserves invalid date values as display fallbacks', () => {
        const wrapper = mountCard({
            created: 'وقت تجميع قديم',
            news_items: [{ id: 1, news_item_data: { published: 'وقت نشر قديم' } }]
        })

        expect(wrapper.text()).toContain('Published: وقت نشر قديم')
        expect(wrapper.text()).toContain('Collected: وقت تجميع قديم')
        expect(wrapper.findAll('bdi[dir="auto"]').map((node) => node.text())).toEqual(
            expect.arrayContaining(['وقت نشر قديم', 'وقت تجميع قديم'])
        )
    })

    it('uses translated fallbacks for a missing source and date', () => {
        const wrapper = mountCard({ news_items: [{ id: 1, news_item_data: {} }] })

        expect(wrapper.text()).toContain('Unknown source')
        expect(wrapper.text()).toContain('Published: Not available')
        expect(wrapper.text()).toContain('Collected: Not available')
        expect(wrapper.text()).not.toContain('N/A')
        expect(wrapper.findAll('bdi[dir="auto"]').map((node) => node.text())).toEqual(
            expect.arrayContaining(['Unknown source', 'Not available'])
        )
    })

    it('renders aggregate count as complete accessible text without overriding it with aria-label', () => {
        const wrapper = mountCard({ news_items: makeNewsItems(12000) })
        const aggregate = wrapper.get('[data-test="aggregate-count"]')

        expect(aggregate.text()).toContain('12.000 news items')
        expect(aggregate.attributes('aria-label')).toBeUndefined()
        expect(aggregate.html()).toContain('mdi-arrow-right-drop-circle')
    })

    it.each([
        [1, 0, '1 analysis in progress', undefined],
        [2, 1, '1 analysis in progress', '1 completed analysis'],
        [12000, 6000, '6.000 analyses in progress', '6.000 completed analyses']
    ])('renders report counts %i/%i as visible plural messages', (total, completed, inProgressText, completedText) => {
        const wrapper = mountCard({ news_items: [{ id: 1 }], in_reports_count: total, completed_reports_count: completed })

        const inProgress = wrapper.get('[data-test="in-progress-count"]')
        expect(inProgress.text()).toContain(inProgressText)
        expect(inProgress.attributes('aria-label')).toBeUndefined()

        if (completedText) {
            const complete = wrapper.get('[data-test="completed-count"]')
            expect(complete.text()).toContain(completedText)
            expect(complete.attributes('aria-label')).toBeUndefined()
        } else {
            expect(wrapper.find('[data-test="completed-count"]').exists()).toBe(false)
        }
    })
})
