import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { createI18n } from 'vue-i18n'
import { mountWithPlugins } from '../helpers/mount-helpers'
import ContentDataAssess from '@/components/assess/ContentDataAssess.vue'

const permissionState = vi.hoisted(() => ({ allowed: true }))
const assessApiMocks = vi.hoisted(() => ({ deleteNewsItem: vi.fn() }))

vi.mock('@/composables/useAuth', () => ({
    useAuth: () => ({ checkPermission: () => permissionState.allowed })
}))

vi.mock('@/api/assess', async () => {
    const actual = await vi.importActual('@/api/assess')
    return { ...actual, deleteNewsItem: assessApiMocks.deleteNewsItem }
})

/**
 * Acting on a card (star, like, read, ...) reloads the whole list from offset 0, and the
 * server echoes an SSE event back that reloads it again. If those loads apply each other's
 * pages, the list grows duplicate keys or collapses to a single page - and because the cards
 * live in a fixed-height scroller, the browser then clamps the scroll position and the list
 * visibly jumps somewhere else under the user's cursor.
 */

const mockRoute = {
    params: {
        groupId: 'all',
        scope: 'local'
    },
    query: {}
}

const makeItems = (count, offset = 0) =>
    Array.from({ length: count }, (_, i) => ({
        id: offset + i + 1,
        title: `Item ${offset + i + 1}`
    }))

/** Items the collector produced after the window was loaded - they sort above everything. */
const freshItems = (count) => Array.from({ length: count }, (_, i) => ({ id: 101 + i, title: `Fresh ${i + 1}` }))

const idsOf = (items) => items.map((item) => item.id)

const mockAssessStore = {
    getMultiSelect: false,
    getCurrentGroup: 'all',
    getNewsItems: { total_count: 0, items: [] },
    changeCurrentGroup: vi.fn(),
    loadNewsItemsByGroup: vi.fn(),
    voteNewsItemAggregate: vi.fn(),
    importantNewsItemAggregate: vi.fn(),
    readNewsItemAggregate: vi.fn(),
    saveNewsItemAggregate: vi.fn(),
    deleteNewsItemAggregate: vi.fn(),
    select: vi.fn(),
    deselect: vi.fn()
}

vi.mock('vue-router', () => ({
    useRoute: () => mockRoute
}))

vi.mock('@/stores/assess', () => ({
    useAssessStore: () => mockAssessStore
}))

const commonStubs = {
    CardAssess: { name: 'CardAssess', template: '<div class="card-assess-stub" />', props: ['card'] },
    CardCompact: { template: '<div class="card-compact-stub" />', props: ['card'] },
    NewsItemDetailDialog: true,
    ReportsListDialog: true,
    NewReportItem: true
}

const mountAssess = (i18n) =>
    mountWithPlugins(ContentDataAssess, {
        props: { analyze_selector: false },
        global: {
            i18n,
            stubs: commonStubs
        }
    })

const createPluralTestI18n = () =>
    createI18n({
        legacy: false,
        locale: 'de-DE',
        fallbackLocale: 'de-DE',
        messages: {
            'de-DE': {
                assess: {
                    no_items: 'Keine Elemente',
                    show_new_items: 'Keine neuen Elemente | {count} neues Element | {count} neue Elemente'
                },
                common: {
                    loading_more: 'Mehr laden',
                    end_of_list: 'Listenende'
                }
            }
        }
    })

/**
 * Where an item stands in the newest-first order, as a number that survives items being added
 * or removed around it: fresh items (ids over 100) are newer than all the others, and lower ids
 * are newer among each.
 */
const seqOf = (item) => (item.id > 100 ? 3000 - item.id : 1000 - item.id)
const cursorOf = (item) => `${seqOf(item)}|${item.id}`
const seqIn = (cursor) => Number(cursor.split('|')[0])

/**
 * Serve pages out of a real server-side list (newest first), the way the API does: by offset,
 * after/before an item's cursor, or the items named by `ids` - with the count of the whole list.
 */
