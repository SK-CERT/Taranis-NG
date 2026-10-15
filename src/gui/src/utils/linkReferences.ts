/**
 * Stable link references.
 *
 * Text cites a link by the link's stable key, written as a token such as `[#k3f9a2]`. The key
 * travels with its link - for a report it is kept in the LINK value's `value_description`, for a
 * product in the link's `key` - so inserting, moving or deleting links never changes what a
 * citation points at. Core renders the tokens to `[n]` numbers for presenters and public web; the
 * numbers shown in the editor are those of the links being edited.
 */

export const LINK_KEY_LENGTH = 6
const LINK_KEY_ALPHABET = 'abcdefghijklmnopqrstuvwxyz0123456789'
const LINK_KEY_PATTERN = '[a-z0-9]{4,12}'
const LINK_KEY_RE = new RegExp(`^${LINK_KEY_PATTERN}$`)

/** Matches one citation token; the key is group 1. Global, so reset lastIndex or use matchAll. */
export const LINK_TOKEN_RE = new RegExp(`\\[#(${LINK_KEY_PATTERN})\\]`, 'g')

/** Attribute types whose text may cite links. */
export const CITING_TYPES: readonly string[] = ['STRING', 'TEXT', 'RICH_TEXT']

/** A link as the editors keep it: the same shape as a report attribute value. */
export type LinkValue = {
    value?: unknown
    value_description?: unknown
    locked?: boolean
    [key: string]: unknown
}

/** A link from elsewhere (e.g. a report in a product) that citing copies into the form's own links. */
export type ExternalLink = {
    key: string | null
    url: string
}

/** A link that text can cite, with the number it shows as. */
export type CitableLink = {
    key: string
    url: string
    number: number
}

export const isLinkKey = (value: unknown): value is string => typeof value === 'string' && LINK_KEY_RE.test(value)

export const linkToken = (key: string): string => `[#${key}]`

/** Return a random link key that is not in `taken`. */
export const generateLinkKey = (taken: Iterable<string> = []): string => {
    const used = new Set(taken)
    const bytes = new Uint8Array(LINK_KEY_LENGTH)
    for (;;) {
        window.crypto.getRandomValues(bytes)
        const key = Array.from(bytes, (byte) => LINK_KEY_ALPHABET[byte % LINK_KEY_ALPHABET.length]).join('')
        if (!used.has(key)) {
            return key
        }
    }
}

/** Only an explicit http(s) URL counts as a link - never javascript: or data: URLs. */
export const isHttpUrl = (value: unknown): value is string => {
    if (typeof value !== 'string') {
        return false
    }
    const trimmed = value.trim()
    if (!/^https?:\/\//i.test(trimmed)) {
        return false
    }
    try {
        const url = new URL(trimmed)
        return url.protocol === 'http:' || url.protocol === 'https:'
    } catch {
        return false
    }
}

const urlOf = (link: LinkValue): string => (typeof link.value === 'string' ? link.value.trim() : '')

/**
 * Number links the way core numbers them: links without URL are skipped, and a URL that is
 * already listed keeps its earlier number.
 */
export const numberLinks = (links: Iterable<LinkValue>): CitableLink[] => {
    const numberByUrl = new Map<string, number>()
    const result: CitableLink[] = []
    for (const link of links) {
        const url = urlOf(link)
        if (!url || !isLinkKey(link.value_description)) {
            continue
        }
        let number = numberByUrl.get(url)
        if (number === undefined) {
            number = numberByUrl.size + 1
            numberByUrl.set(url, number)
        }
        result.push({ key: link.value_description, url, number })
    }
    return result
}

/** The keys cited in `text`, in order, repeats included. */
export const citedKeys = (text: unknown): string[] =>
    typeof text === 'string' ? Array.from(text.matchAll(LINK_TOKEN_RE), (match) => match[1] as string) : []

/** Insert `token` in place of the selection `start`..`end` and return the text and the caret after it. */
export const insertAtCaret = (text: string, token: string, start?: number | null, end?: number | null) => {
    const from = Math.min(Math.max(start ?? text.length, 0), text.length)
    const to = Math.min(Math.max(end ?? from, from), text.length)
    const before = text.slice(0, from)
    // Separate the citation from a preceding word, as in "Fixed upstream [#k3f9a2]".
    const spacer = before && !/\s$/.test(before) ? ' ' : ''
    const inserted = `${spacer}${token}`
    return { text: `${before}${inserted}${text.slice(to)}`, caret: from + inserted.length }
}

export type ReferenceSegment = { text: string } | { key: string; link: CitableLink | undefined }

/** Split `text` into plain runs and citations, for rendering without v-html. */
export const splitReferences = (text: unknown, resolve: (key: string) => CitableLink | undefined): ReferenceSegment[] => {
    if (typeof text !== 'string' || !text) {
        return []
    }
    const segments: ReferenceSegment[] = []
    let last = 0
    for (const match of text.matchAll(LINK_TOKEN_RE)) {
        const index = match.index ?? 0
        if (index > last) {
            segments.push({ text: text.slice(last, index) })
        }
        const key = match[1] as string
        segments.push({ key, link: resolve(key) })
        last = index + match[0].length
    }
    if (last < text.length) {
        segments.push({ text: text.slice(last) })
    }
    return segments
}

/** A compact label for a URL: host and path, without scheme and trailing slash. */
export const shortUrl = (url: string): string => url.replace(/^https?:\/\/(www\.)?/i, '').replace(/\/$/, '')
