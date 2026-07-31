import { describe, it, expect, beforeEach, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { mountWithPlugins } from '../helpers/mount-helpers'
import ContentDataAssess from '@/components/assess/ContentDataAssess.vue'

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
    }
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
    CardAssess: { template: '<div class="card-assess-stub" />', props: ['card'] },
    CardCompact: { template: '<div class="card-compact-stub" />', props: ['card'] },
    NewsItemDetailDialog: true,
    ReportsListDialog: true,
    NewReportItem: true
}

const mountAssess = () =>
    mountWithPlugins(ContentDataAssess, {
        props: { analyze_selector: false },
        global: { stubs: commonStubs }
    })

/**
 * Serve pages out of a real server-side list, honouring offset/limit the way the API does. Newly
 * collected items go on the front, which is what shifts every offset underneath the client.
 */
const serveFrom = (serverItems) =>
    mockAssessStore.loadNewsItemsByGroup.mockImplementation(({ data }) =>
        Promise.resolve({
            data: {
                total_count: serverItems.length,
                items: serverItems.slice(data.offset, data.offset + data.limit)
            }
        })
    )

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

        mockRoute.params.groupId = 'all'
        // The old code read the list off this shared store ref after awaiting, rather than off
        // the response it got back - which is how concurrent loads applied each other's pages.
        mockAssessStore.getNewsItems = { total_count: 60, items: makeItems(20) }
        mockAssessStore.loadNewsItemsByGroup.mockImplementation(({ data }) =>
            Promise.resolve({
                data: {
                    total_count: 60,
                    items: makeItems(data.limit, data.offset)
                }
            })
        )
    })

    it('leaves the rendered cards in the same order across a refresh', async () => {
        const wrapper = mountAssess()

        try {
            await flushPromises()
            const before = wrapper.findAll('.card-assess-stub').length

            mockAssessStore.loadNewsItemsByGroup.mockResolvedValueOnce({
                data: {
                    total_count: 62,
                    items: [...freshItems(2), ...makeItems(20)]
                }
            })
            await wrapper.vm.refreshData()
            await flushPromises()

            // This is what makes the .card-list-move FLIP animation safe to keep: a refresh does
            // not move any card, so Vue measures zero displacement and animates nothing. The
            // animation then only plays when a card genuinely moves - the gap closing after one
            // is marked read - instead of sliding the whole list down the viewport.
            expect(idsOf(wrapper.vm.news_items_data)).toEqual(idsOf(makeItems(20)))
            expect(wrapper.findAll('.card-assess-stub')).toHaveLength(before)
        } finally {
            wrapper.unmount()
        }
    })

    it('appends the next page when scrolling, and keeps it across a reload', async () => {
        const wrapper = mountAssess()

        try {
            await flushPromises()
            expect(idsOf(wrapper.vm.news_items_data)).toEqual(idsOf(makeItems(20)))

            await wrapper.vm.updateData(true, false)
            await flushPromises()
            expect(idsOf(wrapper.vm.news_items_data)).toEqual(idsOf(makeItems(40)))

            // Clicking a card reloads everything the user has scrolled through, not just the
            // first page - collapsing 40 cards back to 20 would clamp the scroller.
            await wrapper.vm.refreshData()
            await flushPromises()
            expect(idsOf(wrapper.vm.news_items_data)).toEqual(idsOf(makeItems(40)))
        } finally {
            wrapper.unmount()
        }
    })

    it('does not concat an in-flight appended page onto a list that was reloaded underneath it', async () => {
        const wrapper = mountAssess()

        try {
            await flushPromises()

            // The user scrolls (append of page 2)...
            const appendPage = deferredPage(makeItems(20, 20))
            mockAssessStore.loadNewsItemsByGroup.mockReturnValueOnce(appendPage.promise)
            const append = wrapper.vm.updateData(true, false)

            // ...and clicks a star before it lands, which reloads the list from offset 0.
            await wrapper.vm.refreshData()
            appendPage.release()
            await append
            await flushPromises()

            // The superseded append must be dropped. Concatenating it would duplicate keys in
            // the TransitionGroup and thrash the rendered cards.
            const ids = idsOf(wrapper.vm.news_items_data)
            expect(ids).toEqual(idsOf(makeItems(20)))
            expect(new Set(ids).size).toBe(ids.length)
        } finally {
            wrapper.unmount()
        }
    })

    it('drops a superseded reload instead of applying its stale page', async () => {
        const wrapper = mountAssess()

        try {
            await flushPromises()

            // A reload that resolves late, carrying a page from before the newer one - applying
            // it would shrink the list back under the user.
            const stalePage = deferredPage(makeItems(5))
            mockAssessStore.loadNewsItemsByGroup.mockReturnValueOnce(stalePage.promise)

            const staleReload = wrapper.vm.refreshData()
            await wrapper.vm.refreshData()
            stalePage.release()
            await staleReload
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
            mockAssessStore.loadNewsItemsByGroup.mockResolvedValueOnce({
                data: {
                    total_count: 62,
                    items: [...freshItems(2), ...makeItems(20)]
                }
            })

            await wrapper.vm.refreshData()
            await flushPromises()

            expect(idsOf(wrapper.vm.news_items_data)).toEqual(idsOf(makeItems(20)))
            expect(idsOf(wrapper.vm.pendingNewItems)).toEqual([101, 102])
            expect(wrapper.text()).toContain('Show new items (2)')
        } finally {
            wrapper.unmount()
        }
    })

    it('brings the held-back items in when the user scrolls back to the top, without moving the view', async () => {
        const wrapper = mountAssess()

        try {
            await flushPromises()

            // happy-dom does no layout, so stand in for it: 100px per card, and the user has just
            // scrolled back up to the top of the window they were reading.
            const CARD_HEIGHT = 100
            const scroller = wrapper.vm.$el.parentElement
            let scrollTop = 0

            Object.defineProperty(scroller, 'scrollTop', {
                configurable: true,
                get: () => scrollTop,
                set: (value) => {
                    scrollTop = value
                }
            })
            Object.defineProperty(scroller, 'scrollHeight', {
                configurable: true,
                get: () => wrapper.vm.news_items_data.length * CARD_HEIGHT
            })
            vi.spyOn(window, 'getComputedStyle').mockImplementation((el) => ({ overflowY: el === scroller ? 'auto' : 'visible' }))

            mockAssessStore.loadNewsItemsByGroup.mockResolvedValueOnce({
                data: {
                    total_count: 62,
                    items: [...freshItems(2), ...makeItems(20)]
                }
            })
            await wrapper.vm.refreshData()
            await flushPromises()

            // Reaching the top of the scroller is the cue to show what was collected meanwhile.
            wrapper.vm.onTopIntersect(true)
            await flushPromises()

            expect(idsOf(wrapper.vm.news_items_data)).toEqual([101, 102, ...idsOf(makeItems(20))])
            expect(wrapper.vm.pendingNewItems).toHaveLength(0)
            expect(wrapper.text()).not.toContain('Show new items')

            // The two new cards added 200px of scrollable space ABOVE the card the user was on, and
            // the scroll position followed it. Nothing on screen moved; there is simply room to
            // scroll up into now. Leaving scrollTop at 0 would drag the list through the new items.
            expect(scrollTop).toBe(2 * CARD_HEIGHT)
        } finally {
            wrapper.unmount()
        }
    })

    it('refreshes the card the user acted on even when newly collected items push the window down the page', async () => {
        const wrapper = mountAssess()

        try {
            await flushPromises()
            expect(starred(wrapper.vm.news_items_data)).toBe(false)

            // Five items were collected, then the user starred card 16. Asking for "the newest 20"
            // now returns the 5 new ones plus cards 1-15: card 16 falls off the end of the page, so
            // it would keep its stale state and the star would not change colour - while the PUT
            // that starred it succeeded and reported "item updated".
            serveFrom([...freshItems(5), ...windowWithStarredCard(), ...makeItems(40, 20)])

            await wrapper.vm.refreshData()
            await flushPromises()

            expect(starred(wrapper.vm.news_items_data)).toBe(true)
            expect(idsOf(wrapper.vm.news_items_data)).toEqual(idsOf(makeItems(20)))
            expect(idsOf(wrapper.vm.pendingNewItems)).toHaveLength(5)
        } finally {
            wrapper.unmount()
        }
    })

    it('refreshes the window even when a collector batch is larger than the page', async () => {
        const wrapper = mountAssess()

        try {
            await flushPromises()

            // A batch bigger than the window: "the newest 20" is now entirely new items, so the
            // page does not reach a single card we render. Nothing would update at all, and the
            // held-back items would never be noticed either.
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

    it('does not append cards it is already showing when offsets have shifted', async () => {
        const wrapper = mountAssess()

        try {
            await flushPromises()

            // Two items collected shift every offset by two, so the next page hands back cards 19
            // and 20 - which are already on screen. Concatenating them would duplicate the keys.
            serveFrom([...freshItems(2), ...makeItems(60)])

            await wrapper.vm.updateData(true, false)
            await flushPromises()

            const ids = idsOf(wrapper.vm.news_items_data)
            expect(new Set(ids).size).toBe(ids.length)
            expect(ids.slice(0, 20)).toEqual(idsOf(makeItems(20)))
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
            const CARD_HEIGHT = 100
            const scroller = wrapper.vm.$el.parentElement
            let base = 500
            let baseLength = 20

            Object.defineProperty(scroller, 'scrollHeight', {
                configurable: true,
                get: () => wrapper.vm.news_items_data.length * CARD_HEIGHT
            })
            Object.defineProperty(scroller, 'scrollTop', {
                configurable: true,
                get: () => base + (wrapper.vm.news_items_data.length - baseLength) * CARD_HEIGHT,
                set: (value) => {
                    base = value
                    baseLength = wrapper.vm.news_items_data.length
                }
            })
            vi.spyOn(window, 'getComputedStyle').mockImplementation((el) => ({ overflowY: el === scroller ? 'auto' : 'visible' }))

            mockAssessStore.loadNewsItemsByGroup.mockResolvedValueOnce({
                data: {
                    total_count: 62,
                    items: [...freshItems(2), ...makeItems(20)]
                }
            })
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

    it('counts the held-back items when paging further down the list', async () => {
        const wrapper = mountAssess()

        try {
            await flushPromises()

            mockAssessStore.loadNewsItemsByGroup.mockResolvedValueOnce({
                data: {
                    total_count: 62,
                    items: [...freshItems(2), ...makeItems(20)]
                }
            })
            await wrapper.vm.refreshData()
            await flushPromises()

            // The window now starts at server offset 2, so the next page starts at 22 - asking
            // for offset 20 would hand back two items that are already on screen.
            await wrapper.vm.updateData(true, false)
            await flushPromises()

            const lastCall = mockAssessStore.loadNewsItemsByGroup.mock.calls.at(-1)[0]
            expect(lastCall.data.offset).toBe(22)

            const ids = idsOf(wrapper.vm.news_items_data)
            expect(new Set(ids).size).toBe(ids.length)
        } finally {
            wrapper.unmount()
        }
    })

    it('drops an item that no longer matches the filter, keeping the window full', async () => {
        const wrapper = mountAssess()

        try {
            await flushPromises()

            // The default filter is unread-only, so marking item 3 read takes it out of the list.
            // The window pulls item 21 in from behind rather than getting shorter, which would
            // shift the cards below and clamp the scroller.
            mockAssessStore.loadNewsItemsByGroup.mockResolvedValueOnce({
                data: {
                    total_count: 59,
                    items: makeItems(21).filter((item) => item.id !== 3)
                }
            })

            await wrapper.vm.refreshData()
            await flushPromises()

            const ids = idsOf(wrapper.vm.news_items_data)
            expect(ids).not.toContain(3)
            expect(ids).toHaveLength(20)
            expect(ids.at(-1)).toBe(21)
        } finally {
            wrapper.unmount()
        }
    })

    /**
     * There is nothing behind the last card to pull in, so the refreshed page ends one card
     * short of the window. That is indistinguishable from a page the API truncated - and the
     * tail-preserving branch used to re-append the very card the user had just read, which
     * left it on screen still showing its stale unread eye.
     */
    it('drops the last card of the list when it no longer matches the filter', async () => {
        const wrapper = mountAssess()

        try {
            mockAssessStore.loadNewsItemsByGroup.mockResolvedValue({
                data: { total_count: 3, items: makeItems(3) }
            })

            await wrapper.vm.updateData()
            await flushPromises()
            expect(idsOf(wrapper.vm.news_items_data)).toEqual([1, 2, 3])

            // Item 3 - the last card - is marked read: the whole remaining list is 2 items.
            mockAssessStore.loadNewsItemsByGroup.mockResolvedValue({
                data: { total_count: 2, items: makeItems(2) }
            })

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
            mockAssessStore.loadNewsItemsByGroup.mockResolvedValue({
                data: { total_count: 1, items: makeItems(1) }
            })

            await wrapper.vm.updateData()
            await flushPromises()
            expect(idsOf(wrapper.vm.news_items_data)).toEqual([1])

            // Nothing we render comes back, and the page proves it: the list really is empty.
            mockAssessStore.loadNewsItemsByGroup.mockResolvedValue({
                data: { total_count: 0, items: [] }
            })

            await wrapper.vm.refreshData()
            await flushPromises()

            expect(wrapper.vm.news_items_data).toEqual([])
        } finally {
            wrapper.unmount()
        }
    })
})
