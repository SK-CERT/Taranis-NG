import { beforeEach, describe, expect, it, vi } from 'vitest'
import ApiService from '@/services/api_service'
import { exportOSINTSources } from '@/api/config'

describe('OSINT source bulk API', () => {
    beforeEach(() => {
        vi.restoreAllMocks()
    })

    it('uses a direct blob POST so callers can handle download success and failure', async () => {
        const response = { data: new Blob(['{}']), headers: {} }
        const post = vi.spyOn(ApiService, 'post').mockResolvedValue(response)

        await expect(exportOSINTSources({ selection: ['source-1'] })).resolves.toBe(response)
        expect(post).toHaveBeenCalledWith('/config/export-osint-sources', { selection: ['source-1'] }, { responseType: 'blob' })
    })

    it('propagates export request errors to the UI', async () => {
        const failure = new Error('export failed')
        vi.spyOn(ApiService, 'post').mockRejectedValue(failure)

        await expect(exportOSINTSources({})).rejects.toBe(failure)
    })
})
