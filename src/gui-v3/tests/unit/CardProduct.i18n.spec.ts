import { describe, expect, it, vi } from 'vitest'
import { createI18n } from 'vue-i18n'
import { mountWithPlugins } from '../helpers/mount-helpers'
import CardProduct from '@/components/publish/CardProduct.vue'

vi.mock('@/composables/useAuth', () => ({
    useAuth: () => ({ checkPermission: () => true })
}))

vi.mock('@/api/publish', async (importOriginal) => {
    const original = await importOriginal<typeof import('@/api/publish')>()
    return {
        ...original,
        deleteProduct: vi.fn().mockResolvedValue({ data: {} })
    }
})

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
                publish: {
                    updated_at: 'Aktualisiert am {date}',
                    updated_at_by: '{user} aktualisierte am {date}',
                    report_items_count: 'Keine Berichte | Ein Bericht | {count} Berichte'
                },
                workflow: { states: {} }
            }
        }
    })

const makeCard = (overrides: Record<string, unknown> = {}) => ({
    id: 1,
    title: 'Product title',
    subtitle: '',
    product_type_name: 'Advisory',
    updated_at: '2026-08-09T10:00:00Z',
    updated_by: '',
    report_items_count: 0,
    ...overrides
})

const mountCard = (overrides: Record<string, unknown> = {}) =>
    mountWithPlugins(CardProduct, {
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

describe('CardProduct locale-safe composition', () => {
    it('uses complete metadata variants and isolates dynamic human/date values', () => {
        const rawDate = '2026-08-09T10:00:00Z'
        const expectedDate = new Intl.DateTimeFormat('de', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(rawDate))
        const wrapper = mountCard({
            title: 'عنوان المنتج',
            subtitle: 'وصف المنتج',
            product_type_name: 'نشرة أمنية',
            state: { display_name: 'قيد النشر', description: 'وصف الحالة' },
            updated_at: rawDate,
            updated_by: 'ناشر'
        })

        expect(wrapper.text()).toContain(`ناشر aktualisierte am ${expectedDate}`)
        expect(wrapper.findAll('.product-card__updated bdi[dir="auto"]').map((node) => node.text())).toEqual(
            expect.arrayContaining(['ناشر', expectedDate])
        )
        expect(wrapper.findAll('bdi[dir="auto"]').map((node) => node.text())).toEqual(
            expect.arrayContaining(['نشرة أمنية', 'ناشر', expectedDate, 'عنوان المنتج', 'وصف المنتج'])
        )
        expect(wrapper.get('[data-test="confirmation"] bdi[dir="auto"]').text()).toBe('عنوان المنتج')
        expect(wrapper.get('.product-card__state').attributes('title')).toBe('\u2068وصف الحالة\u2069')
    })

    it('uses the no-user metadata variant and preserves an invalid raw timestamp', () => {
        const wrapper = mountCard({ updated_at: 'وقت قديم', updated_by: '' })

        expect(wrapper.get('.product-card__updated').text()).toContain('Aktualisiert am وقت قديم')
        expect(wrapper.get('.product-card__updated bdi[dir="auto"]').text()).toBe('وقت قديم')
        expect(wrapper.find('.product-card__updated bdi[dir="ltr"]').exists()).toBe(false)
    })

    it.each([
        [1, 'Ein Bericht'],
        [2, '2 Berichte'],
        [12000, '12.000 Berichte']
    ])('provides a complete accessible label for %i linked report items', (count, expected) => {
        const wrapper = mountCard({ report_items_count: count })
        const reportCount = wrapper.get('.product-card__report-count')

        expect(reportCount.get('.d-sr-only').text()).toBe(expected)
        expect(reportCount.attributes('title')).toBe(expected)
        expect(reportCount.text()).toContain(new Intl.NumberFormat('de').format(count))
        expect(reportCount.get('[aria-hidden="true"] + [aria-hidden="true"]').text()).toBe(new Intl.NumberFormat('de').format(count))
        expect(reportCount.attributes('aria-label')).toBeUndefined()
    })

    it('preserves the existing zero-count visibility condition', () => {
        const wrapper = mountCard({ report_items_count: 0 })

        expect(wrapper.find('.product-card__report-count').exists()).toBe(false)
    })
})
