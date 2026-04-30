import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAssessStore } from '@/stores/assess'

vi.mock('@/api/assess', () => ({
  getManualOSINTSources: vi.fn(),
  getNewsItemsByGroup: vi.fn(),
  voteNewsItemAggregate: vi.fn(),
  readNewsItemAggregate: vi.fn(),
  importantNewsItemAggregate: vi.fn(),
  deleteNewsItemAggregate: vi.fn(),
  saveNewsItemAggregate: vi.fn()
}))

describe('Assess Store', () => {
  let assessApi

  beforeEach(async () => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    assessApi = await import('@/api/assess')
  })

  // ── Initial State ─────────────────────────────
  describe('Initial State', () => {
    it('should start with empty news items', () => {
      const store = useAssessStore()
      expect(store.newsitems).toEqual({ total_count: 0, items: [] })
    })

    it('should start with multi_select disabled', () => {
      const store = useAssessStore()
      expect(store.multi_select).toBe(false)
    })

    it('should start with empty selection', () => {
      const store = useAssessStore()
      expect(store.selection).toEqual([])
    })

    it('should start with empty filter', () => {
      const store = useAssessStore()
      expect(store.filter).toEqual({})
    })
  })

  // ── Getters ───────────────────────────────────
  describe('Getters', () => {
    it('getNewsItems should return newsitems ref', () => {
      const store = useAssessStore()
      expect(store.getNewsItems).toEqual({ total_count: 0, items: [] })
    })

    it('selectedItems should return a Set of selected item ids', () => {
      const store = useAssessStore()
      store.selection = [
        { id: 'a1', type: 'aggregate' },
        { id: 'a2', type: 'aggregate' }
      ]
      expect(store.selectedItems).toEqual(new Set(['a1', 'a2']))
    })

    it('selectedItems should be empty when nothing selected', () => {
      const store = useAssessStore()
      expect(store.selectedItems.size).toBe(0)
    })

    it('getManualOSINTSourcesList should return array even if data is non-array', () => {
      const store = useAssessStore()
      store.manual_osint_sources = null
      expect(store.getManualOSINTSourcesList).toEqual([])
    })

    it('getManualOSINTSourcesList should return sources when loaded', () => {
      const store = useAssessStore()
      store.manual_osint_sources = [{ id: 1, name: 'Manual Source' }]
      expect(store.getManualOSINTSourcesList).toEqual([{ id: 1, name: 'Manual Source' }])
    })
  })

  // ── Selection Actions ─────────────────────────
  describe('Selection', () => {
    it('multiSelect should enable multi-select and clear selection', () => {
      const store = useAssessStore()
      store.selection = [{ id: 'x', type: 'aggregate' }]

      store.multiSelect(true)

      expect(store.multi_select).toBe(true)
      expect(store.selection).toEqual([])
    })

    it('multiSelect(false) should disable and clear', () => {
      const store = useAssessStore()
      store.multi_select = true
      store.selection = [{ id: '1', type: 'aggregate' }]

      store.multiSelect(false)

      expect(store.multi_select).toBe(false)
      expect(store.selection).toEqual([])
    })

    it('select should add item to selection', () => {
      const store = useAssessStore()
      store.select({ id: 'a1', type: 'aggregate' })
      store.select({ id: 'a2', type: 'aggregate' })

      expect(store.selection).toHaveLength(2)
    })

    it('deselect should remove matching item by type and id', () => {
      const store = useAssessStore()
      store.selection = [
        { id: 'a1', type: 'aggregate' },
        { id: 'a2', type: 'aggregate' },
        { id: 'a3', type: 'aggregate' }
      ]

      store.deselect({ id: 'a2', type: 'aggregate' })

      expect(store.selection).toHaveLength(2)
      expect(store.selection.map((s) => s.id)).toEqual(['a1', 'a3'])
    })

    it('deselect should not remove when id does not match', () => {
      const store = useAssessStore()
      store.selection = [{ id: 'a1', type: 'aggregate' }]

      store.deselect({ id: 'missing', type: 'aggregate' })

      expect(store.selection).toHaveLength(1)
    })
  })

  // ── Load News Items ───────────────────────────
  describe('loadNewsItemsByGroup', () => {
    it('should load news items and update state', async () => {
      const items = [{ id: 'n1', title: 'News 1' }, { id: 'n2', title: 'News 2' }]
      vi.mocked(assessApi.getNewsItemsByGroup).mockResolvedValue({
        data: { total_count: 2, items }
      })

      const store = useAssessStore()
      await store.loadNewsItemsByGroup({ group_id: 'g1', data: { offset: 0 } })

      expect(assessApi.getNewsItemsByGroup).toHaveBeenCalledWith('g1', { offset: 0 })
      expect(store.newsitems.items).toEqual(items)
      expect(store.newsitems.total_count).toBe(2)
    })

    it('should default to empty when response has null data', async () => {
      vi.mocked(assessApi.getNewsItemsByGroup).mockResolvedValue({ data: null })

      const store = useAssessStore()
      await store.loadNewsItemsByGroup({ group_id: 'g1', data: {} })

      expect(store.newsitems).toEqual({ total_count: 0, items: [] })
    })

    it('should not update state when response is falsy', async () => {
      vi.mocked(assessApi.getNewsItemsByGroup).mockResolvedValue(null)

      const store = useAssessStore()
      store.newsitems = { total_count: 5, items: [{ id: 'old' }] }
      await store.loadNewsItemsByGroup({ group_id: 'g1', data: {} })

      // State should remain unchanged
      expect(store.newsitems.total_count).toBe(5)
    })
  })

  // ── Aggregate Actions ─────────────────────────
  describe('Aggregate Actions', () => {
    it('voteNewsItemAggregate should call API with correct args', async () => {
      const resp = { data: { votes: 5 } }
      vi.mocked(assessApi.voteNewsItemAggregate).mockResolvedValue(resp)

      const store = useAssessStore()
      const result = await store.voteNewsItemAggregate('g1', 'agg1', 1)

      expect(assessApi.voteNewsItemAggregate).toHaveBeenCalledWith('g1', 'agg1', 1)
      expect(result).toBe(resp)
    })

    it('readNewsItemAggregate should call API', async () => {
      vi.mocked(assessApi.readNewsItemAggregate).mockResolvedValue({ data: {} })

      const store = useAssessStore()
      await store.readNewsItemAggregate('g1', 'agg1')

      expect(assessApi.readNewsItemAggregate).toHaveBeenCalledWith('g1', 'agg1')
    })

    it('importantNewsItemAggregate should call API', async () => {
      vi.mocked(assessApi.importantNewsItemAggregate).mockResolvedValue({ data: {} })

      const store = useAssessStore()
      await store.importantNewsItemAggregate('g1', 'agg1')

      expect(assessApi.importantNewsItemAggregate).toHaveBeenCalledWith('g1', 'agg1')
    })

    it('deleteNewsItemAggregate should call API', async () => {
      vi.mocked(assessApi.deleteNewsItemAggregate).mockResolvedValue({ data: {} })

      const store = useAssessStore()
      await store.deleteNewsItemAggregate('g1', 'agg1')

      expect(assessApi.deleteNewsItemAggregate).toHaveBeenCalledWith('g1', 'agg1')
    })

    it('saveNewsItemAggregate should call API with all parameters', async () => {
      vi.mocked(assessApi.saveNewsItemAggregate).mockResolvedValue({ data: {} })

      const store = useAssessStore()
      await store.saveNewsItemAggregate('g1', 'agg1', 'Title', 'Desc', 'Comment')

      expect(assessApi.saveNewsItemAggregate).toHaveBeenCalledWith(
        'g1', 'agg1', 'Title', 'Desc', 'Comment'
      )
    })
  })

  // ── Other Actions ─────────────────────────────
  describe('Other Actions', () => {
    it('changeCurrentGroup should update current_group_id', () => {
      const store = useAssessStore()
      store.changeCurrentGroup('group-42')
      expect(store.current_group_id).toBe('group-42')
    })

    it('setFilter should update filter state', () => {
      const store = useAssessStore()
      const newFilter = { search: 'test', read: false, important: true }
      store.setFilter(newFilter)
      expect(store.filter).toEqual(newFilter)
    })

    it('loadManualOSINTSources should fetch and store sources', async () => {
      const sources = [{ id: 1, name: 'Manual' }]
      vi.mocked(assessApi.getManualOSINTSources).mockResolvedValue({ data: sources })

      const store = useAssessStore()
      await store.loadManualOSINTSources()

      expect(store.manual_osint_sources).toEqual(sources)
    })

    it('loadManualOSINTSources should default to empty array', async () => {
      vi.mocked(assessApi.getManualOSINTSources).mockResolvedValue({ data: null })

      const store = useAssessStore()
      await store.loadManualOSINTSources()

      expect(store.manual_osint_sources).toEqual([])
    })
  })
})
