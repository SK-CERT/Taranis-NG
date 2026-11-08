import { describe, expect, it } from 'vitest'
import { cveColor, cveStateKey } from '@/utils/cveStatus'

describe('CVE status', () => {
    it('shows a published record that lags behind its report as out of date', () => {
        expect(cveStateKey({ cve_id: 'CVE-2026-1234', state: 'RESERVED' })).toBe('reserved')
        expect(cveStateKey({ cve_id: 'CVE-2026-1234', state: 'PUBLISHED' })).toBe('published')
        expect(cveStateKey({ cve_id: 'CVE-2026-1234', state: 'PUBLISHED', out_of_date: true })).toBe('out_of_date')
        expect(cveStateKey({ cve_id: 'CVE-2026-1234', state: 'REJECTED' })).toBe('rejected')
        expect(cveStateKey(null)).toBe('')
    })

    it('colours an error from CVE Services before the state', () => {
        expect(cveColor({ cve_id: 'CVE-2026-1234', state: 'PUBLISHED' })).toBe('success')
        expect(cveColor({ cve_id: 'CVE-2026-1234', state: 'PUBLISHED', out_of_date: true })).toBe('warning')
        expect(cveColor({ cve_id: 'CVE-2026-1234', state: 'REJECTED' })).toBe('grey')
        expect(cveColor({ cve_id: 'CVE-2026-1234', state: 'PUBLISHED', last_error: 'refused' })).toBe('error')
        expect(cveColor(undefined)).toBe('primary')
    })
})
