<template>
    <v-container
        fluid
        class="pa-0"
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
                {{ pendingNewItemsMessage }}
            </v-btn>
        </div>

        <ContentSkeleton
            v-if="loading && news_items_data.length === 0"
            :compact="!!filter.compact_mode"
        />

        <!-- News Items Cards -->
        <div
            ref="listRef"
            class="card-list assess-list w-100"
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
                @card-items-reindex="handleCardItemsReindex"
                @selection-change="handleSelectionChange(news_item, $event)"
            />
        </div>

        <!-- Infinite Scroll Trigger -->
        <div
            v-intersect="onIntersect"
            class="mt-4 infinite-scroll-trigger"
        >
            <div
                v-if="loading && news_items_data.length > 0"
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
    import ContentSkeleton from '@/components/common/ContentSkeleton.vue'
    import CardCompact from '@/components/common/CardCompact.vue'
    import NewsItemDetailDialog from './NewsItemDetailDialog.vue'
    import NewReportItem from '@/components/analyze/NewReportItem.vue'
    import ReportsListDialog from './ReportsListDialog.vue'
    import { Action, type ActionKey } from '@/types/actions'
    import { useSseResync } from '@/composables/useSseResync'
    import { useAuth } from '@/composables/useAuth'
    import { useLocaleFormatters } from '@/composables/useLocaleFormatters'
    import Permissions from '@/services/permissions'
    import { isServerUnreachable } from '@/utils/deleteError'

    type NewsItem = {
        id: string | number
        entityType?: 'news_item' | 'news_item_aggregate'
        type?: string
        title?: string
        description?: string
        comments?: string
        modify?: boolean
        [key: string]: unknown
    }

    type ReportsMode = 'all' | 'completed' | 'in_progress'

    type ListState = {
        total_count: number
        items: unknown[]
    }

    type DetailActionPayload = {
        action: ActionKey
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

    const emit = defineEmits(['new-data-loaded', 'card-items-reindex', 'update-showing-count', 'show-detail'])

    const { t } = useI18n()
    const { formatNumber } = useLocaleFormatters()
    const { checkPermission } = useAuth()
    const route = useRoute()
    const assessStore = useAssessStore()
    const routeQuery = route.query ?? {}
    const searchQuery = Array.isArray(routeQuery['search']) ? routeQuery['search'][0] : routeQuery['search']

    const news_items_data = ref<NewsItem[]>([])

    /*
     * The list is a window onto the server's list that never moves under the user:
     * - a refresh (card action, server event) re-reads the cards on screen by id, in place, in
     *   the order they are shown - a card whose sort key changed (a new revision of an item, a
     *   vote under a relevance sort) stays where it is;
     * - paging further down continues after the last card loaded (a keyset cursor, not an
     *   offset, which items arriving or leaving above would shift);
     * - items collected meanwhile (newest first) are held back behind the "N new items" pill.
     *   They come in when the user scrolls back to the top, or clicks the pill.
     */
    const pendingNewItems = ref<NewsItem[]>([])
    // How many new items there are, also those not fetched yet (the pill loads at most PENDING_LIMIT).
    const pendingTotal = ref(0)
    const pendingNewItemsMessage = computed(() => {
        const count = Math.max(pendingTotal.value, pendingNewItems.value.length)
        return t('assess.show_new_items', { count: formatNumber(count) }, count)
    })

    // Where the window starts and where the next page continues, as of the last load: the cards
    // themselves get new cursors when they are refreshed, and following those would skip items.
    const windowTopCursor = ref<string | null>(null)
    const bottomCursor = ref<string | null>(null)
    const reachedEnd = ref(false)

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
    // New items fetched for the pill at once; more are counted, and the pill then reloads instead.
    const PENDING_LIMIT = 100
    // Ids one re-read may name (the server's limit).
    const MAX_IDS = 500

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
        search: searchQuery || '',
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

    /**
     * Only the compact card reports its checkbox up here - CardAssess keeps the selection in step
     * itself. Without this, ticking a card in compact mode changed nothing in the store: after
     * "select all", unchecking one left it selected and the group action still took it along.
     */
    const handleSelectionChange = (news_item: NewsItem, isSelected: boolean): void => {
        if (isSelected) {
            assessStore.select({ type: 'news_item_aggregate', id: news_item.id, item: news_item })
        } else {
            assessStore.deselect({ type: 'news_item_aggregate', id: news_item.id })
        }
    }

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
        if (isIntersecting && news_items_data_loaded.value && activeLoads.value === 0 && !reachedEnd.value) {
            // Debounce: only trigger if enough time has passed since last trigger
            const now = Date.now()
            if (now - lastIntersectTime.value >= INTERSECT_DEBOUNCE_MS) {
                lastIntersectTime.value = now
                loadData('append')
            }
        }
    }

    const showDetail = (news_item: NewsItem): void => {
        emit('show-detail', news_item)
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
        notify({ type: 'error', loc: isServerUnreachable(error) ? 'error.server_unreachable' : loc })
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
    const applyItemAction = async (action: ActionKey, item: NewsItem, group_id: string): Promise<boolean> => {
        const isChildNewsItem = item.entityType === 'news_item'
        const mutatingActions: readonly ActionKey[] = [Action.LIKE, Action.DISLIKE, Action.IMPORTANT, Action.READ, Action.UNGROUP]
        if (mutatingActions.includes(action) && (!checkPermission(Permissions.ASSESS_UPDATE) || (isChildNewsItem && item.modify !== true))) {
            return false
        }
        switch (action) {
            case Action.LIKE:
                await (isChildNewsItem ? voteNewsItem(group_id, item.id, 1) : assessStore.voteNewsItemAggregate(group_id, item.id, 1))
                break
            case Action.DISLIKE:
                await (isChildNewsItem ? voteNewsItem(group_id, item.id, -1) : assessStore.voteNewsItemAggregate(group_id, item.id, -1))
                break
            case Action.IMPORTANT:
                await (isChildNewsItem ? importantNewsItem(group_id, item.id) : assessStore.importantNewsItemAggregate(group_id, item.id))
                break
            case Action.READ:
                await (isChildNewsItem ? readNewsItem(group_id, item.id) : assessStore.readNewsItemAggregate(group_id, item.id))
                break
            case Action.UNGROUP:
                await groupAction({
                    group: group_id,
                    action: Action.UNGROUP,
                    items: [{ type: isChildNewsItem ? 'ITEM' : 'AGGREGATE', id: item.id }]
                })
                break
            case Action.CREATE_REPORT:
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
        if (
            (action === Action.COMMENT || action === Action.UPDATE_AGGREGATE) &&
            (!checkPermission(Permissions.ASSESS_UPDATE) || (isChildNewsItem && newsItem.modify !== true))
        ) {
            return
        }
        const toolbarActions: readonly ActionKey[] = [Action.LIKE, Action.DISLIKE, Action.IMPORTANT, Action.READ, Action.UNGROUP]
        const isToolbarAction = toolbarActions.includes(action)
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
                case Action.COMMENT:
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
                case Action.UPDATE_AGGREGATE:
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
            if (selectedItem.value && action !== Action.DELETE) {
                const updatedItem = findUpdatedSelectedItem(selectedItem.value)
                if (updatedItem) {
                    selectedItem.value = updatedItem
                }
            }

            // The comment saves itself as the user types: a toast at every pause is noise, and
            // while one is shown it takes Escape away from the dialog.
            if (action !== Action.COMMENT) {
                notify({ type: 'success', loc: 'assess.item_updated' })
            }
        } catch (error) {
            notifyActionError(error, 'Error handling detail action:', 'assess.error_updating')
        } finally {
            if (isToolbarAction && requestId === detailActionRequestId.value) {
                detailActionPending.value = false
            }
        }
    }

    const handleDetailDelete = async (newsItem: NewsItem) => {
        const isChildNewsItem = newsItem.entityType === 'news_item'
        if (!checkPermission(Permissions.ASSESS_DELETE) || (isChildNewsItem && newsItem.modify !== true)) {
            return
        }
        try {
            const group_id = current_group_id.value || getNormalizedGroupId()
            if (isChildNewsItem) {
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

    const updateItem = async (news_item: NewsItem, action: ActionKey) => {
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

    const handleDelete = async (newsItem?: NewsItem): Promise<void> => {
        // Aggregate cards delete themselves before notifying us. Child cards hand us the item,
        // so perform that request here and repeat the permission/ACL check at the handler edge.
        if (newsItem?.entityType === 'news_item') {
            if (newsItem.modify !== true || !checkPermission(Permissions.ASSESS_DELETE)) {
                return
            }

            try {
                const groupId = current_group_id.value || getNormalizedGroupId()
                await deleteNewsItem(groupId, newsItem.id)
                notify({ type: 'success', loc: 'assess.item_deleted' })
            } catch (error) {
                notifyActionError(error, 'Error deleting item:', 'assess.error_deleting')
                return
            }
        }

        // Reload current view after successful deletion
        // The animation will trigger when the deleted item is missing from the new data
        await refreshData()
    }

    const updateFilter = (newFilter: Partial<FilterState>): void => {
        const oldFilter = filter.value
        const mergedFilter = { ...oldFilter, ...newFilter }
        const dataFilterChanged =
            oldFilter.search !== mergedFilter.search ||
            oldFilter.range !== mergedFilter.range ||
            oldFilter.read !== mergedFilter.read ||
            oldFilter.important !== mergedFilter.important ||
            oldFilter.relevant !== mergedFilter.relevant ||
            oldFilter.sort !== mergedFilter.sort

        filter.value = mergedFilter
        if (dataFilterChanged) {
            updateData(false, false)
        }
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

    /**
     * Change the list without moving what the user is looking at: the first card on screen that
     * stays is put back where it was. Measured after the change, so a browser that already
     * anchored the scroll by itself (Chrome, off the top of the scroller) is not corrected twice.
     */
    const keepingViewStill = async (keeps: (id: string) => boolean, change: () => void): Promise<void> => {
        const scroller = getScroller()
        const cards = Array.from(listRef.value?.children ?? []) as HTMLElement[]
        const ids = news_items_data.value.map((item) => String(item.id))
        const viewTop = scroller?.getBoundingClientRect().top ?? 0
        const anchorIndex = cards.findIndex((card, index) => keeps(ids[index] ?? '') && card.getBoundingClientRect().bottom > viewTop)
        const anchorId = anchorIndex >= 0 ? ids[anchorIndex] : undefined
        const anchorTop = anchorIndex >= 0 ? cards[anchorIndex]!.getBoundingClientRect().top : 0

        change()
        await nextTick()

        if (!scroller || anchorId === undefined) return
        const index = news_items_data.value.findIndex((item) => String(item.id) === anchorId)
        const card = (listRef.value?.children[index] as HTMLElement | undefined) ?? null
        if (!card) return
        const moved = card.getBoundingClientRect().top - anchorTop
        if (Math.abs(moved) > 1) {
            scroller.scrollTop += moved
        }
    }

    /** Whether new items can come in above the window: only the newest-first order puts them there. */
    const holdsNewItemsBack = (): boolean => filter.value.sort === 'DATE_DESC'

    /**
     * reset:   start a fresh window at the top (filter/route change).
     * reload:  re-read the whole window from the top, showing anything new (explicit refresh).
     * refresh: re-read it silently, holding new items back (card actions, server events).
     * append:  next page of older items (infinite scroll).
     */
    type LoadMode = 'reset' | 'reload' | 'refresh' | 'append'

    type PageQuery = { offset?: number; limit?: number; ids?: string; after?: string; before?: string }

    const loadData = async (mode: LoadMode): Promise<void> => {
        if (mode === 'append' && reachedEnd.value) {
            news_items_data_loaded.value = true
            return
        }
        // With nothing on screen there is nothing to keep still: load the top.
        if (mode === 'refresh' && news_items_data.value.length === 0) {
            mode = 'reload'
        }
        const silent = mode === 'refresh'
        if (mode === 'refresh' || mode === 'reload') {
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

        const fetchPage = async (query: PageQuery): Promise<{ total_count: number; items: NewsItem[] } | null> => {
            const response = await assessStore.loadNewsItemsByGroup({
                group_id: group,
                data: { filter: filter.value, offset: 0, limit: PAGE_SIZE, ...query }
            })

            // Read the page we asked for off the response: the store holds a single shared
            // list that a concurrent load (or another component) may already have replaced.
            //
            // And drop it if a newer load has superseded this one - applying it now would
            // resurrect a stale page and, if it is shorter than what is on screen, yank the
            // scroll position.
            if (requestId !== loadSequence.value || !response?.data) {
                return null
            }
            const items = Array.isArray(response.data.items) ? (response.data.items as NewsItem[]) : []
            return { total_count: response.data.total_count || 0, items }
        }

        const cursorOf = (item: NewsItem | undefined): string | null => (typeof item?.['cursor'] === 'string' ? item['cursor'] : null)

        try {
            if (mode === 'append') {
                // Continue after the last card loaded; without a cursor (an order the server cannot
                // page by key), by position, counting what is held back above the window.
                const offset = pendingTotal.value + news_items_data.value.length
                const query: PageQuery = bottomCursor.value ? { after: bottomCursor.value } : { offset }
                const page = await fetchPage(query)
                if (!page) return

                // A position can shift under us, so a page may repeat cards already shown.
                const shown = new Set([...news_items_data.value, ...pendingNewItems.value].map((item) => String(item.id)))
                news_items_data.value = news_items_data.value.concat(page.items.filter((item) => !shown.has(String(item.id))))
                // After a cursor the server counts what is left; by position, the whole list.
                reachedEnd.value = page.items.length >= page.total_count - (query.after ? 0 : offset)
                if (!query.after) {
                    total_count.value = page.total_count
                }
                bottomCursor.value = cursorOf(page.items.at(-1)) ?? bottomCursor.value
            } else if (mode === 'refresh') {
                // 1. The cards on screen, re-read by id (the answer counts the whole list).
                const rendered = news_items_data.value
                const fresh = new Map<string, NewsItem>()
                let listTotal = total_count.value
                for (let start = 0; start < rendered.length; start += MAX_IDS) {
                    const ids = rendered.slice(start, start + MAX_IDS).map((item) => String(item.id))
                    const page = await fetchPage({ ids: ids.join(','), limit: ids.length })
                    if (!page) return
                    page.items.forEach((item) => fresh.set(String(item.id), item))
                    listTotal = page.total_count
                }

                // 2. What was collected above the window since it was loaded.
                let pending = pendingNewItems.value
                let pendingCount = pendingTotal.value
                if (holdsNewItemsBack() && windowTopCursor.value) {
                    const page = await fetchPage({ before: windowTopCursor.value, limit: PENDING_LIMIT })
                    if (!page) return
                    // A card on screen can sort above the window too (a new revision of it).
                    const onScreen = page.items.filter((item) => fresh.has(String(item.id))).length
                    pending = page.items.filter((item) => !fresh.has(String(item.id)))
                    pendingCount = Math.max(page.total_count - onScreen, pending.length)
                }

                // 3. Refresh the cards in place; drop those that are gone (deleted, or no longer
                //    matching the filter, e.g. marked read under "unread").
                await keepingViewStill(
                    (id) => fresh.has(id),
                    () => {
                        news_items_data.value = rendered
                            .filter((item) => fresh.has(String(item.id)))
                            .map((item) => fresh.get(String(item.id))!)
                        pendingNewItems.value = pending
                        pendingTotal.value = pendingCount
                        total_count.value = listTotal
                    }
                )
            } else {
                // reset/reload: a fresh window at the top, nothing held back.
                const page = await fetchPage({ offset: 0, limit: PAGE_SIZE })
                if (!page) return
                news_items_data.value = page.items
                pendingNewItems.value = []
                pendingTotal.value = 0
                windowTopCursor.value = cursorOf(page.items[0])
                bottomCursor.value = cursorOf(page.items.at(-1))
                reachedEnd.value = page.items.length >= page.total_count
                total_count.value = page.total_count
            }

            emit('new-data-loaded', total_count.value)
            emit('update-showing-count', news_items_data.value.length)
            emit('card-items-reindex', mode)
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
    useSseResync(refreshData)

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
        // More arrived than the pill fetched: the gap between them and the window is unknown.
        if (pendingTotal.value > pendingNewItems.value.length) {
            await loadData('reload')
            return
        }

        const pending = pendingNewItems.value
        const shown = new Set(news_items_data.value.map((item) => String(item.id)))
        await keepingViewStill(
            (id) => shown.has(id),
            () => {
                news_items_data.value = pending.filter((item) => !shown.has(String(item.id))).concat(news_items_data.value)
                windowTopCursor.value = typeof pending[0]?.['cursor'] === 'string' ? pending[0]['cursor'] : windowTopCursor.value
                pendingNewItems.value = []
                pendingTotal.value = 0
            }
        )

        emit('update-showing-count', news_items_data.value.length)
        emit('card-items-reindex', 'append')
    }

    async function handleCardItemsReindex(mode: string): Promise<void> {
        emit('card-items-reindex', mode)
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
        updateData,
        closeDetailDialog: () => {
            detailDialog.value = false
        }
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
