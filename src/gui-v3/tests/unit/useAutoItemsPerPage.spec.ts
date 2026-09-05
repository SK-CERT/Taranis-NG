import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { defineComponent, h, nextTick, ref } from 'vue'
import { mount } from '@vue/test-utils'
import { useAutoItemsPerPage } from '@/composables/useAutoItemsPerPage'

/**
 * The table pages to whatever the viewport fits, so nobody has to pick a page size and the list
 * never spills into a scrollbar. Everything below turns on one sum: the space between the bottom
 * of the header row and the bottom of the window, divided by the height of a row.
 */

const HEADER_BOTTOM = 200
const FOOTER_HEIGHT = 60
const ROW_HEIGHT = 40

/** Build the slice of table markup the composable measures, with the geometry jsdom cannot supply. */
function buildTable({ rows = 3, rowHeight = ROW_HEIGHT, headerBottom = HEADER_BOTTOM, noDataRow = false } = {}) {
    const root = document.createElement('div')
    root.innerHTML = `
        <table>
            <thead><tr><th>a</th><th>b</th></tr></thead>
            <tbody></tbody>
        </table>
        <div class="v-data-table-footer"></div>
    `
    const head = root.querySelector('thead') as HTMLElement
    head.getBoundingClientRect = () => ({ bottom: headerBottom, top: headerBottom - 40 }) as DOMRect

    const body = root.querySelector('tbody') as HTMLElement
    const cells = noDataRow ? 1 : 2
    for (let index = 0; index < rows; index += 1) {
        const row = document.createElement('tr')
        row.innerHTML = '<td></td>'.repeat(cells)
        row.getBoundingClientRect = () => ({ height: rowHeight }) as DOMRect
        body.appendChild(row)
    }

    const footer = root.querySelector('.v-data-table-footer') as HTMLElement
    Object.defineProperty(footer, 'offsetHeight', { value: FOOTER_HEIGHT, configurable: true })

    document.body.appendChild(root)
    return root
}

/** Mount a throwaway component so the composable's lifecycle hooks run. */
function withTable(root: HTMLElement, options?: Parameters<typeof useAutoItemsPerPage>[1]) {
    const api: { itemsPerPage?: { value: number }; recalculate?: () => void } = {}
    const wrapper = mount(
        defineComponent({
            setup() {
                const source = ref<HTMLElement | null>(root)
                const { itemsPerPage, recalculate } = useAutoItemsPerPage(source, options)
                api.itemsPerPage = itemsPerPage
                api.recalculate = recalculate
                return () => h('div')
            }
        })
    )
    return { wrapper, api }
}

describe('useAutoItemsPerPage', () => {
    beforeEach(() => {
        window.innerHeight = 1000
        vi.useFakeTimers()
    })

    afterEach(() => {
        vi.useRealTimers()
        document.body.innerHTML = ''
    })

    it('fills the space left between the header row and the bottom of the window', async () => {
        const { wrapper, api } = withTable(buildTable())
        await nextTick()

        // (1000 - 200 header - 60 footer - 16 gap) / 40 = 18
        expect(api.itemsPerPage?.value).toBe(18)
        wrapper.unmount()
    })

    it('gives a shorter window fewer rows', async () => {
        window.innerHeight = 600
        const { wrapper, api } = withTable(buildTable())
        await nextTick()

        // (600 - 200 - 60 - 16) / 40 = 8
        expect(api.itemsPerPage?.value).toBe(8)
        wrapper.unmount()
    })

    it('keeps a usable page on a window too short to fit one', async () => {
        window.innerHeight = 260
        const { wrapper, api } = withTable(buildTable())
        await nextTick()

        expect(api.itemsPerPage?.value).toBe(5)
        wrapper.unmount()
    })

    it('honours a caller-supplied floor', async () => {
        window.innerHeight = 260
        const { wrapper, api } = withTable(buildTable(), { minRows: 12 })
        await nextTick()

        expect(api.itemsPerPage?.value).toBe(12)
        wrapper.unmount()
    })

    it('measures the row height rather than assuming it', async () => {
        const { wrapper, api } = withTable(buildTable({ rowHeight: 80 }))
        await nextTick()

        // Same space, rows twice as tall: half as many fit.
        expect(api.itemsPerPage?.value).toBe(9)
        wrapper.unmount()
    })

    it('ignores the no-data placeholder, which is not a row', async () => {
        // A single full-width cell is Vuetify's empty state; measuring it would size the page
        // from a row that does not exist, so the fallback height stands in.
        const { wrapper, api } = withTable(buildTable({ rows: 1, rowHeight: 300, noDataRow: true }))
        await nextTick()

        // (1000 - 200 - 60 - 16) / 48 fallback = 15
        expect(api.itemsPerPage?.value).toBe(15)
        wrapper.unmount()
    })

    it('recomputes when the window is resized', async () => {
        const { wrapper, api } = withTable(buildTable())
        await nextTick()
        expect(api.itemsPerPage?.value).toBe(18)

        window.innerHeight = 600
        window.dispatchEvent(new Event('resize'))
        vi.runAllTimers()
        await nextTick()

        expect(api.itemsPerPage?.value).toBe(8)
        wrapper.unmount()
    })

    it('settles instead of chasing the resize its own result causes', async () => {
        // Applying a page size resizes the observed element, so the computation has to be
        // idempotent for the same geometry - otherwise the observer feeds itself forever.
        const { wrapper, api } = withTable(buildTable())
        await nextTick()
        const first = api.itemsPerPage?.value

        api.recalculate?.()
        api.recalculate?.()
        await nextTick()

        expect(api.itemsPerPage?.value).toBe(first)
        wrapper.unmount()
    })

    it('stops listening once the table is gone', async () => {
        const removeListener = vi.spyOn(window, 'removeEventListener')
        const { wrapper } = withTable(buildTable())
        await nextTick()

        wrapper.unmount()

        expect(removeListener).toHaveBeenCalledWith('resize', expect.any(Function))
        removeListener.mockRestore()
    })
})
