import { describe, it, expect, beforeEach, vi } from 'vitest'
import { createNewReportItem } from '@/api/analyze'
import ApiService from '@/services/api_service'

vi.mock('@/services/api_service', () => ({
  default: {
    post: vi.fn()
  }
}))

describe('analyze api', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('createNewReportItem strips server-managed fields from the create payload', () => {
    const data = {
      id: 173,
      uuid: '9c6988d9-75b8-40b5-af23-6aff10f554d5',
      created: '10.04.2026 - 14:59',
      last_updated: '10.04.2026 - 14:59',
      title: 'sseefsefs',
      title_prefix: '',
      report_item_type_id: 1,
      state_id: 2,
      news_item_aggregates: [{ id: 11 }],
      remote_report_items: [{ id: 22 }],
      attributes: [{ id: -1, attribute_group_item_id: 5, value: 'test' }]
    }

    createNewReportItem(data)

    expect(ApiService.post).toHaveBeenCalledWith('/analyze/report-items', {
      title: 'sseefsefs',
      title_prefix: '',
      report_item_type_id: 1,
      state_id: 2,
      news_item_aggregates: [{ id: 11 }],
      remote_report_items: [{ id: 22 }],
      attributes: [{ id: -1, attribute_group_item_id: 5, value: 'test' }]
    })
  })
})
