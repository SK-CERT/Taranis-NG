import { createI18n } from 'vue-i18n'
import { flushPromises } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mountWithPlugins } from '../helpers/mount-helpers'
import NewsItemDetailDialog from '@/components/assess/NewsItemDetailDialog.vue'

vi.mock('@/composables/useAuth', () => ({
    useAuth: () => ({ checkPermission: () => true })
}))

const { getNewsItemVersions } = vi.hoisted(() => ({ getNewsItemVersions: vi.fn() }))
vi.mock('@/api/assess', () => ({ getNewsItemVersions }))

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
                    attributes: 'Attribute',
                    version_label: 'Fassung {version}',
                    current_version_label: 'Fassung {version} (aktuell)',
                    superseded_at: 'Am {date} ersetzt'
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

const formatGerman = (value: string) => new Intl.DateTimeFormat('de', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value))

const versionedItem = (data: Record<string, unknown> = {}) => ({
    id: 1,
    entityType: 'news_item',
    title: 'EX-2026-001: Example',
    modify: true,
    news_items: [
        {
            id: 7,
            news_item_data: {
                id: 'data-1',
                hash: 'hash-2',
                version: '2',
                content: '<p>Second revision</p>',
                link: 'https://example.test/advisory',
                attributes: [],
                ...data
            }
        }
    ]
})

const versions = {
    data: {
        items: [
            { id: null, version: '2', content: '<p>Second revision</p>', current: true, superseded: null },
            {
                id: 11,
                version: '1',
                content: '<p>First revision</p>',
                collected: '2026-09-01T10:00:00Z',
                published: '2026-09-01T09:00:00Z',
                author: 'Example PSIRT',
                link: 'https://example.test/advisory',
                superseded: '2026-09-10T08:00:00Z',
                current: false
            }
        ]
    }
}

const mountVersioned = (newsItem: Record<string, unknown>) =>
    mountWithPlugins(NewsItemDetailDialog, {
        props: { modelValue: true, newsItem },
        global: {
            plugins: [createMessages()],
            stubs: { VDialog: VDialogStub, AssessItemActions: true, NewsItemAttribute: true, Editor: true }
        }
    })

const activePane = (wrapper: ReturnType<typeof mountVersioned>) => wrapper.get('.pane.pane--active')

describe('NewsItemDetailDialog versions', () => {
    beforeEach(() => {
        getNewsItemVersions.mockReset()
    })

    it('keeps the single source tab for an item without versions', async () => {
        const wrapper = mountDialog({ content: '<p>Body</p>' })
        await flushPromises()

        expect(wrapper.get('[data-test="source-tab"]').text()).toBe('Quelle')
        expect(wrapper.findAll('[data-test="version-tab"]')).toHaveLength(0)
        expect(getNewsItemVersions).not.toHaveBeenCalled()
    })

    it('shows one tab per version, newest first, with the current one open', async () => {
        getNewsItemVersions.mockResolvedValue(versions)
        const wrapper = mountVersioned(versionedItem())

        // The current version needs no request: it is the item itself.
        expect(wrapper.get('[data-test="source-tab"]').text()).toBe('Fassung 2 (aktuell)')
        expect(activePane(wrapper).text()).toContain('Second revision')

        await flushPromises()
        // The versions belong to the news item (7), not to the aggregate around it (1).
        expect(getNewsItemVersions).toHaveBeenCalledWith(7)
        expect(wrapper.findAll('[data-test="version-tab"]').map((tab) => tab.text())).toEqual(['Fassung 1'])
        // An older version is only rendered once opened.
        expect(wrapper.text()).not.toContain('First revision')

        await wrapper.findComponent({ name: 'VTabs' }).vm.$emit('update:modelValue', 'version-11')
        await flushPromises()

        const pane = activePane(wrapper)
        expect(pane.text()).toContain('First revision')
        expect(pane.get('[data-test="superseded-notice"]').text()).toBe(`Am ${formatGerman('2026-09-10T08:00:00Z')} ersetzt`)
        expect(pane.text()).toContain('Example PSIRT')
    })

    it('shows only the current version when the history cannot be read', async () => {
        getNewsItemVersions.mockRejectedValue(new Error('403'))
        const wrapper = mountVersioned(versionedItem())
        await flushPromises()

        expect(wrapper.findAll('[data-test="version-tab"]')).toHaveLength(0)
        expect(activePane(wrapper).text()).toContain('Second revision')
    })

    it('reloads the versions when a newer revision arrives', async () => {
        getNewsItemVersions.mockResolvedValue(versions)
        const wrapper = mountVersioned(versionedItem())
        await flushPromises()
        expect(getNewsItemVersions).toHaveBeenCalledTimes(1)

        // The same data refreshed: nothing to load.
        await wrapper.setProps({ newsItem: versionedItem() })
        await flushPromises()
        expect(getNewsItemVersions).toHaveBeenCalledTimes(1)

        await wrapper.setProps({ newsItem: versionedItem({ hash: 'hash-3', version: '3', content: '<p>Third revision</p>' }) })
        await flushPromises()
        expect(getNewsItemVersions).toHaveBeenCalledTimes(2)
        expect(wrapper.get('[data-test="source-tab"]').text()).toBe('Fassung 3 (aktuell)')
    })
})
