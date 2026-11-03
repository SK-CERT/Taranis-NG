/** Render an API instant as a browser-local datetime-local input value. */
export function toLocalDateTime(value: string | null | undefined): string {
    if (!value) return ''
    // Legacy/default wall times without a timezone have the API's UTC meaning.
    const instant = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(value) ? value : `${value}Z`
    const date = new Date(instant)
    if (Number.isNaN(date.getTime())) return ''
    const pad = (part: number, width = 2): string => String(part).padStart(width, '0')
    return `${pad(date.getFullYear(), 4)}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}.${pad(date.getMilliseconds(), 3)}`
}

/** Store a datetime-local edit as a UTC API instant; clearing the field stays empty. */
export function fromLocalDateTime(value: string | null | undefined): string {
    if (!value) return ''
    const date = new Date(value)
    return Number.isNaN(date.getTime()) ? '' : date.toISOString()
}
