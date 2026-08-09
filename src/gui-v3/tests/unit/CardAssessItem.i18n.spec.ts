import { mount } from '@vue/test-utils'
import { createI18n } from 'vue-i18n'
import { describe, expect, it } from 'vitest'
import CardAssessItem from '@/components/assess/CardAssessItem.vue'
import { Action } from '@/types/actions'

const BaseCardStub = {
    name: 'BaseCard',
    emits: ['card-click'],
    template: '<div class="base-card" @click="$emit(\'card-click\')"><slot name="content" /></div>'
}

const AssessItemActionsStub = {
    name: 'AssessItemActions',
    props: ['item'],
    emits: ['action'],
    template: `
        <div class="actions">
            <button class="update" @click.stop="$emit('action', '${Action.READ}')">update</button>
            <button class="delete" @click.stop="$emit('action', '${Action.DELETE}')">delete</button>
        </div>
    `
}

const passthroughStub = (name: string) => ({ name, template: '<div><slot /></div>' })

const i18n = () =>
    createI18n({
        legacy: false,
        locale: 'de',
        messages: {
            de: {
                card_item: {
                    source_with_type: 'Quelle {source}, Typ {type}',
                    unknown_source: 'Unbekannte Quelle',
                    published_at: 'Veröffentlicht {date}',
                    collected_at: 'Gesammelt {date}',
                    not_available: 'Nicht verfügbar'
                }
            }
        }
    })

const formatGermanDateTime = (value: string) =>
    new Intl.DateTimeFormat('de', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value))

const newsItem = {
    id: 42,
    title: 'Fallback title',
    description: 'Fallback review',
    comments: 'Comment',
    created: '2026-08-07T08:00:00Z',
    read: true,
    important: true,
    likes: 3,
    dislikes: 1,
    me_like: true,
    me_dislike: false,
    news_item_data: {
        source: 'مصدر الأخبار',
        osint_source_type: 'RSS Collector',
        published: '2026-08-08T09:00:00Z',
        collected: '2026-08-08T10:00:00Z',
        title: 'عنوان الخبر',
        review: 'وصف الخبر',
        link: 'https://example.test/item'
    }
}

const mountItem = (props: Record<string, unknown> = {}) =>
    mount(CardAssessItem, {
        props: { newsItem, ...props },
        global: {
            plugins: [i18n()],
            stubs: {
                BaseCard: BaseCardStub,
                AssessItemActions: AssessItemActionsStub,
                HighlightedText: { props: ['text'], template: '<span>{{ text }}</span>' },
                VRow: passthroughStub('VRow'),
                VCol: passthroughStub('VCol'),
                VSpacer: true
            }
        }
    })

describe('CardAssessItem locale-safe composition', () => {
    it('renders complete source/date messages and isolates dynamic values', () => {
        const published = formatGermanDateTime('2026-08-08T09:00:00Z')
        const collected = formatGermanDateTime('2026-08-08T10:00:00Z')
        const wrapper = mountItem()

        expect(wrapper.text()).toContain('Quelle مصدر الأخبار, Typ RSS')
        expect(wrapper.text()).toContain(`Veröffentlicht ${published}`)
        expect(wrapper.text()).toContain(`Gesammelt ${collected}`)
        expect(wrapper.findAll('bdi[dir="auto"]').map((node) => node.text())).toEqual(
            expect.arrayContaining(['مصدر الأخبار', 'RSS', published, collected, 'عنوان الخبر', 'وصف الخبر'])
        )
        expect(wrapper.findAll('bdi[dir="ltr"]').map((node) => node.text())).toEqual(['https://example.test/item'])
    })

    it('preserves invalid date values as display fallbacks', () => {
        const wrapper = mountItem({
            newsItem: {
                ...newsItem,
                created: 'original-created-date',
                news_item_data: {
                    ...newsItem.news_item_data,
                    published: 'وقت نشر قديم',
                    collected: 'وقت تجميع قديم'
                }
            }
        })

        expect(wrapper.text()).toContain('Veröffentlicht وقت نشر قديم')
        expect(wrapper.text()).toContain('Gesammelt وقت تجميع قديم')
        expect(wrapper.findAll('bdi[dir="auto"]').map((node) => node.text())).toEqual(
            expect.arrayContaining(['وقت نشر قديم', 'وقت تجميع قديم'])
        )
    })

    it('preserves detail and action event payloads', async () => {
        const wrapper = mountItem()
        await wrapper.get('.base-card').trigger('click')
        await wrapper.get('.update').trigger('click')
        await wrapper.get('.delete').trigger('click')

        const expectedItem = expect.objectContaining({
            id: 42,
            entityType: 'news_item',
            title: 'عنوان الخبر',
            description: 'وصف الخبر',
            comments: 'Comment',
            created: '2026-08-08T10:00:00Z',
            read: true,
            important: true,
            likes: 3,
            dislikes: 1,
            me_like: true,
            me_dislike: false,
            link: 'https://example.test/item',
            news_items: [newsItem]
        })

        expect(wrapper.emitted('show-detail')).toEqual([[expectedItem]])
        expect(wrapper.emitted('update-item')).toEqual([[expectedItem, Action.READ]])
        expect(wrapper.emitted('delete-item')).toEqual([[expectedItem]])
    })

    it('preserves fallbacks, event data, and analyze-selector visibility conditions', async () => {
        const fallback = {
            id: 7,
            title: 'عنوان بديل',
            description: 'مراجعة بديلة',
            news_item_data: {}
        }
        const wrapper = mountItem({ newsItem: fallback, analyzeSelector: true, hideReviews: true, hideSourceLinks: true })

        expect(wrapper.text()).toContain('Unbekannte Quelle')
        expect(wrapper.text()).toContain('Veröffentlicht Nicht verfügbar')
        expect(wrapper.text()).toContain('Gesammelt Nicht verfügbar')
        expect(wrapper.text()).not.toContain('N/A')
        expect(wrapper.findAll('bdi[dir="auto"]').map((node) => node.text())).toEqual(
            expect.arrayContaining(['Unbekannte Quelle', 'Nicht verfügbar'])
        )
        expect(wrapper.find('.actions').exists()).toBe(false)
        expect(wrapper.text()).not.toContain('مراجعة بديلة')
        expect(wrapper.find('.source-link').exists()).toBe(false)

        await wrapper.get('.base-card').trigger('click')
        expect(wrapper.emitted('show-detail')?.[0]?.[0]).toEqual(expect.objectContaining({ created: 'N/A' }))
    })
})
