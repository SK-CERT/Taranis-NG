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
        return new Intl.DateTimeFormat(activeLocale(), options).format(date)
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
