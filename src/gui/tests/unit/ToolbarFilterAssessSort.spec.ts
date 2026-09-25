import { beforeEach, describe, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'
import ApiService from '@/services/api_service'
import { getNewsItemsByGroup } from '@/api/assess'
import ToolbarFilterAssess from '@/components/assess/ToolbarFilterAssess.vue'
import { mountWithPlugins } from '../helpers/mount-helpers'

vi.mock('vue-router', () => ({
    useRoute: () => ({ query: {} })
}))

vi.mock('@/services/api_service', () => ({
    default: { getWithCancel: vi.fn() }
}))

const latestSort = (wrapper: ReturnType<typeof mountWithPlugins>): string => {
    const updates = wrapper.emitted('update-filter') ?? []
    return (updates.at(-1)?.[0] as { sort: string }).sort
}

const sortChip = (wrapper: ReturnType<typeof mountWithPlugins>, title: string) => {
    const chip = wrapper.find(`[title="${title}"]`)
    expect(chip.exists()).toBe(true)
    return chip
}

describe('ToolbarFilterAssess sorting', () => {
    beforeEach(() => vi.clearAllMocks())

    it('allows relevance descending, relevance ascending, and date ordering to be selected distinctly', async () => {
        const wrapper = mountWithPlugins(ToolbarFilterAssess, {
            props: { analyze_selector: true },
            global: { stubs: { ToolbarGroup: true } }
        })

        await sortChip(wrapper, 'Sort news items by relevance descending').trigger('click')
        expect(latestSort(wrapper)).toBe('RELEVANCE_DESC')
        await nextTick()

        await sortChip(wrapper, 'Sort news items by relevance descending').trigger('click')
        expect(latestSort(wrapper)).toBe('RELEVANCE_ASC')
        await nextTick()

        await sortChip(wrapper, 'Sort news items by collected date descending').trigger('click')
        expect(latestSort(wrapper)).toBe('DATE_DESC')

        await sortChip(wrapper, 'Sort news items by collected date descending').trigger('click')
        expect(latestSort(wrapper)).toBe('DATE_ASC')
    })

    it.each(['RELEVANCE_DESC', 'RELEVANCE_ASC'])('passes %s through the Assess API query', (sort) => {
        getNewsItemsByGroup('group-a', {
            offset: 0,
            limit: 20,
            filter: { search: '', read: 'ALL', important: 'ALL', relevant: 'ALL', range: 'ALL', sort }
        })

        expect(ApiService.getWithCancel).toHaveBeenCalledWith(
            'screenData',
            `/assess/news-item-aggregates-by-group/group-a?offset=0&limit=20&sort=${sort}`
        )
    })
})
