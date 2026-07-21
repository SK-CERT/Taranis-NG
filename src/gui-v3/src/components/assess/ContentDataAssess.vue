<template>
    <v-container
        fluid
        class="pa-2"
    >
        <!-- Scrolling back up to the top brings in whatever was collected in the meantime. -->
        <div v-intersect="onTopIntersect" />

        <!-- Items collected while the user is reading are held back, so they cannot push the
             list around. The pill floats over the first card: giving it layout space of its
             own would shift the cards down the moment it appeared. -->
        <div class="new-items-banner">
            <v-btn
                v-if="pendingNewItems.length > 0"
                class="new-items-banner__button"
                size="small"
                color="primary"
                variant="flat"
                @click="showPendingNewItems"
            >
                <v-icon start>
                    {{ ICONS.ARROW_UP }}
                </v-icon>
                {{ t('assess.show_new_items', { count: pendingNewItems.length }) }}
            </v-btn>
        </div>

        <!-- News Items Cards -->
        <div
            ref="listRef"
            class="card-list"
        >
            <TransitionGroup
                name="card-list"
                :move-class="moveClass"
                tag="div"
                class="w-100"
            >
                <component
                    :is="currentCard"
                    v-for="news_item in news_items_data"
                    :key="news_item.id"
                    :card="news_item"
                    :analyze-selector="analyze_selector"
                    :multi-select-active="multiSelectActive"
                    :preselected="isPreselected(news_item.id)"
                    :hide-reviews="filter.hide_reviews"
                    :hide-source-links="filter.hide_source_links"
                    :highlight-wordlist="filter.highlight_wordlist"
                    @show-detail="showDetail"
                    @show-reports-for-item="showReportsForItem"
                    @update-item="updateItem"
                    @delete-item="handleDelete"
                />
            </TransitionGroup>
        </div>

        <!-- Infinite Scroll Trigger -->
        <div
            v-intersect="onIntersect"
            class="mt-4 infinite-scroll-trigger"
        >
            <div
                v-if="loading"
                class="text-center text-grey"
            >
                <v-progress-circular
                    indeterminate
                    size="small"
                />
                <p class="text-caption mt-2">
                    {{ t('common.loading_more') }}
                </p>
            </div>
            <div
                v-else-if="news_items_data.length > 0"
                class="text-caption text-grey"
            >
                {{ t('common.end_of_list') }}
            </div>
        </div>

        <!-- Empty State -->
        <v-row
            v-if="!loading && news_items_data.length === 0"
            justify="center"
            class="my-8"
        >
            <v-col
                cols="12"
                md="6"
                class="text-center"
            >
                <v-icon
                    size="64"
                    color="grey"
                >
                    {{ ICONS.NEWSPAPER_VARIANT_OUTLINE }}
                </v-icon>
                <p class="text-h6 text-grey mt-4">
                    {{ t('assess.no_items') }}
                </p>
            </v-col>
        </v-row>

        <!-- News Item Detail Dialog -->
        <NewsItemDetailDialog
            v-model="detailDialog"
            :news-item="selectedItem"
            :actions-disabled="detailActionPending"
            :multi-select-active="multiSelectActive"
            @action="handleDetailAction"
            @delete="handleDetailDelete"
        />

        <!-- Reports List Dialog -->
        <ReportsListDialog
            ref="reportsListDialogRef"
            @view-report-detail="handleViewReportDetail"
        />

        <!-- Report Item Detail Modal (opened from ReportsListDialog) -->
        <NewReportItem
            ref="reportItemModalRef"
            :show-button="false"
        />
    </v-container>
</template>

