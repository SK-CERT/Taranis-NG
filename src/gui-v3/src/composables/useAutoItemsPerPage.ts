import { nextTick, onMounted, onUnmounted, ref, type Ref } from 'vue'

/** A template ref pointing at either a plain element or a component whose root is one. */
type ElementSource = Ref<HTMLElement | { $el?: HTMLElement } | null | undefined>

type Options = {
    /** Never page below this, however short the viewport. */
    minRows?: number
    /** Used until a real row has been rendered and can be measured. */
    fallbackRowHeight?: number
    /** Breathing room kept below the table footer. */
    bottomGap?: number
}

const RESIZE_DEBOUNCE_MS = 150

/**
 * Size a v-data-table's page to whatever fits the viewport, so the list never spills into a
 * scrollbar and the reader never has to pick a page size.
 *
 * The app is a fixed-height flex layout (`height: 100vh` on the shell, see App.vue), so the
 * window itself does not scroll and the header row's position is stable: the space for rows is
 * simply what is left between the bottom of the header row and the bottom of the viewport.
 *
 * The result is recomputed from that geometry alone, so recomputing is idempotent - which is
 * what keeps the ResizeObserver below from chasing its own tail, since applying a new page size
 * resizes the very element it observes.
 *
 * Pair it with `v-model:items-per-page` and hide the footer's page-size select, which no longer
 * has anything to decide:
 *
 *     const table = ref(null)
 *     const { itemsPerPage, recalculate } = useAutoItemsPerPage(table)
 *     <v-data-table ref="table" v-model:items-per-page="itemsPerPage" ... />
 *
 * @param source Template ref for the table (the component ref works; its root element is used).
 * @param options Row-count floor, fallback row height and the gap kept below the footer.
 * @returns The reactive page size and a `recalculate` to call once rows have rendered.
 */
export function useAutoItemsPerPage(source: ElementSource, options: Options = {}) {
    const minRows = options.minRows ?? 5
    const fallbackRowHeight = options.fallbackRowHeight ?? 48
    const bottomGap = options.bottomGap ?? 16

    const itemsPerPage = ref(minRows)
    // Remembered so a page showing no rows (empty table, or a filter with no matches) keeps
    // sizing itself the way the populated table did.
    let lastRowHeight = fallbackRowHeight
    let resizeTimer: ReturnType<typeof setTimeout> | undefined
    let observer: ResizeObserver | undefined

    const rootElement = (): HTMLElement | null => {
        const value = source.value
        if (!value) return null
        return value instanceof HTMLElement ? value : (value.$el ?? null)
    }

    /**
     * Height of one body row. Vuetify's "no data" placeholder is a single full-width cell, so it
     * is skipped: measuring it would size the page from a row that is not a row.
     */
    const measureRowHeight = (root: HTMLElement): number => {
        for (const row of root.querySelectorAll<HTMLElement>('tbody tr')) {
            if (row.querySelectorAll('td').length > 1) {
                const height = row.getBoundingClientRect().height
                if (height > 0) {
                    lastRowHeight = height
                    return height
                }
            }
        }
        return lastRowHeight
    }

    const recalculate = (): void => {
        const root = rootElement()
        if (!root) return

        const header = root.querySelector('thead')
        const table = root.querySelector('table')
        const anchor = header ?? table
        if (!anchor) return

        const rowsTop = anchor.getBoundingClientRect().bottom
        const footer = root.querySelector<HTMLElement>('.v-data-table-footer')
        const available = window.innerHeight - rowsTop - (footer?.offsetHeight ?? 0) - bottomGap
        const rowHeight = measureRowHeight(root)
        if (rowHeight <= 0) return

        itemsPerPage.value = Math.max(minRows, Math.floor(available / rowHeight))
    }

    const scheduleRecalculate = (): void => {
        clearTimeout(resizeTimer)
        resizeTimer = setTimeout(recalculate, RESIZE_DEBOUNCE_MS)
    }

    onMounted(async () => {
        await nextTick()
        recalculate()
        window.addEventListener('resize', scheduleRecalculate)
        // Also catches layout changes the window never sees, such as the navigation drawer
        // opening, which move the table without resizing the viewport.
        const root = rootElement()
        if (root && typeof ResizeObserver !== 'undefined') {
            observer = new ResizeObserver(scheduleRecalculate)
            observer.observe(root)
        }
    })

    onUnmounted(() => {
        clearTimeout(resizeTimer)
        window.removeEventListener('resize', scheduleRecalculate)
        observer?.disconnect()
    })

    return { itemsPerPage, recalculate }
}
