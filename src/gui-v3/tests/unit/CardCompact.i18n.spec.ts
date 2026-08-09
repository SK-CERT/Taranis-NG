import { describe, expect, it, vi } from 'vitest'
import { createI18n } from 'vue-i18n'
import { mountWithPlugins } from '../helpers/mount-helpers'
import CardCompact from '@/components/common/CardCompact.vue'

vi.mock('@/composables/useAuth', () => ({
    useAuth: () => ({ checkPermission: () => false })
}))

const createCardMessages = () =>
    createI18n({
        legacy: false,
        locale: 'en',
        messages: {
            en: {
                card_item: {
                    in_analyze_count: 'No analyses in progress | {count} analysis in progress | {count} analyses in progress',
                    analyzed_count: 'No completed analyses | {count} completed analysis | {count} completed analyses'
                },
                analyze: {
                    news_items_count: 'No news items | {count} news item | {count} news items'
                },
                publish: {
                    report_items_count: 'No report items | {count} report item | {count} report items'
                }
            }
        }
    })

const mountCard = (card: Record<string, unknown>) =>
    mountWithPlugins(CardCompact, {
        props: { card },
        global: {
            plugins: [createCardMessages()],
            stubs: {
                ActionButton: true,
                ConfirmationDialog: true,
                HighlightedText: {
                    props: ['text'],
                    template: '<span>{{ text }}</span>'
                }
            }
        }
    })

describe('CardCompact localized status and bidi content', () => {
    it.each([
        [1, '1 analysis in progress'],
        [2, '2 analyses in progress'],
        [12000, '12,000 analyses in progress']
    ])('renders in-progress count %i as a complete plural message', (count, expected) => {
        const wrapper = mountCard({ news_items: [], in_reports_count: count })

        expect(wrapper.get('[data-test="in-progress-status"]').text()).toContain(expected)
    })

    it.each([
        [1, '1 completed analysis'],
        [2, '2 completed analyses'],
        [12000, '12,000 completed analyses']
    ])('renders completed count %i as a complete plural message', (count, expected) => {
        const wrapper = mountCard({ news_items: [], in_reports_count: count, completed_reports_count: count })

        expect(wrapper.get('[data-test="completed-status"]').text()).toContain(expected)
    })

    it('does not render empty status chips', () => {
        const wrapper = mountCard({ news_items: [], in_reports_count: 0, completed_reports_count: 0 })

        expect(wrapper.find('[data-test="in-progress-status"]').exists()).toBe(false)
        expect(wrapper.find('[data-test="completed-status"]').exists()).toBe(false)
    })

    it('locale-formats the review-item count and exposes one complete plural message', () => {
        const wrapper = mountCard({ news_items: [], news_items_count: 12000 })
        const count = wrapper.get('.compact-review-count')

        expect(count.attributes('title')).toBe('12,000 news items')
        expect(count.get('.d-sr-only').text()).toBe('12,000 news items')
        expect(count.get('span[aria-hidden="true"]').text()).toBe('12,000')
        expect(count.get('.v-icon').attributes('aria-hidden')).toBe('true')
    })

    it('announces report items for compact product cards', () => {
        const wrapper = mountCard({ product_type_name: 'PDF', report_items_count: 2 })
        const count = wrapper.get('.compact-review-count')

        expect(count.attributes('title')).toBe('2 report items')
        expect(count.get('.d-sr-only').text()).toBe('2 report items')
    })

    it('isolates dynamic provider, title, description, error, and workflow state labels', () => {
        const providerCard = mountCard({
            collector_id: 'collector-1',
            collector: { name: 'مزود RSS' },
            title: 'عنوان المصدر',
            description: 'وصف المصدر',
            last_error_message: 'خطأ التجميع'
        })
        const isolatedText = providerCard.findAll('bdi[dir="auto"]').map((node) => node.text())

        expect(isolatedText).toEqual(expect.arrayContaining(['مزود RSS', 'عنوان المصدر', 'وصف المصدر', 'خطأ التجميع']))

        const stateCard = mountCard({
            report_type_name: 'Report',
            state: { display_name: 'قيد المراجعة', description: 'حالة سير العمل' }
        })
        expect(stateCard.findAll('bdi[dir="auto"]').map((node) => node.text())).toContain('قيد المراجعة')
        expect(stateCard.findComponent({ name: 'VChip' }).attributes('title')).toBe('\u2068حالة سير العمل\u2069')
    })
})
