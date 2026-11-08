/**
 * Structured attribute values: the fields of a CVD Report that hold an object (an affected product,
 * a credit, a timeline event, a relationship to another record, a reference, a JSON fragment), stored
 * as JSON in the attribute's `value`. Core checks them against the CVE Record Format when they are
 * saved; here they are read, written with a stable key order (so an unchanged object is never sent
 * again) and summed up in one line where they are only shown.
 */

export const STRUCTURED_TYPES = ['AFFECTED', 'CREDIT', 'TIMELINE', 'RELATIONSHIP', 'REFERENCE', 'JSON'] as const
export type StructuredType = (typeof STRUCTURED_TYPES)[number]

/** Version numbering schemes the CVE Record Format names as examples; any other may be typed. */
export const VERSION_TYPES = ['semver', 'custom', 'git', 'python', 'maven', 'npm', 'rpm', 'deb'] as const

export type StructuredData = Record<string, unknown>

export function isStructuredType(type: unknown): type is StructuredType {
    return typeof type === 'string' && (STRUCTURED_TYPES as readonly string[]).includes(type)
}

/** The object a stored value holds; an empty one for an empty or malformed value. */
export function parseStructured(raw: unknown): StructuredData {
    if (typeof raw !== 'string' || !raw.trim()) return {}
    try {
        const parsed: unknown = JSON.parse(raw)
        return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? (parsed as StructuredData) : {}
    } catch {
        return {}
    }
}

/** Drop what holds nothing (empty texts, lists and objects), so an untouched field sends nothing. */
function prune(value: unknown): unknown {
    if (typeof value === 'string') return value.trim() ? value : undefined
    if (Array.isArray(value)) {
        const items = value.map(prune).filter((item) => item !== undefined)
        return items.length ? items : undefined
    }
    if (value && typeof value === 'object') {
        const entries = Object.keys(value as StructuredData)
            .sort()
            .map((key) => [key, prune((value as StructuredData)[key])] as const)
            .filter(([, item]) => item !== undefined)
        return entries.length ? Object.fromEntries(entries) : undefined
    }
    return value === null ? undefined : value
}

/** The value to store: the object as JSON with sorted keys, or '' when it holds nothing. */
export function serializeStructured(data: StructuredData): string {
    const pruned = prune(data)
    return pruned === undefined ? '' : JSON.stringify(pruned)
}

function text(value: unknown): string {
    return value === undefined || value === null ? '' : String(value)
}

function versionsSummary(versions: unknown): string {
    if (!Array.isArray(versions)) return ''
    return versions
        .filter((version): version is StructuredData => !!version && typeof version === 'object')
        .map((version) => {
            const start = text(version['version'])
            const open = start === '' || start === '0' || start === '*'
            let span = start
            if (version['lessThan']) span = open ? `< ${text(version['lessThan'])}` : `${start} – < ${text(version['lessThan'])}`
            else if (version['lessThanOrEqual'])
                span = open ? `≤ ${text(version['lessThanOrEqual'])}` : `${start} – ≤ ${text(version['lessThanOrEqual'])}`
            // Status changes within a range: "affected; unaffected from 1.2".
            const changes = (Array.isArray(version['changes']) ? version['changes'] : [])
                .filter((change): change is StructuredData => !!change && typeof change === 'object')
                .map((change) => `; ${text(change['status']) || 'unknown'} from ${text(change['at'])}`)
                .join('')
            return `${span} (${text(version['status']) || 'unknown'}${changes})`
        })
        .join(', ')
}

/** One line for a structured value, for where it is shown rather than edited. */
export function structuredSummary(type: StructuredType, raw: unknown): string {
    const data = parseStructured(raw)
    switch (type) {
        case 'AFFECTED': {
            const name = [data['vendor'], data['product'] || data['packageName']].filter(Boolean).map(text).join(' ')
            const versions = versionsSummary(data['versions'])
            return versions ? `${name}: ${versions}` : name
        }
        case 'CREDIT':
            return data['type'] ? `${text(data['value'])} (${text(data['type'])})` : text(data['value'])
        case 'TIMELINE':
            return `${text(data['time']).replace('T', ' ')}: ${text(data['value'])}`
        case 'RELATIONSHIP':
            return `${text(data['type'])} ${text(data['destId'])}`.trim()
        case 'REFERENCE':
            return data['name'] ? `${text(data['name'])} <${text(data['url'])}>` : text(data['url'])
        default:
            return Object.keys(data).length ? JSON.stringify(data) : ''
    }
}

/** The URL a reference points at; empty when it has none. */
export function referenceUrl(raw: unknown): string {
    return text(parseStructured(raw)['url']).trim()
}