const serveFrom = (serverItems) =>
    mockAssessStore.loadNewsItemsByGroup.mockImplementation(({ data }) => {
        let list = serverItems.map((item) => ({ ...item, cursor: cursorOf(item) }))
        if (data.ids) {
            const ids = String(data.ids).split(',').map(Number)
            return Promise.resolve({ data: { total_count: serverItems.length, items: list.filter((item) => ids.includes(item.id)) } })
        }
        if (data.after) list = list.filter((item) => seqOf(item) < seqIn(data.after))
        if (data.before) list = list.filter((item) => seqOf(item) > seqIn(data.before))
        const offset = data.offset ?? 0
        return Promise.resolve({ data: { total_count: list.length, items: list.slice(offset, offset + data.limit) } })
    })

/** The 20-card window the user is reading, with the card they just starred marked important. */
const windowWithStarredCard = () => makeItems(20).map((item) => (item.id === 16 ? { ...item, important: true } : item))

const starred = (items) => items.find((item) => item.id === 16)?.important === true

/** A response the test releases by hand, to hold a load in flight. */
const deferredPage = (items, total_count = 60) => {
    let release
    const promise = new Promise((resolve) => {
        release = () => resolve({ data: { total_count, items } })
    })
    return { promise, release }
}

describe('ContentDataAssess list reloads', () => {
    beforeEach(() => {
        vi.clearAllMocks()
        permissionState.allowed = true
        assessApiMocks.deleteNewsItem.mockResolvedValue({})

        mockRoute.params.groupId = 'all'
        // The old code read the list off this shared store ref after awaiting, rather than off
        // the response it got back - which is how concurrent loads applied each other's pages.
        mockAssessStore.getNewsItems = { total_count: 60, items: makeItems(20) }
        serveFrom(makeItems(60))
    })

    afterEach(() => {
        vi.restoreAllMocks()
    })

    it('leaves the rendered cards in the same order across a refresh', async () => {
        const wrapper = mountAssess()

        try {
            await flushPromises()
            const before = wrapper.findAll('.card-assess-stub').length

            serveFrom([...freshItems(2), ...makeItems(60)])
            await wrapper.vm.refreshData()
            await flushPromises()

            expect(idsOf(wrapper.vm.news_items_data)).toEqual(idsOf(makeItems(20)))
            expect(wrapper.findAll('.card-assess-stub')).toHaveLength(before)
        } finally {
            wrapper.unmount()
        }
    })

    it('re-reads the cards on screen by id, and asks only for what is newer than the window', async () => {
        const wrapper = mountAssess()

        try {
            await flushPromises()
            mockAssessStore.loadNewsItemsByGroup.mockClear()

            await wrapper.vm.refreshData()
            await flushPromises()

            const queries = mockAssessStore.loadNewsItemsByGroup.mock.calls.map(([{ data }]) => data)
            expect(queries).toHaveLength(2)
            expect(queries[0].ids).toBe(idsOf(makeItems(20)).join(','))
            expect(queries[1].before).toBe(cursorOf({ id: 1 }))
        } finally {
            wrapper.unmount()
        }
    })

    it('deletes only child items that carry modify access', async () => {
        const wrapper = mountAssess()

        try {
            await flushPromises()
            const card = wrapper.findComponent({ name: 'CardAssess' })

            card.vm.$emit('delete-item', { id: 41, entityType: 'news_item', modify: false })
            await flushPromises()
            expect(assessApiMocks.deleteNewsItem).not.toHaveBeenCalled()

            card.vm.$emit('delete-item', { id: 42, entityType: 'news_item', modify: true })
            await flushPromises()
            expect(assessApiMocks.deleteNewsItem).toHaveBeenCalledOnce()
            expect(assessApiMocks.deleteNewsItem).toHaveBeenCalledWith('all', 42)
        } finally {
            wrapper.unmount()
        }
    })

    it('appends the next page when scrolling, and keeps it across a refresh', async () => {
        const wrapper = mountAssess()

        try {
            await flushPromises()
            expect(idsOf(wrapper.vm.news_items_data)).toEqual(idsOf(makeItems(20)))

            await wrapper.vm.updateData(true, false)
            await flushPromises()
            expect(idsOf(wrapper.vm.news_items_data)).toEqual(idsOf(makeItems(40)))

            // Clicking a card refreshes everything the user has scrolled through, not just the
            // first page - collapsing 40 cards back to 20 would clamp the scroller.
            await wrapper.vm.refreshData()
            await flushPromises()
            expect(idsOf(wrapper.vm.news_items_data)).toEqual(idsOf(makeItems(40)))
        } finally {
            wrapper.unmount()
        }
    })

    it('does not concat an in-flight appended page onto a list that was refreshed underneath it', async () => {
        const wrapper = mountAssess()

        try {
            await flushPromises()

            // The user scrolls (append of page 2)...
            const appendPage = deferredPage(makeItems(20, 20))
            mockAssessStore.loadNewsItemsByGroup.mockReturnValueOnce(appendPage.promise)
            const append = wrapper.vm.updateData(true, false)

            // ...and clicks a star before it lands, which refreshes the list.
            await wrapper.vm.refreshData()
            appendPage.release()
            await append
            await flushPromises()

            const ids = idsOf(wrapper.vm.news_items_data)
            expect(ids).toEqual(idsOf(makeItems(20)))
            expect(new Set(ids).size).toBe(ids.length)
        } finally {
            wrapper.unmount()
        }
    })

    it('drops a superseded refresh instead of applying its stale page', async () => {
        const wrapper = mountAssess()

        try {
            await flushPromises()

            // A re-read that resolves late, from before the newer one - applying it would shrink
            // the list under the user.
            const stalePage = deferredPage(makeItems(5))
            mockAssessStore.loadNewsItemsByGroup.mockReturnValueOnce(stalePage.promise)

            const staleRefresh = wrapper.vm.refreshData()
            await wrapper.vm.refreshData()
            stalePage.release()
            await staleRefresh
            await flushPromises()

            expect(idsOf(wrapper.vm.news_items_data)).toEqual(idsOf(makeItems(20)))
        } finally {
            wrapper.unmount()
        }
    })

    it('holds newly collected items back instead of pushing the rendered list down', async () => {
        const wrapper = mountAssess()

        try {
            await flushPromises()

            // Two items were collected while the user was reading. DATE_DESC puts them on top, so
            // rendering them would push every card the user is looking at two cards down.
            serveFrom([...freshItems(2), ...makeItems(60)])

            await wrapper.vm.refreshData()
            await flushPromises()

            expect(idsOf(wrapper.vm.news_items_data)).toEqual(idsOf(makeItems(20)))
            expect(idsOf(wrapper.vm.pendingNewItems)).toEqual([101, 102])
            expect(wrapper.text()).toContain('Show 2 new items')
        } finally {
            wrapper.unmount()
        }
    })

    it('keeps a card in place when a new revision brings it to the top, and still holds new items back', async () => {
        const wrapper = mountAssess()

        try {
            await flushPromises()

            // Card 16 got a new revision: it is unread again and sorts first now, above an item
            // collected meanwhile. The old window anchored on it and showed everything below it.
            const revised = { id: 16, title: 'Item 16 (revised)' }
            const server = [revised, ...freshItems(1), ...makeItems(60).filter((item) => item.id !== 16)]
            mockAssessStore.loadNewsItemsByGroup.mockImplementation(({ data }) => {
                const list = server.map((item) => ({ ...item, cursor: item.id === 16 ? '5000|16' : cursorOf(item) }))
                if (data.ids) {
                    const ids = String(data.ids).split(',').map(Number)
                    return Promise.resolve({ data: { total_count: server.length, items: list.filter((item) => ids.includes(item.id)) } })
                }
                const newer = list.filter((item) => Number(item.cursor.split('|')[0]) > seqIn(data.before))
                return Promise.resolve({ data: { total_count: newer.length, items: newer.slice(0, data.limit) } })
            })

            await wrapper.vm.refreshData()
            await flushPromises()

            expect(idsOf(wrapper.vm.news_items_data)).toEqual(idsOf(makeItems(20)))
            expect(wrapper.vm.news_items_data[15].title).toBe('Item 16 (revised)')
            expect(idsOf(wrapper.vm.pendingNewItems)).toEqual([101])
            expect(wrapper.text()).toContain('Show 1 new item')
        } finally {
            wrapper.unmount()
        }
    })

    it('pluralizes and locale-formats the held-back item count without changing the banner interaction', async () => {
        const wrapper = mountAssess(createPluralTestI18n())

        try {
            await flushPromises()
            expect(wrapper.find('.new-items-banner__button').exists()).toBe(false)

            wrapper.vm.pendingNewItems = freshItems(1)
            await flushPromises()
            expect(wrapper.find('.new-items-banner__button').text()).toContain('1 neues Element')

            wrapper.vm.pendingNewItems = freshItems(1200)
            await flushPromises()
            const button = wrapper.find('.new-items-banner__button')
            expect(button.text()).toContain('1.200 neue Elemente')

            await button.trigger('click')
            await flushPromises()
            expect(wrapper.vm.pendingNewItems).toHaveLength(0)
            expect(wrapper.find('.new-items-banner__button').exists()).toBe(false)
        } finally {
            wrapper.unmount()
        }
    })

    /**
     * happy-dom does no layout, so stand in for it: 100px per card, in list order, in a scroller
     * whose top is at 0 - a card's top on screen is its position minus the scroll offset.
     */
    const layOut = (wrapper, scroller, getScrollTop) => {
        const CARD_HEIGHT = 100
        vi.spyOn(window, 'getComputedStyle').mockImplementation((el) => ({ overflowY: el === scroller ? 'auto' : 'visible' }))
        vi.spyOn(Element.prototype, 'getBoundingClientRect').mockImplementation(function () {
            if (this === scroller) return { top: 0, bottom: 800 }
            const index = Array.from(this.parentElement?.children ?? []).indexOf(this)
            const top = index * CARD_HEIGHT - getScrollTop()
            return { top, bottom: top + CARD_HEIGHT }
        })
        return CARD_HEIGHT
    }

    it('brings the held-back items in when the user scrolls back to the top, without moving the view', async () => {
        const wrapper = mountAssess()

        try {
            await flushPromises()

            const scroller = wrapper.vm.$el.parentElement
            let scrollTop = 0
            Object.defineProperty(scroller, 'scrollTop', {
                configurable: true,
                get: () => scrollTop,
                set: (value) => {
                    scrollTop = value
                }
            })
            const CARD_HEIGHT = layOut(wrapper, scroller, () => scrollTop)

            serveFrom([...freshItems(2), ...makeItems(60)])
            await wrapper.vm.refreshData()
            await flushPromises()

            // Reaching the top of the scroller is the cue to show what was collected meanwhile.
            wrapper.vm.onTopIntersect(true)
            await flushPromises()

            expect(idsOf(wrapper.vm.news_items_data)).toEqual([101, 102, ...idsOf(makeItems(20))])
            expect(wrapper.vm.pendingNewItems).toHaveLength(0)
            expect(wrapper.text()).not.toContain('Show new items')

            // The two new cards added 200px of scrollable space ABOVE the card the user was on, and
            // the scroll position followed it. Nothing on screen moved.
            expect(scrollTop).toBe(2 * CARD_HEIGHT)
        } finally {
            wrapper.unmount()
        }
    })

    it('does not move the scroll twice when the browser already anchors it', async () => {
        const wrapper = mountAssess()

        try {
            await flushPromises()

            // Chrome's scroll anchoring already follows content inserted above the viewport, but
            // only when the scroller is off the top - and Safari never does. Emulate a browser that
            // does: scrollTop tracks the cards added above all by itself.
            const scroller = wrapper.vm.$el.parentElement
            let base = 500
            let baseLength = 20
            const scrollTop = () => base + (wrapper.vm.news_items_data.length - baseLength) * 100
            Object.defineProperty(scroller, 'scrollTop', {
                configurable: true,
                get: scrollTop,
                set: (value) => {
                    base = value
                    baseLength = wrapper.vm.news_items_data.length
                }
            })
            layOut(wrapper, scroller, scrollTop)

            serveFrom([...freshItems(2), ...makeItems(60)])
            await wrapper.vm.refreshData()
            await flushPromises()

            wrapper.vm.onTopIntersect(true)
            await flushPromises()

            // The browser moved 500 -> 700 on its own. Adding the 200px again would land on 900 and
            // throw the list a screenful down the page, which is what the user sees as a jump.
            expect(scroller.scrollTop).toBe(700)
        } finally {
            wrapper.unmount()
        }
    })

    it('keeps the view still when a card above it leaves the list', async () => {
        const wrapper = mountAssess()

        try {
            await flushPromises()

            const scroller = wrapper.vm.$el.parentElement
            let scrollTop = 1000
            Object.defineProperty(scroller, 'scrollTop', {
                configurable: true,
                get: () => scrollTop,
                set: (value) => {
                    scrollTop = value
                }
            })
            layOut(wrapper, scroller, () => scrollTop)

            // Someone else marks card 3 read; under the unread filter it leaves the list. The user
            // reads card 11 at the top of the screen: it must stay there.
            serveFrom(makeItems(60).filter((item) => item.id !== 3))
            await wrapper.vm.refreshData()
            await flushPromises()

            expect(idsOf(wrapper.vm.news_items_data)).not.toContain(3)
            expect(scrollTop).toBe(900)
        } finally {
            wrapper.unmount()
        }
    })

    it('lets a card on screen fade out and fold away before it leaves, but not one above the view', async () => {
        const wrapper = mountAssess()

        try {
            await flushPromises()

            const scroller = wrapper.vm.$el.parentElement
            let scrollTop = 0
            Object.defineProperty(scroller, 'scrollTop', {
                configurable: true,
                get: () => scrollTop,
                set: (value) => {
                    scrollTop = value
                }
            })
            layOut(wrapper, scroller, () => scrollTop)
            const animated = []
            vi.spyOn(Element.prototype, 'animate').mockImplementation(function (keyframes) {
                animated.push({ card: this, keyframes })
                return { finished: Promise.resolve(), cancel: vi.fn() }
            })

            // The user marks card 3 read under "unread" (it is on screen): it leaves with an animation.
            serveFrom(makeItems(60).filter((item) => item.id !== 3))
            await wrapper.vm.refreshData()
            await flushPromises()

            expect(animated).toHaveLength(1)
            expect(animated[0].keyframes.at(-1)).toMatchObject({ opacity: 0, height: '0px' })
            expect(idsOf(wrapper.vm.news_items_data)).not.toContain(3)

            // Card 1 leaves while the user reads further down: no animation, the view stays put.
            animated.length = 0
            scrollTop = 1000
            serveFrom(makeItems(60).filter((item) => item.id !== 3 && item.id !== 1))
            await wrapper.vm.refreshData()
            await flushPromises()

            expect(animated).toHaveLength(0)
            expect(idsOf(wrapper.vm.news_items_data)).not.toContain(1)
        } finally {
            wrapper.unmount()
        }
    })

    it('refreshes the card the user acted on even when many items were collected meanwhile', async () => {
        const wrapper = mountAssess()

        try {
            await flushPromises()
            expect(starred(wrapper.vm.news_items_data)).toBe(false)

            // Twenty-five items were collected, then the user starred card 16. "The newest 20"
            // would not even reach the window; re-reading it by id always does.
            serveFrom([...freshItems(25), ...windowWithStarredCard(), ...makeItems(40, 20)])

            await wrapper.vm.refreshData()
            await flushPromises()

            expect(starred(wrapper.vm.news_items_data)).toBe(true)
            expect(idsOf(wrapper.vm.news_items_data)).toEqual(idsOf(makeItems(20)))
            expect(idsOf(wrapper.vm.pendingNewItems)).toHaveLength(25)
        } finally {
            wrapper.unmount()
        }
    })

    it('reloads from the top when more new items arrived than the pill fetched', async () => {
        const wrapper = mountAssess()

        try {
            await flushPromises()

            serveFrom([...freshItems(150), ...makeItems(60)])
            await wrapper.vm.refreshData()
            await flushPromises()

            expect(wrapper.vm.pendingNewItems).toHaveLength(100)
            expect(wrapper.text()).toContain('Show 150 new items')

            await wrapper.find('.new-items-banner__button').trigger('click')
            await flushPromises()

            expect(idsOf(wrapper.vm.news_items_data)).toEqual(idsOf(freshItems(20)))
            expect(wrapper.vm.pendingNewItems).toHaveLength(0)
        } finally {
            wrapper.unmount()
        }
    })

    it('pages on after the last card loaded, so items arriving above do not repeat cards', async () => {
        const wrapper = mountAssess()

        try {
            await flushPromises()

            // Two items collected would shift every offset by two and hand back cards 19 and 20.
            serveFrom([...freshItems(2), ...makeItems(60)])

            await wrapper.vm.updateData(true, false)
            await flushPromises()

            const lastCall = mockAssessStore.loadNewsItemsByGroup.mock.calls.at(-1)[0]
            expect(lastCall.data.after).toBe(cursorOf({ id: 20 }))
            expect(idsOf(wrapper.vm.news_items_data)).toEqual(idsOf(makeItems(40)))
        } finally {
            wrapper.unmount()
        }
    })

    it('pages on after the card it last loaded, even when that card was refreshed with a new place in the order', async () => {
        const wrapper = mountAssess()

        try {
            await flushPromises()

            // Card 20 (the last) gets a new revision: its cursor jumps to the top. Paging on from
            // its new cursor would hand back the whole list again.
            const server = makeItems(60)
            mockAssessStore.loadNewsItemsByGroup.mockImplementation(({ data }) => {
                const list = server.map((item) => ({ ...item, cursor: item.id === 20 ? '5000|20' : cursorOf(item) }))
                if (data.ids) {
                    const ids = String(data.ids).split(',').map(Number)
                    return Promise.resolve({ data: { total_count: 60, items: list.filter((item) => ids.includes(item.id)) } })
                }
                const key = (cursor) => seqIn(cursor)
                let rest = list
                if (data.after) rest = rest.filter((item) => key(item.cursor) < key(data.after))
                if (data.before) rest = rest.filter((item) => key(item.cursor) > key(data.before))
                return Promise.resolve({ data: { total_count: rest.length, items: rest.slice(0, data.limit) } })
            })
            await wrapper.vm.refreshData()
            await flushPromises()

            await wrapper.vm.updateData(true, false)
            await flushPromises()

            const lastCall = mockAssessStore.loadNewsItemsByGroup.mock.calls.at(-1)[0]
            expect(lastCall.data.after).toBe(cursorOf({ id: 20 }))
            const ids = idsOf(wrapper.vm.news_items_data)
            expect(new Set(ids).size).toBe(ids.length)
            expect(ids.slice(20)).toEqual(idsOf(makeItems(20, 20)))
        } finally {
            wrapper.unmount()
        }
    })

    it('drops an item that no longer matches the filter', async () => {
        const wrapper = mountAssess()

        try {
            await flushPromises()

            // The default filter is unread-only, so marking item 3 read takes it out of the list.
            serveFrom(makeItems(60).filter((item) => item.id !== 3))

            await wrapper.vm.refreshData()
            await flushPromises()

            const ids = idsOf(wrapper.vm.news_items_data)
            expect(ids).toEqual(idsOf(makeItems(20)).filter((id) => id !== 3))
            expect(wrapper.vm.total_count).toBe(59)
        } finally {
            wrapper.unmount()
        }
    })

    it('drops the last card of the list when it no longer matches the filter', async () => {
        const wrapper = mountAssess()

        try {
            serveFrom(makeItems(3))

            await wrapper.vm.updateData()
            await flushPromises()
            expect(idsOf(wrapper.vm.news_items_data)).toEqual([1, 2, 3])

            // Item 3 - the last card - is marked read: the whole remaining list is 2 items.
            serveFrom(makeItems(2))

            await wrapper.vm.refreshData()
            await flushPromises()

            expect(idsOf(wrapper.vm.news_items_data)).toEqual([1, 2])
        } finally {
            wrapper.unmount()
        }
    })

    it('empties the window when its last remaining card is acted on', async () => {
        const wrapper = mountAssess()

        try {
            serveFrom(makeItems(1))

            await wrapper.vm.updateData()
            await flushPromises()
            expect(idsOf(wrapper.vm.news_items_data)).toEqual([1])

            serveFrom([])

            await wrapper.vm.refreshData()
            await flushPromises()

            expect(wrapper.vm.news_items_data).toEqual([])
        } finally {
            wrapper.unmount()
        }
    })

    it('shows new items right away when the list was empty', async () => {
        const wrapper = mountAssess()

        try {
            serveFrom([])
            await wrapper.vm.updateData()
            await flushPromises()

            // Nothing on screen to keep still: the first items simply appear.
            serveFrom(freshItems(2))
            await wrapper.vm.refreshData()
            await flushPromises()

            expect(idsOf(wrapper.vm.news_items_data)).toEqual([101, 102])
            expect(wrapper.vm.pendingNewItems).toHaveLength(0)
        } finally {
            wrapper.unmount()
        }
    })
})