<script setup lang="ts">
    import type { AxiosError } from 'axios'
    import { ref, onMounted, onUnmounted, watch, computed, nextTick } from 'vue'
    import { useI18n } from 'vue-i18n'
    import { useRoute } from 'vue-router'
    import { ICONS } from '@/config/ui-constants'
    import { deleteNewsItem, groupAction, importantNewsItem, readNewsItem, voteNewsItem } from '@/api/assess'
    import { useAssessStore } from '@/stores/assess'
    import CardAssess from './CardAssess.vue'
    import CardCompact from '@/components/common/CardCompact.vue'
    import NewsItemDetailDialog from './NewsItemDetailDialog.vue'
    import NewReportItem from '@/components/analyze/NewReportItem.vue'
    import ReportsListDialog from './ReportsListDialog.vue'

    type NewsItem = {
        id: string | number
        entityType?: 'news_item' | 'news_item_aggregate'
        type?: string
        title?: string
        description?: string
        comments?: string
        [key: string]: unknown
    }

    type ReportsMode = 'all' | 'completed' | 'in_progress'

    type ListState = {
        total_count: number
        items: unknown[]
    }

    type DetailActionPayload = {
        action: string
        newsItem: NewsItem
        comment?: string
        title?: string
        description?: string
    }

    type FilterState = {
        search: string
        range: string
        read: boolean | string
        important: boolean | string
        relevant: boolean | string
        sort: string
        hide_reviews: boolean
        hide_source_links: boolean
        highlight_wordlist: boolean
        compact_mode?: boolean
    }

    const props = withDefaults(
        defineProps<{
            analyze_selector?: boolean
            selection?: Array<{ id: string | number }>
        }>(),
        {
            analyze_selector: false,
            selection: () => []
        }
    )

    const emit = defineEmits(['new-data-loaded', 'card-items-reindex', 'update-showing-count'])

    const { t } = useI18n()
    const route = useRoute()
    const assessStore = useAssessStore()

    const news_items_data = ref<NewsItem[]>([])

    // Items the collector produced since the user last looked at the top of the list. They are
    // deliberately NOT rendered: the feed is sorted DATE_DESC, so injecting them would push
    // every card the user is reading down the viewport. They come in when the user scrolls
    // back to the top, or clicks the pill - so the rendered list stays a stable window.
    const pendingNewItems = ref<NewsItem[]>([])

    // Empty means the shared .card-list-move FLIP animation (BaseCard.vue), which slides a card
    // from where it was to where it now is - the gap closing when an item leaves the list. It is
    // swapped for a no-op class while held-back items are prepended; see mergePendingNewItems().
    const NO_MOVE_CLASS = 'card-list-no-move'
    const moveClass = ref('')

    // Where our window starts in the server's list. Everything held back sits above it.
    const windowOffset = computed(() => pendingNewItems.value.length)
    const loadedCount = computed(() => windowOffset.value + news_items_data.value.length)

    const total_count = ref(0)
    const news_items_data_loaded = ref(false)
    const detailDialog = ref(false)
    const selectedItem = ref<NewsItem | null>(null)
    const detailActionPending = ref(false)
    const listRef = ref<HTMLElement | null>(null)
    const reportsListDialogRef = ref<{ open: (card: NewsItem, mode: ReportsMode) => void } | null>(null)
    const reportItemModalRef = ref<{ openDialog: (items: NewsItem[]) => void; showDetail: (report: unknown) => void } | null>(null)
    const current_group_id = ref('')
    const detailActionRequestId = ref(0)
    const lastIntersectTime = ref(0)
    const INTERSECT_DEBOUNCE_MS = 500
    const PAGE_SIZE = 20

    // How many times a refresh may ask for a wider page to reach past freshly collected items.
    // Each attempt at least doubles the reach, so this covers a very large collector batch.
    const REFRESH_WIDEN_ATTEMPTS = 4

    // Loads that replace the list under the user (item actions, server events) run silently:
    // toggling the spinners would change the page height and move the scroll position.
    const visibleLoads = ref(0)
    const activeLoads = ref(0)
    const loadSequence = ref(0)
    const loading = computed(() => visibleLoads.value > 0)

    // The server echoes an SSE event back for our own updates, and fires one per collector
    // run. Coalesce those refreshes, and skip the echo of a refresh we just did ourselves.
    const SSE_REFRESH_COALESCE_MS = 400
    const SELF_REFRESH_ECHO_MS = 1000
    let sseRefreshTimer: ReturnType<typeof setTimeout> | undefined
    let lastSelfRefresh = 0
    const filter = ref<FilterState>({
        search: '',
        range: 'ALL',
        read: false,
        important: 'ALL',
        relevant: 'ALL',
        sort: 'DATE_DESC',
        hide_reviews: false,
        hide_source_links: false,
        highlight_wordlist: false
    })

    const currentCard = computed(() => {
        return filter.value.compact_mode ? CardCompact : CardAssess
    })

    const multiSelectActive = computed(() => assessStore.getMultiSelect)

    const isPreselected = (item_id: string | number): boolean => props.selection.some((item) => item.id === item_id)

    const getNormalizedGroupId = (): string => {
        const routeGroupId = route.params['groupId']
        if (typeof routeGroupId === 'string') {
            return routeGroupId
        }
        if (Array.isArray(routeGroupId)) {
            return routeGroupId[0] || 'all'
        }
        return 'all'
    }

    const onIntersect = (isIntersecting: boolean): void => {
        // Gate on activeLoads, not on the spinner: appending on top of an in-flight reload
        // mixes two different pages of the same list together.
        if (isIntersecting && news_items_data_loaded.value && activeLoads.value === 0 && loadedCount.value < total_count.value) {
            // Debounce: only trigger if enough time has passed since last trigger
            const now = Date.now()
            if (now - lastIntersectTime.value >= INTERSECT_DEBOUNCE_MS) {
                lastIntersectTime.value = now
                loadData('append')
            }
        }
    }

    const showDetail = (news_item: NewsItem): void => {
        selectedItem.value = news_item
        detailDialog.value = true
    }

    const normalizeId = (id: string | number | undefined): string => String(id ?? '')

    const toDetailNewsItem = (news_item: NewsItem): NewsItem => {
        if (news_item.entityType === 'news_item') {
            const nestedData = (news_item['news_item_data'] as Record<string, unknown> | undefined) || {}

            return {
                ...news_item,
                entityType: 'news_item',
                title: (nestedData['title'] as string) || (news_item['title'] as string) || '',
                description: (nestedData['review'] as string) || (news_item['description'] as string) || '',
                comments: (news_item['comments'] as string) || '',
                created: (nestedData['collected'] as string) || (news_item['created'] as string) || '',
                read: Boolean(news_item['read']),
                important: Boolean(news_item['important']),
                likes: Number(news_item['likes'] || 0),
                dislikes: Number(news_item['dislikes'] || 0),
                me_like: Boolean(news_item['me_like']),
                me_dislike: Boolean(news_item['me_dislike']),
                link: (nestedData['link'] as string) || '',
                news_items: [news_item]
            }
        }

        return news_item
    }

    const findTopLevelById = (id: string): NewsItem | null => {
        const match = news_items_data.value.find((item) => normalizeId(item.id) === id)
        return match ? toDetailNewsItem(match) : null
    }

    const findNestedById = (id: string): NewsItem | null => {
        for (const aggregate of news_items_data.value) {
            const nestedItems = Array.isArray(aggregate['news_items']) ? (aggregate['news_items'] as NewsItem[]) : []
            const nestedMatch = nestedItems.find((item) => normalizeId(item.id) === id)
            if (nestedMatch) {
                return toDetailNewsItem({ ...nestedMatch, entityType: 'news_item' })
            }
        }

        return null
    }

    const findUpdatedSelectedItem = (currentItem: NewsItem): NewsItem | null => {
        const currentId = normalizeId(currentItem.id)

        // A child item dialog resolves from the nested items, an aggregate one from the top level.
        // Either way fall back to the other list, in case the entity type metadata is missing.
        if (currentItem.entityType === 'news_item') {
            return findNestedById(currentId) ?? findTopLevelById(currentId)
        }

        return findTopLevelById(currentId) ?? findNestedById(currentId)
    }

    const showReportsForItem = (card: NewsItem, mode: ReportsMode): void => {
        reportsListDialogRef.value?.open(card, mode)
    }

    const notify = (detail: { type: 'success' | 'error'; loc?: string; message?: string }): void => {
        window.dispatchEvent(new CustomEvent('notification', { detail }))
    }

    const isAggregateInUseError = (error: unknown): boolean => {
        const responseData = (error as AxiosError)?.response?.data
        const responseError =
            responseData && typeof responseData === 'object' && 'error' in responseData
                ? (responseData as { error?: string }).error
                : undefined

        return (
            responseData === 'aggregate_in_use' ||
            responseError === 'aggregate_in_use' ||
            (typeof responseData === 'string' && responseData.includes('aggregate_in_use'))
        )
    }

    /**
     * An aggregate the user tried to change may be locked by a report item, which the server
     * reports rather than a generic failure - it is the user's own doing, so no console noise.
     */
    const notifyActionError = (error: unknown, logMessage: string, loc: string): void => {
        if (isAggregateInUseError(error)) {
            notify({ type: 'error', message: t('error.aggregate_in_use') })
            return
        }

        console.error(logMessage, error)
        notify({ type: 'error', loc })
    }

    const handleViewReportDetail = (report: unknown): void => {
        // Open report in NewReportItem modal without navigation
        reportItemModalRef.value?.showDetail(report)
    }

    /**
     * The actions a card and the detail dialog can fire are the same, and each one only differs
     * in whether the target is a child news item or an aggregate. Returns false when the action
     * was handled on the spot and there is nothing to reload.
     */
    const applyItemAction = async (action: string, item: NewsItem, group_id: string): Promise<boolean> => {
        const isChildNewsItem = item.entityType === 'news_item'

        switch (action) {
            case 'like':
                await (isChildNewsItem ? voteNewsItem(group_id, item.id, 1) : assessStore.voteNewsItemAggregate(group_id, item.id, 1))
                break
            case 'dislike':
                await (isChildNewsItem ? voteNewsItem(group_id, item.id, -1) : assessStore.voteNewsItemAggregate(group_id, item.id, -1))
                break
            case 'important':
                await (isChildNewsItem ? importantNewsItem(group_id, item.id) : assessStore.importantNewsItemAggregate(group_id, item.id))
                break
            case 'read':
                await (isChildNewsItem ? readNewsItem(group_id, item.id) : assessStore.readNewsItemAggregate(group_id, item.id))
                break
            case 'ungroup':
                await groupAction({
                    group: group_id,
                    action: 'UNGROUP',
                    items: [{ type: isChildNewsItem ? 'ITEM' : 'AGGREGATE', id: item.id }]
                })
                break
            case 'create-report':
                reportItemModalRef.value?.openDialog([item])
                return false
        }

        // 'refresh' - and anything unrecognised - falls through to a plain reload.
        return true
    }

    const handleDetailAction = async (payload: DetailActionPayload) => {
        const { action, newsItem } = payload
        const group_id = current_group_id.value || getNormalizedGroupId()
        const isChildNewsItem = newsItem.entityType === 'news_item'
        const isToolbarAction = ['like', 'dislike', 'important', 'read', 'ungroup'].includes(action)

        if (isToolbarAction && detailActionPending.value) {
            return
        }

        const requestId = detailActionRequestId.value + 1
        detailActionRequestId.value = requestId

        if (isToolbarAction) {
            detailActionPending.value = true
        }

        try {
            // The two editing actions are the dialog's own; everything else is shared with the cards.
            switch (action) {
                case 'comment':
                    if (!isChildNewsItem) {
                        await assessStore.saveNewsItemAggregate(
                            group_id,
                            newsItem.id,
                            newsItem.title || '',
                            newsItem.description || '',
                            payload.comment || ''
                        )
                    }
                    break
                case 'update-aggregate':
                    if (!isChildNewsItem) {
                        await assessStore.saveNewsItemAggregate(
                            group_id,
                            newsItem.id,
                            payload.title || '',
                            payload.description || '',
                            newsItem.comments || ''
                        )
                    }
                    break
                default:
                    if (!(await applyItemAction(action, newsItem, group_id))) {
                        return
                    }
            }

            // Reload current view
            await refreshData()

            // Ignore stale completions from older requests.
            if (requestId !== detailActionRequestId.value) {
                return
            }

            // Update the selected item in the dialog to show fresh data with updated colors
            if (selectedItem.value && action !== 'delete') {
                const updatedItem = findUpdatedSelectedItem(selectedItem.value)
                if (updatedItem) {
                    selectedItem.value = updatedItem
                }
            }

            notify({ type: 'success', loc: 'assess.item_updated' })
        } catch (error) {
            notifyActionError(error, 'Error handling detail action:', 'assess.error_updating')
        } finally {
            if (isToolbarAction && requestId === detailActionRequestId.value) {
                detailActionPending.value = false
            }
        }
    }

    const handleDetailDelete = async (newsItem: NewsItem) => {
        try {
            const group_id = current_group_id.value || getNormalizedGroupId()
            if (newsItem.entityType === 'news_item') {
                await deleteNewsItem(group_id, newsItem.id)
            } else {
                await assessStore.deleteNewsItemAggregate(group_id, newsItem.id)
            }

            // Close dialog and reload
            detailDialog.value = false
            selectedItem.value = null
            await refreshData()

            notify({ type: 'success', loc: 'assess.item_deleted' })
        } catch (error) {
            notifyActionError(error, 'Error deleting item:', 'assess.error_deleting')
        }
    }

    const updateItem = async (news_item: NewsItem, action: string) => {
        try {
            const group_id = current_group_id.value || getNormalizedGroupId()
            if (!(await applyItemAction(action, news_item, group_id))) {
                return
            }

            // Reload current view
            await refreshData()

            notify({ type: 'success', loc: 'assess.item_updated' })
        } catch (error) {
            notifyActionError(error, 'Error updating item:', 'assess.error_updating')
        }
    }

    const handleDelete = async (): Promise<void> => {
        // Reload current view after successful deletion
        // The animation will trigger when the deleted item is missing from the new data
        await refreshData()
    }

    const updateFilter = (newFilter: Partial<FilterState>): void => {
        filter.value = { ...filter.value, ...newFilter }
        updateData(false, false)
    }

    const handleNewsItemsUpdated = (): void => {
        // Coalesce bursts (a collector run emits one event per batch) into a single reload.
        // Deliberately not a debounce: a steady stream of events would keep pushing the
        // timer back and the list would never refresh at all.
        if (sseRefreshTimer) {
            return
        }

        sseRefreshTimer = setTimeout(() => {
            sseRefreshTimer = undefined

            // The server echoes an SSE event back to us for our own updates, which we have
            // already reloaded for - refetching would be a second full reload per click.
            if (Date.now() - lastSelfRefresh < SELF_REFRESH_ECHO_MS) {
                return
            }

            refreshData()
        }, SSE_REFRESH_COALESCE_MS)
    }

    const getScroller = (): HTMLElement | null => {
        let el = listRef.value?.parentElement ?? null
        while (el) {
            if (/(auto|scroll)/.test(window.getComputedStyle(el).overflowY)) {
                return el
            }
            el = el.parentElement
        }
        return null
    }

    const sameId = (a: NewsItem, b: NewsItem): boolean => String(a.id) === String(b.id)

    /** Index of the first card in `page` that we are currently rendering, or -1. */
    const windowStartIn = (page: NewsItem[]): number =>
        page.findIndex((item) => news_items_data.value.some((current) => sameId(current, item)))

    /**
     * A refresh can only ask for "the newest N", because that is all the API offers. Items
     * collected in the meantime sit above the window and push its tail out of that page - and the
     * cards past the end would then keep their stale state, so the star the user just clicked
     * would not change colour. Ask for a wider page until it reaches the end of the window.
     */
    const widenUntilWindowIsCovered = async (
        page: ListState,
        limit: number,
        fetchPage: (limit: number) => Promise<ListState | null>
    ): Promise<ListState | null> => {
        let current: ListState | null = page
        let currentLimit = limit

        for (let attempt = 0; attempt < REFRESH_WIDEN_ATTEMPTS; attempt++) {
            const items = (current?.items ?? []) as NewsItem[]
            const rendered = news_items_data.value

            // The server ran out of items (or capped the page): a wider ask cannot return more.
            if (items.length < currentLimit) {
                return current
            }

            const start = windowStartIn(items)
            if (start >= 0 && items.length - start >= rendered.length) {
                return current
            }

            // Widen by exactly how far the window slipped when we can see it; when the page does
            // not reach the window at all, we cannot tell how many arrived, so double and look again.
            const widened = start >= 0 ? start + rendered.length : currentLimit * 2
            if (widened <= currentLimit) {
                return current
            }

            currentLimit = widened
            current = await fetchPage(currentLimit)
            if (!current) {
                return null
            }
        }

        return current
    }

    /**
     * Fold a fresh server page (always fetched from offset 0, newest first) into the rendered
     * window without moving it: everything above the window is held back, everything inside it
     * is refreshed in place. Returns the new window.
     *
     * `pageIsComplete` says the fetch covered the whole filtered list, so a rendered card the
     * page does not list is genuinely gone - marked read under the unread filter, deleted, or
     * filtered out - and must not be carried over. Without it, marking the last card read left
     * it on screen with its stale (unread) state.
     */
    const mergeRefreshedPage = (page: NewsItem[], pageIsComplete: boolean): NewsItem[] => {
        const rendered = news_items_data.value
        if (rendered.length === 0) {
            pendingNewItems.value = []
            return page
        }

        // Anchor on the first rendered card that still exists on the server. Anything the page
        // lists above it is newer than everything we render, i.e. freshly collected.
        const anchorIndex = windowStartIn(page)
        if (anchorIndex < 0) {
            if (pageIsComplete) {
                // Nothing we render is on the server any more: the whole window is gone.
                pendingNewItems.value = []
                return page
            }
            // The window has drifted out of the fetched range. Leave the screen alone rather
            // than guess - a filter or route change will reset it.
            return rendered
        }

        pendingNewItems.value = page.slice(0, anchorIndex)
        const refreshed = page.slice(anchorIndex)

        if (pageIsComplete) {
            return refreshed
        }

        // The page stopped short of our window (the API caps limit at 200, and held-back items
        // eat into the range). Keep the cards past that point instead of dropping them, which
        // would shorten the list and clamp the scroller.
        const last = refreshed[refreshed.length - 1]
        const cut = last ? rendered.findIndex((current) => sameId(current, last)) : -1
        return cut < 0 ? refreshed : refreshed.concat(rendered.slice(cut + 1))
    }

    /**
     * reset:   start a fresh window at the top (filter/route change).
     * reload:  re-read the whole window from the top, showing anything new (explicit refresh).
     * refresh: re-read it silently, holding new items back (card actions, server events).
     * append:  next page of older items (infinite scroll).
     */
    type LoadMode = 'reset' | 'reload' | 'refresh' | 'append'

    const loadData = async (mode: LoadMode): Promise<void> => {
        const silent = mode === 'refresh'

        let offset = 0
        let limit = PAGE_SIZE

        if (mode === 'append') {
            offset = loadedCount.value
            if (total_count.value > 0 && offset >= total_count.value) {
                news_items_data_loaded.value = true
                return
            }
        } else if (mode === 'reload' || mode === 'refresh') {
            // Cover the held-back items as well, or the page would stop short of our window.
            limit = Math.max(limit, loadedCount.value)
            lastSelfRefresh = Date.now()
        }

        // Get group from route or store
        let group: string
        if (props.analyze_selector) {
            group =
                typeof assessStore.getCurrentGroup === 'string' ? assessStore.getCurrentGroup : String(assessStore.getCurrentGroup || 'all')
        } else {
            // Get groupId from route params
            group = getNormalizedGroupId()
            assessStore.changeCurrentGroup(group)
        }
        current_group_id.value = group

        const requestId = ++loadSequence.value
        activeLoads.value++
        if (!silent) {
            visibleLoads.value++
            news_items_data_loaded.value = false
        }

        const fetchPage = async (pageLimit: number): Promise<ListState | null> => {
            const response = await assessStore.loadNewsItemsByGroup({
                group_id: group,
                data: {
                    filter: filter.value,
                    offset: offset,
                    limit: pageLimit
                }
            })

            // Read the page we asked for off the response: the store holds a single shared
            // list that a concurrent load (or another component) may already have replaced.
            //
            // And drop it if a newer load has superseded this one - applying it now would
            // resurrect a stale page and, if it is shorter than what is on screen, yank the
            // scroll position.
            return requestId === loadSequence.value ? (response?.data ?? null) : null
        }

        try {
            let page = await fetchPage(limit)
            if (!page) {
                return
            }

            if (mode === 'refresh') {
                page = await widenUntilWindowIsCovered(page, limit, fetchPage)
                if (!page) {
                    return
                }
            }

            const items = Array.isArray(page.items) ? (page.items as NewsItem[]) : []
            total_count.value = page.total_count || 0

            let nextItems: NewsItem[]
            if (mode === 'append') {
                // Items collected since the last refresh shift every offset down, so a page can
                // hand back cards we already show. Dropping them keeps the keys unique.
                const rendered = news_items_data.value
                nextItems = rendered.concat(items.filter((item) => !rendered.some((current) => sameId(current, item))))
            } else if (mode === 'refresh') {
                // The page holds the whole filtered list, so anything missing from it is gone.
                nextItems = mergeRefreshedPage(items, items.length >= total_count.value)
            } else {
                // reset/reload both start the window at the top, so nothing is held back.
                pendingNewItems.value = []
                nextItems = items
            }

            // Directly assign new data - Vue will detect removed items and animate them
            news_items_data.value = nextItems

            emit('new-data-loaded', total_count.value)
            emit('update-showing-count', news_items_data.value.length)
            emit('card-items-reindex')
        } catch (error) {
            console.error('Error loading news items:', error)
        } finally {
            activeLoads.value--
            if (!silent) {
                visibleLoads.value--
            }
            news_items_data_loaded.value = true
        }
    }

    /** Silent reload after a card action or a server event: the window must not move. */
    const refreshData = (): Promise<void> => loadData('refresh')

    /** Kept for the toolbar and the analyze selector, which drive this component by ref. */
    const updateData = (append = false, reload_all = false): Promise<void> => loadData(append ? 'append' : reload_all ? 'reload' : 'reset')

    /**
     * Put the held-back items on screen without moving what the user is reading: the cards keep
     * their place and the new ones simply add scrollable space above, to scroll up into.
     */
    const mergePendingNewItems = async (): Promise<void> => {
        if (pendingNewItems.value.length === 0) {
            return
        }

        const scroller = getScroller()
        const scrollBefore = scroller?.scrollTop ?? 0
        const heightBefore = scroller?.scrollHeight ?? 0

        // Prepending pushes every card down. A FLIP move would animate that as one long slide of
        // the whole list, and it measures positions before the scroll correction below, so the two
        // would each apply the same offset. Nothing may move for this one update.
        moveClass.value = NO_MOVE_CLASS
        news_items_data.value = pendingNewItems.value.concat(news_items_data.value)
        pendingNewItems.value = []

        await nextTick()
        if (scroller) {
            // Everything we added sits above the viewport, so the growth in scrollHeight is exactly
            // how far the content moved down, and following it leaves the view untouched.
            //
            // Chrome does that by itself (scroll anchoring) - but only off the top of the scroller,
            // and Safari never does it. So aim at the position rather than adding an offset: adding
            // one on top of Chrome's would double it and throw the list down the page.
            const target = scrollBefore + (scroller.scrollHeight - heightBefore)
            if (Math.abs(scroller.scrollTop - target) > 1) {
                scroller.scrollTop = target
            }
        }
        moveClass.value = ''

        emit('update-showing-count', news_items_data.value.length)
        emit('card-items-reindex')
    }

    /** The pill says "show me what is new", so it also takes the user there. */
    const showPendingNewItems = async (): Promise<void> => {
        await mergePendingNewItems()
        getScroller()?.scrollTo({ top: 0 })
    }

    const onTopIntersect = (isIntersecting: boolean): void => {
        if (isIntersecting && news_items_data_loaded.value) {
            mergePendingNewItems()
        }
    }

    // Watch route changes
    watch(
        () => route.params['groupId'],
        () => {
            updateData(false, false)
        }
    )

    // Initial load
    onMounted(() => {
        updateData(false, false)
        window.addEventListener('news-items-updated', handleNewsItemsUpdated)
    })

    onUnmounted(() => {
        clearTimeout(sseRefreshTimer)
        window.removeEventListener('news-items-updated', handleNewsItemsUpdated)
    })

    defineExpose({
        updateFilter,
        updateData
    })
</script>

<style scoped>
    /* A card leaving the list is positioned absolutely while it fades out (.card-list-leave-active
       in BaseCard.vue). Give it a containing block: against the viewport its width:100% overshoots
       the content column by the width of the nav drawer, and the page grows a horizontal scrollbar
       for as long as the animation runs. */
    .card-list {
        position: relative;
    }

    .infinite-scroll-trigger {
        min-height: 100px;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    .new-items-banner {
        position: sticky;
        top: 0;
        z-index: 5;
        display: flex;
        justify-content: center;
        /* No height of its own: the pill floats over the first card, so showing and hiding it
           cannot push the list up and down. */
        height: 0;
    }

    .new-items-banner__button {
        position: absolute;
        top: 4px;
    }
</style>

<style>
    /* Vue skips the whole FLIP pass when the move class carries no transition, so the cards do not
       animate to their new positions - see mergePendingNewItems(). Not scoped: the class lands on
       the card components' root elements. */
    .card-list-no-move {
        transition: none;
    }
</style>
