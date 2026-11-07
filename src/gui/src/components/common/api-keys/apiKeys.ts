/** Types and helpers shared by the API key table, dialogs and panels. */

export type ApiKeyPermission = {
    id: string
    name?: string
    description?: string | null
}

export type ApiKeyOwner = {
    id: number
    username: string
    name?: string | null
    status?: string
}

export type ApiKeyItem = {
    id: number
    name: string
    description: string
    key_prefix: string
    user: ApiKeyOwner | null
    user_id: number
    created_at: string | null
    created_by: string | null
    expires_at: string | null
    expired: boolean
    enabled: boolean
    restricted: boolean
    permissions: ApiKeyPermission[]
    allowed_ips: string[]
    last_used_at: string | null
    last_used_ip: string | null
}

export type ApiKeyPolicy = {
    require_expiry: boolean
    max_days: number | null
    require_allowlist: boolean
    site_allowlist_active: boolean
}

export type ApiKeyListResponse = {
    total_count: number
    items: ApiKeyItem[]
    policy: ApiKeyPolicy
    client_ip: string | null
    /** Whether the caller's address is public, so it may go on an allowlist. */
    client_ip_public?: boolean
    available_permissions?: ApiKeyPermission[]
    owners?: ApiKeyOwner[]
}

/** What the create and update endpoints accept. */
export type ApiKeyPayload = {
    user_id?: number
    name?: string
    description?: string
    expires_at?: string | null
    enabled?: boolean
    restricted?: boolean
    permissions?: string[]
    allowed_ips?: string[]
}

export type ApiKeySaved = { item: ApiKeyItem; key?: string }

export type ApiKeyStatus = 'active' | 'disabled' | 'expired'

export const DEFAULT_POLICY: ApiKeyPolicy = {
    require_expiry: false,
    max_days: null,
    require_allowlist: false,
    site_allowlist_active: false
}

/** Days a key may have left before the table warns that it expires soon. */
export const EXPIRING_SOON_DAYS = 14
/** The expiry presets, in days; each has its own fixed label (``api_keys.expiry_<days>``). */
export const EXPIRY_PRESETS = [30, 90, 180, 365] as const
export const DEFAULT_EXPIRY_DAYS = 90

const DAY_MS = 24 * 60 * 60 * 1000

export const apiKeyStatus = (item: Pick<ApiKeyItem, 'enabled' | 'expired' | 'expires_at'>, now = Date.now()): ApiKeyStatus => {
    if (item.expired || (item.expires_at && Date.parse(item.expires_at) <= now)) return 'expired'
    return item.enabled ? 'active' : 'disabled'
}

export const expiresSoon = (item: Pick<ApiKeyItem, 'expires_at'>, now = Date.now()): boolean => {
    if (!item.expires_at) return false
    const left = Date.parse(item.expires_at) - now
    return left > 0 && left <= EXPIRING_SOON_DAYS * DAY_MS
}

/** ``days`` days from ``now``, as the ISO string the API takes. */
export const expiryInDays = (days: number, now = Date.now()): string => new Date(now + days * DAY_MS).toISOString()

/** The end of a picked day (``YYYY-MM-DD``) in the browser's zone, as an ISO string. */
export const expiryAtEndOfDay = (date: string): string | null => {
    const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(date)
    if (!match) return null
    const end = new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]), 23, 59, 59)
    return Number.isNaN(end.getTime()) ? null : end.toISOString()
}

/** A date as the ``YYYY-MM-DD`` an ``<input type="date">`` reads, in the browser's zone. */
export const toDateInput = (time: number): string => {
    const date = new Date(time)
    const pad = (value: number): string => String(value).padStart(2, '0')
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
}

export const dateInDays = (days: number, now = Date.now()): string => toDateInput(now + days * DAY_MS)

/** The entries of an allowlist textarea: one per line, commas and blanks also separate. */
export const parseAllowlist = (text: string | null | undefined): string[] =>
    (text || '')
        .split(/[\s,;]+/u)
        .map((entry) => entry.trim())
        .filter((entry) => entry.length > 0)

const IPV4 = /^(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}$/u

const isIpv6 = (address: string): boolean => {
    if (!address.includes(':') || !/^[0-9a-fA-F:.]+$/u.test(address)) return false
    try {
        // The URL parser implements the IPv6 address grammar, embedded IPv4 included.
        new URL(`http://[${address}]/`)
        return true
    } catch {
        return false
    }
}

/** Whether an entry is an IPv4/IPv6 address or CIDR range (the server checks again). */
export const isIpOrCidr = (entry: string): boolean => {
    const [address, prefix, extra] = entry.split('/')
    if (extra !== undefined || !address) return false
    const v4 = IPV4.test(address)
    if (!v4 && !isIpv6(address)) return false
    if (prefix === undefined) return true
    if (!/^\d{1,3}$/u.test(prefix)) return false
    return Number(prefix) <= (v4 ? 32 : 128)
}

export const invalidAllowlistEntries = (text: string | null | undefined): string[] =>
    parseAllowlist(text).filter((entry) => !isIpOrCidr(entry))

