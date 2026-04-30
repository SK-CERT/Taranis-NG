import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { effectScope } from 'vue'
import { useAttributes } from '@/components/common/attribute/useAttributes'

// Mock dependencies
const mockCheckPermission = vi.fn(() => true)

vi.mock('@/stores/auth', () => ({
  useAuthStore: () => ({
    checkPermission: mockCheckPermission
  })
}))

vi.mock('@/api/analyze', () => ({
  getReportItemData: vi.fn(),
  holdLockReportItem: vi.fn(),
  lockReportItem: vi.fn(),
  unlockReportItem: vi.fn(),
  updateReportItem: vi.fn()
}))

function makeProps(overrides = {}) {
  return {
    edit: false,
    modify: true,
    readOnly: false,
    reportItemId: 'report-1',
    values: [],
    attributeGroup: {
      id: 'ag-1',
      min_occurrence: 0,
      max_occurrence: 10,
      attribute: { type: 'TEXT' }
    },
    ...overrides
  }
}

// Helper: run composable in a Vue effect scope (provides onUnmounted support)
function setupComposable(props) {
  let result
  const scope = effectScope()
  scope.run(() => {
    result = useAttributes(props)
  })
  return { result, scope }
}

describe('useAttributes', () => {
  let analyzeApi

  beforeEach(async () => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    mockCheckPermission.mockReturnValue(true)
    analyzeApi = await import('@/api/analyze')
  })

  // ── canModify ─────────────────────────────────
  describe('canModify', () => {
    it('should be true when edit=true (create mode)', () => {
      const { result, scope } = setupComposable(makeProps({ edit: true }))
      expect(result.canModify.value).toBe(true)
      scope.stop()
    })

    it('should be true when edit=false, modify=true, and has permission', () => {
      mockCheckPermission.mockReturnValue(true)
      const { result, scope } = setupComposable(makeProps({ edit: false, modify: true }))
      expect(result.canModify.value).toBe(true)
      scope.stop()
    })

    it('should be false when edit=false and modify=false', () => {
      const { result, scope } = setupComposable(makeProps({ edit: false, modify: false }))
      expect(result.canModify.value).toBe(false)
      scope.stop()
    })

    it('should be false when edit=false and permission denied', () => {
      mockCheckPermission.mockReturnValue(false)
      const { result, scope } = setupComposable(makeProps({ edit: false, modify: true }))
      expect(result.canModify.value).toBe(false)
      scope.stop()
    })
  })

  // ── addButtonVisible ──────────────────────────
  describe('addButtonVisible', () => {
    it('should be true when under max_occurrence and canModify', () => {
      const { result, scope } = setupComposable(
        makeProps({ values: [{ id: 1, value: '' }], readOnly: false })
      )
      expect(result.addButtonVisible.value).toBe(true)
      scope.stop()
    })

    it('should be false when at max_occurrence', () => {
      const values = Array.from({ length: 2 }, (_, i) => ({ id: i, value: '' }))
      const { result, scope } = setupComposable(
        makeProps({
          values,
          attributeGroup: { id: 'ag', min_occurrence: 0, max_occurrence: 2, attribute: { type: 'TEXT' } }
        })
      )
      expect(result.addButtonVisible.value).toBe(false)
      scope.stop()
    })

    it('should be false when readOnly', () => {
      const { result, scope } = setupComposable(makeProps({ readOnly: true }))
      expect(result.addButtonVisible.value).toBe(false)
      scope.stop()
    })
  })

  // ── delButtonVisible ──────────────────────────
  describe('delButtonVisible', () => {
    it('should be true when values count exceeds min_occurrence', () => {
      const values = [{ id: 1, value: '' }, { id: 2, value: '' }]
      const { result, scope } = setupComposable(
        makeProps({
          values,
          attributeGroup: { id: 'ag', min_occurrence: 1, max_occurrence: 10, attribute: { type: 'TEXT' } }
        })
      )
      expect(result.delButtonVisible.value).toBe(true)
      scope.stop()
    })

    it('should be false when at min_occurrence', () => {
      const values = [{ id: 1, value: '' }]
      const { result, scope } = setupComposable(
        makeProps({
          values,
          attributeGroup: { id: 'ag', min_occurrence: 1, max_occurrence: 10, attribute: { type: 'TEXT' } }
        })
      )
      expect(result.delButtonVisible.value).toBe(false)
      scope.stop()
    })
  })

  // ── add (non-edit mode) ───────────────────────
  describe('add (create mode, edit=false)', () => {
    it('should push a new value with id=-1', async () => {
      const props = makeProps({ edit: false, values: [] })
      const { result, scope } = setupComposable(props)
      await result.add()

      expect(props.values).toHaveLength(1)
      expect(props.values[0]).toMatchObject({ id: -1, index: 0, value: '' })
      scope.stop()
    })

    it('should assign sequential indices', async () => {
      const props = makeProps({ edit: false, values: [{ id: -1, index: 0, value: 'first' }] })
      const { result, scope } = setupComposable(props)
      await result.add()

      expect(props.values).toHaveLength(2)
      expect(props.values[0].index).toBe(0)
      expect(props.values[1].index).toBe(1)
      scope.stop()
    })
  })

  // ── add (edit mode) ───────────────────────────
  describe('add (edit mode, edit=true)', () => {
    it('should call API and push new value with server-assigned id', async () => {
      vi.mocked(analyzeApi.updateReportItem).mockResolvedValue({
        data: 'update-ref'
      })
      vi.mocked(analyzeApi.getReportItemData).mockResolvedValue({
        data: {
          attribute_id: 42,
          attribute_last_updated: '2024-01-01',
          attribute_user: 'admin'
        }
      })

      const props = makeProps({ edit: true, values: [] })
      const { result, scope } = setupComposable(props)
      await result.add()

      expect(analyzeApi.updateReportItem).toHaveBeenCalledWith('report-1', {
        add: true,
        report_item_id: 'report-1',
        attribute_id: -1,
        attribute_group_item_id: 'ag-1'
      })
      expect(props.values).toHaveLength(1)
      expect(props.values[0].id).toBe(42)
      scope.stop()
    })

    it('should not push value on API error', async () => {
      vi.mocked(analyzeApi.updateReportItem).mockRejectedValue(new Error('fail'))

      const props = makeProps({ edit: true, values: [] })
      const { result, scope } = setupComposable(props)
      await result.add()

      expect(props.values).toHaveLength(0)
      scope.stop()
    })
  })

  // ── del ───────────────────────────────────────
  describe('del', () => {
    it('should splice value at index in create mode', async () => {
      const values = [
        { id: -1, index: 0, value: 'a' },
        { id: -1, index: 1, value: 'b' },
        { id: -1, index: 2, value: 'c' }
      ]
      const props = makeProps({ edit: false, values })
      const { result, scope } = setupComposable(props)
      await result.del(1)

      expect(props.values).toHaveLength(2)
      expect(props.values.map((v) => v.value)).toEqual(['a', 'c'])
      scope.stop()
    })

    it('should call API then splice in edit mode', async () => {
      vi.mocked(analyzeApi.updateReportItem).mockResolvedValue({ data: {} })

      const values = [{ id: 10, index: 0, value: 'x' }]
      const props = makeProps({ edit: true, values })
      const { result, scope } = setupComposable(props)
      await result.del(0)

      expect(analyzeApi.updateReportItem).toHaveBeenCalledWith('report-1', {
        delete: true,
        report_item_id: 'report-1',
        attribute_group_item_id: 'ag-1',
        attribute_id: 10
      })
      expect(props.values).toHaveLength(0)
      scope.stop()
    })

    it('should not splice on API error in edit mode', async () => {
      vi.mocked(analyzeApi.updateReportItem).mockRejectedValue(new Error('403'))

      const values = [{ id: 10, index: 0, value: 'x' }]
      const props = makeProps({ edit: true, values })
      const { result, scope } = setupComposable(props)
      await result.del(0)

      expect(props.values).toHaveLength(1)
      scope.stop()
    })

    it('should handle invalid index gracefully', async () => {
      const props = makeProps({ values: [{ id: 1, value: 'a' }] })
      const { result, scope } = setupComposable(props)
      await result.del(5) // out of bounds
      expect(props.values).toHaveLength(1) // unchanged
      scope.stop()
    })
  })

  // ── getLockedStyle ────────────────────────────
  describe('getLockedStyle', () => {
    it('should return "locked-style" when field is locked', () => {
      const values = [{ id: 1, value: 'x', locked: true }]
      const { result, scope } = setupComposable(makeProps({ values }))
      expect(result.getLockedStyle(0)).toBe('locked-style')
      scope.stop()
    })

    it('should return empty string when field is not locked', () => {
      const values = [{ id: 1, value: 'x', locked: false }]
      const { result, scope } = setupComposable(makeProps({ values }))
      expect(result.getLockedStyle(0)).toBe('')
      scope.stop()
    })

    it('should return empty string for invalid index', () => {
      const { result, scope } = setupComposable(makeProps({ values: [] }))
      expect(result.getLockedStyle(0)).toBe('')
      scope.stop()
    })
  })

  // ── onFocus / onBlur ──────────────────────────
  describe('onFocus / onBlur', () => {
    it('onFocus should call lockReportItem in edit mode', async () => {
      vi.mocked(analyzeApi.lockReportItem).mockResolvedValue({})

      const values = [{ id: 5, value: 'val' }]
      const { result, scope } = setupComposable(makeProps({ edit: true, values }))
      await result.onFocus(0)

      expect(analyzeApi.lockReportItem).toHaveBeenCalledWith('report-1', { field_id: 5 })
      scope.stop()
    })

    it('onFocus should not call API in create mode', async () => {
      const values = [{ id: -1, value: '' }]
      const { result, scope } = setupComposable(makeProps({ edit: false, values }))
      await result.onFocus(0)

      expect(analyzeApi.lockReportItem).not.toHaveBeenCalled()
      scope.stop()
    })

    it('onBlur should call unlockReportItem in edit mode', async () => {
      vi.mocked(analyzeApi.updateReportItem).mockResolvedValue({ data: 'ref' })
      vi.mocked(analyzeApi.getReportItemData).mockResolvedValue({
        data: { attribute_last_updated: 'now', attribute_user: 'admin' }
      })
      vi.mocked(analyzeApi.unlockReportItem).mockResolvedValue({})

      const values = [{ id: 5, value: 'val' }]
      const { result, scope } = setupComposable(
        makeProps({
          edit: true,
          values,
          attributeGroup: { id: 'ag-1', min_occurrence: 0, max_occurrence: 10, attribute: { type: 'TEXT' } }
        })
      )
      await result.onBlur(0)

      expect(analyzeApi.unlockReportItem).toHaveBeenCalledWith('report-1', { field_id: 5 })
      scope.stop()
    })
  })

  // ── onEdit ────────────────────────────────────
  describe('onEdit', () => {
    it('should send updated value to API in edit mode', async () => {
      vi.mocked(analyzeApi.updateReportItem).mockResolvedValue({ data: 'ref' })
      vi.mocked(analyzeApi.getReportItemData).mockResolvedValue({
        data: { attribute_last_updated: '2024-02-01', attribute_user: 'editor' }
      })

      const values = [{ id: 7, value: 'new-val', value_description: 'desc' }]
      const props = makeProps({ edit: true, values })
      const { result, scope } = setupComposable(props)
      await result.onEdit(0)

      expect(analyzeApi.updateReportItem).toHaveBeenCalledWith('report-1', {
        update: true,
        attribute_id: 7,
        attribute_value: 'new-val',
        value_description: 'desc'
      })
      expect(props.values[0].last_updated).toBe('2024-02-01')
      expect(props.values[0].user).toEqual({ name: 'editor' })
      scope.stop()
    })

    it('should replace * with % for CPE type', async () => {
      vi.mocked(analyzeApi.updateReportItem).mockResolvedValue({ data: 'ref' })
      vi.mocked(analyzeApi.getReportItemData).mockResolvedValue({
        data: { attribute_last_updated: 'now', attribute_user: 'admin' }
      })

      const values = [{ id: 1, value: 'cpe:2.3:*:vendor:*' }]
      const props = makeProps({
        edit: true,
        values,
        attributeGroup: { id: 'ag', min_occurrence: 0, max_occurrence: 10, attribute: { type: 'CPE' } }
      })
      const { result, scope } = setupComposable(props)
      await result.onEdit(0)

      expect(analyzeApi.updateReportItem).toHaveBeenCalledWith(
        'report-1',
        expect.objectContaining({ attribute_value: 'cpe:2.3:%:vendor:%' })
      )
      scope.stop()
    })

    it('should not call API in create mode', async () => {
      const values = [{ id: -1, value: 'val' }]
      const { result, scope } = setupComposable(makeProps({ edit: false, values }))
      await result.onEdit(0)

      expect(analyzeApi.updateReportItem).not.toHaveBeenCalled()
      scope.stop()
    })
  })

  // ── enumSelected ──────────────────────────────
  describe('enumSelected', () => {
    it('should set value and value_description then call onEdit', async () => {
      vi.mocked(analyzeApi.updateReportItem).mockResolvedValue({ data: 'ref' })
      vi.mocked(analyzeApi.getReportItemData).mockResolvedValue({
        data: { attribute_last_updated: 'now', attribute_user: 'a' }
      })

      const values = [{ id: 1, value: '', value_description: '' }]
      const props = makeProps({ edit: true, values })
      const { result, scope } = setupComposable(props)

      result.enumSelected({ index: 0, value: 'opt-a', value_description: 'Option A' })

      // Wait for async onEdit
      await vi.waitFor(() => {
        expect(props.values[0].value).toBe('opt-a')
        expect(props.values[0].value_description).toBe('Option A')
      })
      scope.stop()
    })
  })
})
