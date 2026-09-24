import { describe, expect, it, vi } from 'vitest'
import { createI18n } from 'vue-i18n'
import { mountWithPlugins } from '../helpers/mount-helpers'
import CardAnalyze from '@/components/analyze/CardAnalyze.vue'

vi.mock('vue-router', () => ({
    useRoute: () => ({ path: '/analyze/local', params: { scope: 'local' } }),
    useRouter: () => ({ push: vi.fn() })
}))

vi.mock('@/composables/useAuth', () => ({
    useAuth: () => ({ checkPermission: () => true })
}))

vi.mock('@/api/analyze', () => ({
    deleteReportItem: vi.fn().mockResolvedValue({ data: {} })
}))

const BaseCardStub = {
    name: 'BaseCard',
    template: '<div><slot name="content" /></div>'
}

const ConfirmationDialogStub = {
    name: 'ConfirmationDialog',
    template: '<div data-test="confirmation"><slot /></div>'
}

const createCardMessages = () =>
    createI18n({
        legacy: false,
        locale: 'de',
        messages: {
            de: {
                analyze: {
                    updated_at: 'Aktualisiert am {date}',
                    updated_at_by: '{user} aktualisierte am {date}',
                    title_with_prefix: '{title} // {prefix}',
                    news_items_count: 'Keine Nachrichten | Eine Nachricht | {count} Nachrichten'
                },
                workflow: { states: {} }
            }
        }
    })

const makeCard = (overrides: Record<string, unknown> = {}) => ({
    id: 1,
    title: 'Report title',
    report_type_name: 'Advisory',
    last_updated: '2026-08-09T10:00:00Z',
    updated_by: '',
    news_items_count: 0,
    modify: true,
    access: true,
    remote_user: null,
    ...overrides
})

const mountCard = (overrides: Record<string, unknown> = {}) =>
    mountWithPlugins(CardAnalyze, {
        props: { card: makeCard(overrides) },
        global: {
            plugins: [createCardMessages()],
            stubs: {
                BaseCard: BaseCardStub,
                ActionButton: true,
                ConfirmationDialog: ConfirmationDialogStub
            }
        }
    })

describe('CardAnalyze locale-safe composition', () => {
    it('uses complete reorderable metadata and title messages with isolated values', () => {
        const rawDate = '2026-08-09T10:00:00Z'
        const expectedDate = new Intl.DateTimeFormat('de', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(rawDate))
        const wrapper = mountCard({
            title: 'عنوان التقرير',
            title_prefix: 'بادئة',
            report_type_name: 'تقرير أمني',
            state: { display_name: 'قيد المراجعة', description: 'وصف الحالة' },
            last_updated: rawDate,
            updated_by: 'محلل'
        })

        const text = wrapper.text()
        expect(text).toContain(`محلل aktualisierte am ${expectedDate}`)
        expect(text.indexOf('عنوان التقرير')).toBeLessThan(text.indexOf('بادئة'))
        expect(wrapper.findAll('.report-card__updated bdi[dir="auto"]').map((node) => node.text())).toEqual(
            expect.arrayContaining(['محلل', expectedDate])
        )
        expect(wrapper.findAll('bdi[dir="auto"]').map((node) => node.text())).toEqual(
            expect.arrayContaining(['تقرير أمني', 'محلل', expectedDate, 'عنوان التقرير', 'بادئة'])
        )
        expect(wrapper.findAll('[data-test="confirmation"] bdi[dir="auto"]').map((node) => node.text())).toEqual([
            'عنوان التقرير',
            'عنوان التقرير'
        ])
        expect(wrapper.get('.report-card__state').attributes('title')).toBe('\u2068وصف الحالة\u2069')
    })

    it('uses the no-user metadata variant and preserves an invalid raw timestamp', () => {
        const wrapper = mountCard({ last_updated: 'وقت قديم', updated_by: '' })

        expect(wrapper.get('.report-card__updated').text()).toContain('Aktualisiert am وقت قديم')
        expect(wrapper.get('.report-card__updated bdi[dir="auto"]').text()).toBe('وقت قديم')
        expect(wrapper.find('.report-card__updated bdi[dir="ltr"]').exists()).toBe(false)
    })

    it.each([
        [1, 'Eine Nachricht'],
        [2, '2 Nachrichten'],
        [12000, '12.000 Nachrichten']
    ])('provides a complete accessible label for %i linked news items', (count, expected) => {
        const wrapper = mountCard({ news_items_count: count })
        const sourceCount = wrapper.get('.report-card__source-count')

        expect(sourceCount.get('.d-sr-only').text()).toBe(expected)
        expect(sourceCount.attributes('title')).toBe(expected)
        expect(sourceCount.text()).toContain(new Intl.NumberFormat('de').format(count))
        expect(sourceCount.get('[aria-hidden="true"] + [aria-hidden="true"]').text()).toBe(new Intl.NumberFormat('de').format(count))
    })

    it('preserves the existing zero-count visibility condition', () => {
        const wrapper = mountCard({ news_items_count: 0 })

        expect(wrapper.find('.report-card__source-count').exists()).toBe(false)
    })
})
