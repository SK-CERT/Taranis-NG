/**
 * Where a news item came from, as the cards show it: its OSINT source, or - for an item a user
 * entered by hand, which has none - who entered it ("Manual entry by Alice"), with the name of the
 * manual source an item entered before those were removed came from.
 */
export type NewsItemSourceData = {
    osint_source_name?: string | null
    source?: string | null
    entered_by?: string | null
    source_label?: string | null
}

type Translate = (key: string, params?: Record<string, unknown>) => string

/** The source to show; '' when nothing is known (the caller shows its own "unknown"). */
export function newsItemSourceName(data: NewsItemSourceData | null | undefined, t: Translate): string {
    if (!data) return ''
    if (data.entered_by !== undefined && data.entered_by !== null) {
        const entry = data.entered_by ? t('enter.manual_entry_by', { name: data.entered_by }) : t('enter.manual_entry')
        return data.source_label ? `${entry} · ${data.source_label}` : entry
    }
    return data.osint_source_name || data.source || ''
}
