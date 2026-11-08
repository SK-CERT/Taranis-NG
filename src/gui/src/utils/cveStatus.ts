/**
 * Where a CVD Report's CVE record stands at CVE Services, as core reports it (``cve_status``), and
 * how the GUI shows it: one state key for the label (``gna.cve.state.<key>``) and a chip colour.
 */

export type CveState = 'RESERVED' | 'PUBLISHED' | 'REJECTED'

export type CveStatus = {
    cve_id: string
    state: CveState
    out_of_date?: boolean
    last_error?: string | null
    rejected_reason?: string | null
}

export type CveStateKey = 'reserved' | 'published' | 'out_of_date' | 'rejected'

/** The state shown: a published record that lags behind its report is out of date. */
export function cveStateKey(status: CveStatus | null | undefined): CveStateKey | '' {
    if (!status) return ''
    if (status.state === 'PUBLISHED') return status.out_of_date ? 'out_of_date' : 'published'
    return status.state === 'REJECTED' ? 'rejected' : 'reserved'
}

const COLORS: Record<CveStateKey, string> = { reserved: 'primary', published: 'success', out_of_date: 'warning', rejected: 'grey' }

/** The chip colour: an error from CVE Services first, then the state's. */
export function cveColor(status: CveStatus | null | undefined): string {
    if (status?.last_error) return 'error'
    const key = cveStateKey(status)
    return key ? COLORS[key] : 'primary'
}