// Only public addresses may be listed. These lists repeat the server's (core
// managers/ip_allowlist.py, SPECIAL_IPV4 / GLOBAL_UNICAST_IPV6 / SPECIAL_IPV6); keep them in step.
// 240.0.0.0/4 includes the limited broadcast address 255.255.255.255.
const SPECIAL_IPV4 = [
    '0.0.0.0/8',
    '10.0.0.0/8',
    '100.64.0.0/10',
    '127.0.0.0/8',
    '169.254.0.0/16',
    '172.16.0.0/12',
    '192.0.0.0/24',
    '192.0.2.0/24',
    '192.88.99.0/24',
    '192.168.0.0/16',
    '198.18.0.0/15',
    '198.51.100.0/24',
    '203.0.113.0/24',
    '224.0.0.0/4',
    '240.0.0.0/4'
]
const GLOBAL_UNICAST_IPV6 = '2000::/3'
const SPECIAL_IPV6 = ['2001::/23', '2001:db8::/32', '2002::/16', '3fff::/20']

type Range = { start: bigint; end: bigint }

const ipv4Value = (address: string): bigint => address.split('.').reduce((value, octet) => (value << 8n) + BigInt(Number(octet)), 0n)

/** The 128-bit value of an IPv6 address, or null; an embedded IPv4 tail is allowed. */
const ipv6Value = (address: string): bigint | null => {
    let text = address.toLowerCase()
    const tail = /(\d{1,3}(?:\.\d{1,3}){3})$/u.exec(text)?.[1]
    if (tail) {
        if (!IPV4.test(tail)) return null
        const value = ipv4Value(tail)
        text = `${text.slice(0, -tail.length)}${(value >> 16n).toString(16)}:${(value & 0xffffn).toString(16)}`
    }
    const halves = text.split('::')
    if (halves.length > 2) return null
    const head = halves[0] ? halves[0].split(':') : []
    const rest = halves.length === 2 && halves[1] ? halves[1].split(':') : []
    const zeros = halves.length === 2 ? 8 - head.length - rest.length : 0
    if (zeros < 0 || (halves.length === 2 && zeros < 1)) return null
    const groups = [...head, ...Array<string>(zeros).fill('0'), ...rest]
    if (groups.length !== 8 || groups.some((group) => !/^[0-9a-f]{1,4}$/u.test(group))) return null
    return groups.reduce((value, group) => (value << 16n) + BigInt(parseInt(group, 16)), 0n)
}

/** The first and last address of a range; IPv4-mapped IPv6 (::ffff:a.b.c.d) counts as IPv4. */
const rangeOf = (entry: string): { version: 4 | 6; range: Range } | null => {
    if (!isIpOrCidr(entry)) return null
    const [address = '', prefixText] = entry.split('/')
    const v4 = IPV4.test(address)
    let version: 4 | 6 = v4 ? 4 : 6
    let bits = v4 ? 32 : 128
    let value = v4 ? ipv4Value(address) : ipv6Value(address)
    if (value === null) return null
    let prefix = prefixText === undefined ? bits : Number(prefixText)
    if (!v4 && value >> 32n === 0xffffn && prefix >= 96) {
        version = 4
        bits = 32
        value &= 0xffffffffn
        prefix -= 96
    }
    const size = 1n << BigInt(bits - prefix)
    const start = (value / size) * size
    return { version, range: { start, end: start + size - 1n } }
}

const toRange = (network: string): Range => (rangeOf(network) as { range: Range }).range
const SPECIAL_IPV4_RANGES = SPECIAL_IPV4.map(toRange)
const GLOBAL_UNICAST_IPV6_RANGE = toRange(GLOBAL_UNICAST_IPV6)
const SPECIAL_IPV6_RANGES = SPECIAL_IPV6.map(toRange)
const overlaps = (a: Range, b: Range): boolean => a.start <= b.end && b.start <= a.end

/** Whether a valid entry is wholly public: routable, and touching no special-purpose range. */
export const isPublicIpOrCidr = (entry: string): boolean => {
    const parsed = rangeOf(entry)
    if (!parsed) return false
    const { version, range } = parsed
    if (version === 4) return !SPECIAL_IPV4_RANGES.some((special) => overlaps(range, special))
    const inGlobalUnicast = range.start >= GLOBAL_UNICAST_IPV6_RANGE.start && range.end <= GLOBAL_UNICAST_IPV6_RANGE.end
    return inGlobalUnicast && !SPECIAL_IPV6_RANGES.some((special) => overlaps(range, special))
}

/** Valid entries that are not public (private, loopback, multicast, broadcast, documentation, ...). */
export const nonPublicAllowlistEntries = (text: string | null | undefined): string[] =>
    parseAllowlist(text).filter((entry) => isIpOrCidr(entry) && !isPublicIpOrCidr(entry))

/** The message of an API error, when core sent one. */
export const apiErrorMessage = (error: unknown): string | undefined =>
    (error as { response?: { data?: { error?: string } } } | null)?.response?.data?.error
