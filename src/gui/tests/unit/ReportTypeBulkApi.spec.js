import { beforeEach, describe, expect, it, vi } from 'vitest'
import ApiService from '@/services/api_service'
import { exportReportTypes, importReportTypes } from '@/api/config'

describe('report type bulk API', () => {
    beforeEach(() => {
        vi.restoreAllMocks()
    })

    it('sends only the selected report type ids with a blob export request', async () => {
        const response = { data: new Blob(['{}']), headers: {} }
        const post = vi.spyOn(ApiService, 'post').mockResolvedValue(response)
        const selection = [17, 24]

        await expect(exportReportTypes({ selection })).resolves.toBe(response)
        expect(post).toHaveBeenCalledWith('/config/export-report-types', { selection }, { responseType: 'blob' })
    })

    it('propagates export errors to the UI', async () => {
        const failure = new Error('export failed')
        vi.spyOn(ApiService, 'post').mockRejectedValue(failure)

        await expect(exportReportTypes({ selection: [17] })).rejects.toBe(failure)
    })

    it('uploads the JSON file as multipart form data', async () => {
        const formData = new FormData()
        formData.append('file', new File(['{}'], 'report-types.json', { type: 'application/json' }))
        const post = vi.spyOn(ApiService, 'upload').mockResolvedValue({ data: { report_types_created: 1 } })

        await importReportTypes(formData)

        expect(post).toHaveBeenCalledWith('/config/import-report-types', formData)
    })
})
