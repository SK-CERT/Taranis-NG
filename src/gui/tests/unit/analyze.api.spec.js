import { describe, it, expect, beforeEach, vi } from 'vitest'
import {
    createNewReportItem,
    downloadReportItemAttachment,
    getReportItemData,
    updateAttachmentDescription,
    uploadAttachment
} from '@/api/analyze'
import ApiService from '@/services/api_service'

vi.mock('@/services/api_service', () => ({
    default: {
        get: vi.fn(),
        post: vi.fn(),
        put: vi.fn(),
        upload: vi.fn(),
        download: vi.fn()
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
            attributes: [{ id: -1, attribute_group_item_id: 5, value: 'test' }],
            language: 'cs',
            tag_ids: [7]
        }

        createNewReportItem(data)

        expect(ApiService.post).toHaveBeenCalledWith('/analyze/report-items', {
            uuid: '9c6988d9-75b8-40b5-af23-6aff10f554d5',
            title: 'sseefsefs',
            title_prefix: '',
            report_item_type_id: 1,
            state_id: 2,
            news_item_aggregates: [{ id: 11 }],
            remote_report_items: [{ id: 22 }],
            attributes: [{ id: -1, attribute_group_item_id: 5, value: 'test' }],
            language: 'cs',
            tag_ids: [7]
        })
    })

    it('uploads an attachment with the backend multipart field names', () => {
        const file = new File(['evidence'], 'evidence.txt', { type: 'text/plain' })

        uploadAttachment(42, 7, file, 'Collected evidence')

        expect(ApiService.upload).toHaveBeenCalledOnce()
        const [url, formData] = ApiService.upload.mock.calls[0]
        expect(url).toBe('/analyze/report-items/42/file-attributes')
        expect(formData.get('file')).toBe(file)
        expect(formData.get('attribute_group_item_id')).toBe('7')
        expect(formData.get('description')).toBe('Collected evidence')
    })

    it('updates an attachment description on the existing attachment resource', () => {
        updateAttachmentDescription({ report_item_id: 42, attribute_id: 9, description: 'Updated' })

        expect(ApiService.put).toHaveBeenCalledWith('/analyze/report-items/42/file-attributes/9', { description: 'Updated' })
    })

    it('downloads an attachment through its report-scoped authorized resource', () => {
        downloadReportItemAttachment(42, 9, 'evidence.txt')

        expect(ApiService.download).toHaveBeenCalledWith('/analyze/report-items/42/file-attributes/9/file', undefined, 'evidence.txt')
    })

    // Another user's view refetches what changed; with `for...in` it asked for the array's indexes
    // (0--1) instead of the news items added, and read a translated value in the source language.
    it('getReportItemData asks for the added ids themselves, in the language being edited', () => {
        getReportItemData(7, { add: true, aggregate_ids: [11, 12], remote_report_item_ids: [5], language: 'cs', source_language: 'en' })

        expect(ApiService.get).toHaveBeenCalledWith(
            '/analyze/report-items/7/data?add=true&aggregate_ids=11--12&remote_report_item_ids=5&language=cs&source_language=en'
        )
    })

    it('getReportItemData leaves out what did not change', () => {
        getReportItemData(7, { update: true, attribute_id: 3 })

        expect(ApiService.get).toHaveBeenCalledWith('/analyze/report-items/7/data?update=true&attribute_id=3')
    })
})
