import { createI18n } from 'vue-i18n'
import { describe, expect, it, vi } from 'vitest'
import { mountWithPlugins } from '../helpers/mount-helpers'
import NewsItemDetailDialog from '@/components/assess/NewsItemDetailDialog.vue'

vi.mock('@/composables/useAuth', () => ({
    useAuth: () => ({ checkPermission: () => true })
}))

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
                    source: 'Quelle',
                    attributes: 'Attribute'
                }
            }
        }
    })

const VDialogStub = {
    name: 'VDialog',
    template: '<div><slot /></div>'
}

const makeNewsItem = (data: Record<string, unknown>) => ({
    id: 1,
    entityType: 'news_item',
    title: 'عنوان الخبر',
    modify: true,
    news_items: [{ news_item_data: { content: '<p>Body</p>', attributes: [], ...data } }]
})

const mountDialog = (data: Record<string, unknown>) =>
    mountWithPlugins(NewsItemDetailDialog, {
        props: { modelValue: true, newsItem: makeNewsItem(data) },
        global: {
            plugins: [createMessages()],
            stubs: {
                VDialog: VDialogStub,
                AssessItemActions: true,
                NewsItemAttribute: true,
                Editor: true
            }
        }
    })

describe('NewsItemDetailDialog locale-safe metadata', () => {
    it('renders complete reorderable metadata messages with localized and isolated values', () => {
        const collected = '2026-08-09T10:00:00Z'
        const published = '2026-08-08T09:00:00Z'
        const expectedCollected = new Intl.DateTimeFormat('de', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(collected))
        const expectedPublished = new Intl.DateTimeFormat('de', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(published))
        const wrapper = mountDialog({
            collected,
            published,
            source: 'مصدر الأخبار',
            author: 'محرر',
            link: 'https://example.test/news/CVE-2026-1'
        })

        const header = wrapper.get('.source-header')
        expect(header.text()).toContain(`${expectedCollected} wurde erfasst`)
        expect(header.text()).toContain(`${expectedPublished} wurde veröffentlicht`)
        expect(header.text()).toContain('مصدر الأخبار ist die Quelle')
        expect(header.text()).toContain('محرر ist der Autor')
        expect(header.findAll('bdi[dir="auto"]').map((node) => node.text())).toEqual(
            expect.arrayContaining([expectedCollected, expectedPublished, 'مصدر الأخبار', 'محرر'])
        )

        const footer = wrapper.get('.source-footer')
        expect(footer.text()).toContain('Quelle öffnen: https://example.test/news/CVE-2026-1')
        expect(footer.get('a').attributes('href')).toBe('https://example.test/news/CVE-2026-1')
        expect(footer.get('a').attributes('rel')).toBe('noopener noreferrer')
        expect(footer.get('bdi[dir="ltr"]').text()).toBe('https://example.test/news/CVE-2026-1')
        expect(wrapper.get('.v-toolbar-title bdi[dir="auto"]').text()).toBe('عنوان الخبر')
    })

    it('uses the translated fallback while preserving invalid raw date values', () => {
        const wrapper = mountDialog({ collected: 'وقت قديم', published: '', source: '', author: '' })
        const header = wrapper.get('.source-header')

        expect(header.text()).toContain('وقت قديم wurde erfasst')
        expect(header.text()).toContain('Nicht verfügbar wurde veröffentlicht')
        expect(header.text()).toContain('Nicht verfügbar ist die Quelle')
        expect(header.text()).toContain('Nicht verfügbar ist der Autor')
        expect(header.findAll('bdi[dir="auto"]').map((node) => node.text())).toEqual(
            expect.arrayContaining(['وقت قديم', 'Nicht verfügbar', 'Nicht verfügbar'])
        )
        expect(wrapper.find('.source-footer').exists()).toBe(false)
    })

    it('shows unsafe source URLs as text without creating a clickable link', () => {
        const unsafeLink = 'javascript:alert(document.domain)'
        const wrapper = mountDialog({ link: unsafeLink })
        const footer = wrapper.get('.source-footer')

        expect(footer.text()).toContain(`Quelle öffnen: ${unsafeLink}`)
        expect(footer.find('a').exists()).toBe(false)
        expect(footer.get('bdi[dir="ltr"]').text()).toBe(unsafeLink)
    })
})
