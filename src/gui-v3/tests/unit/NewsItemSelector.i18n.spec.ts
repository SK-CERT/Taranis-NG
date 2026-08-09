import { flushPromises, mount } from '@vue/test-utils'
import { createI18n } from 'vue-i18n'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import { describe, expect, it, vi } from 'vitest'
import NewsItemSelector from '@/components/analyze/NewsItemSelector.vue'

vi.mock('@/stores/assess', () => ({
    useAssessStore: () => ({
        getSelection: [],
        changeCurrentGroup: vi.fn(),
        multiSelect: vi.fn(),
        select: vi.fn()
    })
}))

vi.mock('@/stores/config', () => ({
    useConfigStore: () => ({
        loadOSINTSourceGroupsAssess: vi.fn().mockResolvedValue(undefined),
        osintSourceGroupsForAssess: []
    })
}))

vi.mock('@/composables/useAuth', () => ({
    useAuth: () => ({ checkPermission: () => true, getUserId: () => 1 })
}))

vi.mock('@/api/analyze', () => ({
    updateReportItem: vi.fn(),
    getReportItemData: vi.fn()
}))

const BaseCardStub = {
    name: 'BaseCard',
    template: '<div><slot name="content" /></div>'
}

const ConfirmationDialogStub = {
    name: 'ConfirmationDialog',
    props: ['modelValue'],
    template: '<div v-if="modelValue" data-test="remove-confirmation"><slot /></div>'
}

const messages = {
    de: {
        assess: {
            attached_news_items: 'Attached news items',
            read_news_item: 'Read news item',
            total_count: 'Total'
        },
        card_item: {
            published_at: 'Published: {date}',
            unknown_source: 'Unknown source',
            not_available: 'Not available',
            aggregated_items_count: 'No news items | {count} news item | {count} news items'
        },
        common: {
            add_items: 'Add items',
            remove: 'Remove',
            cancel: 'Cancel',
            messagebox: { remove: 'Remove item' }
        }
    }
}

const makeAggregate = (count: number) => ({
    id: 7,
    title: 'عنوان الخبر',
    description: 'وصف الخبر',
    news_items: Array.from({ length: count }, (_, index) => ({
        id: index + 1,
        news_item_data: index === 0 ? { source: 'مصدر الأخبار', published: '2026-08-08T09:00:00Z' } : {}
    }))
})

const formatGermanDateTime = (value: string) =>
    new Intl.DateTimeFormat('de', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value))

const mountSelector = (rtl = false, count = 12000, values = [makeAggregate(count)]) => {
    const i18n = createI18n({ legacy: false, locale: 'de', messages })
    const vuetify = createVuetify({
        components,
        directives,
        locale: { locale: rtl ? 'ar' : 'en', rtl: { ar: true } }
    })

    return mount(NewsItemSelector, {
        props: { values },
        global: {
            plugins: [i18n, vuetify],
            stubs: {
                BaseCard: BaseCardStub,
                CardAssessItem: { props: ['newsItem'], template: '<div class="child-item">{{ newsItem.id }}</div>' },
                ConfirmationDialog: ConfirmationDialogStub,
                ContentDataAssess: true,
                GroupNavList: true,
                NewsItemDetailDialog: true,
                ToolbarFilterAssess: true
            }
        }
    })
}

describe('NewsItemSelector locale-safe composition', () => {
    it('uses complete date/count messages, locale numbers, and isolated server values', async () => {
        const published = formatGermanDateTime('2026-08-08T09:00:00Z')
        const wrapper = mountSelector()
        await flushPromises()

        expect(wrapper.text()).toContain(`Published: ${published}`)
        expect(wrapper.text()).toContain('12.000 news items')
        expect(wrapper.findAll('bdi[dir="auto"]').map((node) => node.text())).toEqual(
            expect.arrayContaining(['مصدر الأخبار', published, 'عنوان الخبر', 'وصف الخبر'])
        )

        const aggregateButton = wrapper.findAllComponents({ name: 'VBtn' }).find((button) => button.text().includes('12.000 news items'))
        if (!aggregateButton) throw new Error('Aggregate button was not rendered')
        expect(aggregateButton.html()).toContain('mdi-arrow-right-drop-circle')

        const removeButton = wrapper.findAllComponents({ name: 'VBtn' }).find((button) => button.attributes('title') === 'Remove')
        if (!removeButton) throw new Error('Remove button was not rendered')
        await removeButton.trigger('click')
        expect(wrapper.get('[data-test="remove-confirmation"] bdi[dir="auto"]').text()).toBe('عنوان الخبر')
    })

    it.each([
        ['invalid', { source: '', published: 'وقت قديم' }, 'Published: وقت قديم'],
        ['missing', {}, 'Published: Not available']
    ])('uses translated/raw fallbacks for %s metadata', async (_case, newsItemData, publishedText) => {
        const wrapper = mountSelector(false, 1, [
            {
                id: 8,
                title: 'Fallback title',
                description: 'Fallback description',
                news_items: [{ id: 1, news_item_data: newsItemData }]
            }
        ])
        await flushPromises()

        expect(wrapper.text()).toContain('Unknown source')
        expect(wrapper.text()).toContain(publishedText)
        expect(wrapper.text()).not.toContain('N/A')
        expect(wrapper.findAll('bdi[dir="auto"]').map((node) => node.text())).toContain(
            'published' in newsItemData ? newsItemData.published : 'Not available'
        )
    })

    it('uses the semantic collapsed arrow for RTL without changing expansion behavior', async () => {
        const wrapper = mountSelector(true, 2)
        await flushPromises()

        const aggregateButton = wrapper.findAllComponents({ name: 'VBtn' }).find((button) => button.text().includes('2 news items'))
        if (!aggregateButton) throw new Error('Aggregate button was not rendered')
        expect(aggregateButton.html()).toContain('mdi-arrow-left-drop-circle')
        await aggregateButton.trigger('click')
        expect(aggregateButton.html()).toContain('mdi-arrow-down-drop-circle')
        expect(wrapper.findAll('.child-item')).toHaveLength(2)
    })
})
