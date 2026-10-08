import { toValue, type MaybeRefOrGetter } from 'vue'
import { useI18n } from 'vue-i18n'

type DateInput = Date | number | string

export type FileSizeUnitSystem = 'iec' | 'si'

export type FileSizeFormatOptions = {
    /** IEC uses powers of 1024 with KiB/MiB; SI uses powers of 1000 with kB/MB. */
    unitSystem?: FileSizeUnitSystem
    minimumFractionDigits?: number
    maximumFractionDigits?: number
}

export type LocaleFormatters = ReturnType<typeof createLocaleFormatters>

const fileSizePolicies = Object.freeze({
    iec: {
        base: 1024,
        units: Object.freeze(['B', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB', 'EiB'])
    },
    si: {
        base: 1000,
        units: Object.freeze(['B', 'kB', 'MB', 'GB', 'TB', 'PB', 'EB'])
    }
})

const calendarDataByLocale = new Map<string, boolean>()

/**
 * Whether this browser has the date names of a locale. Chrome reports Kazakh as supported yet
 * ships none of its calendar data, so Intl falls back to ICU's root patterns there: "2026 M10 8",
 * "Thu", "yesterday".
 */
export function hasCalendarData(locale: string): boolean {
    let present = calendarDataByLocale.get(locale)
    if (present === undefined) {
        present = !/^M\d+$/.test(new Intl.DateTimeFormat(locale, { month: 'long' }).format(new Date(2000, 9, 15)))
        calendarDataByLocale.set(locale, present)
    }
    return present
}

/**
 * A date written with digits only, day first ("08.10.2026 15:59"), for a locale whose date names
 * the browser lacks. It covers the fields the options ask for; a weekday becomes the day and month.
 */
const formatDigitsOnly = (locale: string, date: Date, options: Intl.DateTimeFormatOptions): string => {
    const parts = new Intl.DateTimeFormat(locale, {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hourCycle: 'h23',
        ...(options.timeZone ? { timeZone: options.timeZone } : {})
    }).formatToParts(date)
    const part = (type: Intl.DateTimeFormatPartTypes): string => parts.find((candidate) => candidate.type === type)?.value ?? ''

    const { dateStyle, timeStyle } = options
    const dayAndMonth = Boolean(dateStyle || options.day || options.month || options.weekday)
    const calendarDate = [dayAndMonth && part('day'), dayAndMonth && part('month'), Boolean(dateStyle || options.year) && part('year')]
    const withSeconds = Boolean((timeStyle && timeStyle !== 'short') || options.second)
    const time = timeStyle || options.hour || options.minute ? [part('hour'), part('minute'), withSeconds && part('second')] : []

    return [calendarDate.filter(Boolean).join('.'), time.filter(Boolean).join(':')].filter(Boolean).join(' ')
}

/**
 * Create display-only formatters that read the active locale for every call.
 *
 * Keep API timestamps, stored numbers, protocol values and other machine
 * serialization in their original standard forms; these helpers are only for
 * localized, user-visible output.
 */
export function createLocaleFormatters(localeSource: MaybeRefOrGetter<string>) {
    const activeLocale = (): string => toValue(localeSource) || 'en'

    const formatNumber = (value: number | bigint, options?: Intl.NumberFormatOptions): string =>
        new Intl.NumberFormat(activeLocale(), options).format(value)

    const formatDateValue = (value: DateInput, options: Intl.DateTimeFormatOptions): string => {
        const date = value instanceof Date ? value : new Date(value)
        if (Number.isNaN(date.getTime())) return ''
        const locale = activeLocale()
        return hasCalendarData(locale) ? new Intl.DateTimeFormat(locale, options).format(date) : formatDigitsOnly(locale, date, options)
    }

    const parseCalendarDate = (value: DateInput): DateInput => {
        if (typeof value !== 'string') return value
        const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value)
        if (!match) return value

        const [, yearPart, monthPart, dayPart] = match
        const year = Number(yearPart)
        const month = Number(monthPart)
        const day = Number(dayPart)
        const date = new Date(0)
        date.setHours(0, 0, 0, 0)
        date.setFullYear(year, month - 1, day)

        return date.getFullYear() === year && date.getMonth() === month - 1 && date.getDate() === day ? date : Number.NaN
    }

    const formatDate = (value: DateInput, options: Intl.DateTimeFormatOptions = { dateStyle: 'medium' }): string =>
        formatDateValue(parseCalendarDate(value), options)

    const formatTime = (value: DateInput, options: Intl.DateTimeFormatOptions = { timeStyle: 'short' }): string =>
        formatDateValue(value, options)

    const formatDateTime = (value: DateInput, options: Intl.DateTimeFormatOptions = { dateStyle: 'medium', timeStyle: 'short' }): string =>
        formatDateValue(value, options)

    const formatList = (values: Iterable<string>, options?: Intl.ListFormatOptions): string =>
        new Intl.ListFormat(activeLocale(), options).format(values)

    const formatFileSize = (bytes: number | null | undefined, options: FileSizeFormatOptions = {}): string => {
        const unitSystem = options.unitSystem ?? 'iec'
        const policy = fileSizePolicies[unitSystem]
        const safeBytes = typeof bytes === 'number' && Number.isFinite(bytes) && bytes > 0 ? bytes : 0
        const unitIndex = safeBytes === 0 ? 0 : Math.min(Math.floor(Math.log(safeBytes) / Math.log(policy.base)), policy.units.length - 1)
        const value = safeBytes / policy.base ** unitIndex
        const formattedValue = formatNumber(value, {
            minimumFractionDigits: options.minimumFractionDigits ?? 0,
            maximumFractionDigits: options.maximumFractionDigits ?? 2
        })

        return `${formattedValue} ${policy.units[unitIndex]}`
    }

    return {
        formatNumber,
        formatDate,
        formatTime,
        formatDateTime,
        formatList,
        formatFileSize
    }
}

/** Use display formatters backed by the current Vue I18n application locale. */
export function useLocaleFormatters(): LocaleFormatters {
    const { locale } = useI18n()
    return createLocaleFormatters(locale)
}
