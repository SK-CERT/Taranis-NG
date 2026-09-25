import { ref } from 'vue'
import { describe, expect, it } from 'vitest'
import { createLocaleFormatters } from '@/composables/useLocaleFormatters'

describe('active-locale display formatters', () => {
    it('uses the app locale rather than the browser locale and follows runtime changes', () => {
        const appLocale = ref('de-DE')
        const { formatNumber } = createLocaleFormatters(appLocale)
        const value = 1234567.89

        expect(appLocale.value).not.toBe(navigator.language)
        expect(formatNumber(value)).toBe(new Intl.NumberFormat('de-DE').format(value))
        expect(formatNumber(value)).not.toBe(new Intl.NumberFormat(navigator.language).format(value))

        appLocale.value = 'fr-FR'
        expect(formatNumber(value)).toBe(new Intl.NumberFormat('fr-FR').format(value))
    })

    it('formats dates and times with explicit active-locale policies', () => {
        const { formatDate, formatTime, formatDateTime } = createLocaleFormatters('cs-CZ')
        const value = new Date('2026-08-09T17:30:00.000Z')
        const dateOptions: Intl.DateTimeFormatOptions = { dateStyle: 'long', timeZone: 'UTC' }
        const timeOptions: Intl.DateTimeFormatOptions = { timeStyle: 'short', timeZone: 'UTC' }
        const dateTimeOptions: Intl.DateTimeFormatOptions = { dateStyle: 'long', timeStyle: 'short', timeZone: 'UTC' }

        expect(formatDate(value, dateOptions)).toBe(new Intl.DateTimeFormat('cs-CZ', dateOptions).format(value))
        expect(formatTime(value, timeOptions)).toBe(new Intl.DateTimeFormat('cs-CZ', timeOptions).format(value))
        expect(formatDateTime(value, dateTimeOptions)).toBe(new Intl.DateTimeFormat('cs-CZ', dateTimeOptions).format(value))
        expect(formatDate('not-a-date')).toBe('')
    })

    it('keeps date-only values on their local calendar day without changing datetime instant parsing', () => {
        const originalTimeZone = process.env['TZ']
        process.env['TZ'] = 'America/Los_Angeles'
        try {
            const { formatDate, formatDateTime } = createLocaleFormatters('en-US')
            const dateOptions: Intl.DateTimeFormatOptions = { dateStyle: 'medium' }
            const dateTimeOptions: Intl.DateTimeFormatOptions = { dateStyle: 'medium', timeStyle: 'short' }
            const instant = '2024-01-15T00:00:00Z'

            expect(formatDate('2024-01-15')).toBe(new Intl.DateTimeFormat('en-US', dateOptions).format(new Date(2024, 0, 15)))
            expect(formatDate('2024-02-31')).toBe('')
            expect(formatDateTime(instant)).toBe(new Intl.DateTimeFormat('en-US', dateTimeOptions).format(new Date(instant)))
        } finally {
            if (originalTimeZone === undefined) {
                delete process.env['TZ']
            } else {
                process.env['TZ'] = originalTimeZone
            }
        }
    })

    it('formats human-readable lists according to the active locale', () => {
        const appLocale = ref('en-US')
        const { formatList } = createLocaleFormatters(appLocale)
        const values = ['Alpha', 'Beta', 'Gamma']
        const options: Intl.ListFormatOptions = { style: 'long', type: 'conjunction' }

        expect(formatList(values, options)).toBe(new Intl.ListFormat('en-US', options).format(values))
        appLocale.value = 'es-ES'
        expect(formatList(values, options)).toBe(new Intl.ListFormat('es-ES', options).format(values))
    })

    it('formats 0, 1 and large file sizes with the documented IEC default', () => {
        const { formatFileSize } = createLocaleFormatters('de-DE')
        const localizedOneAndHalf = new Intl.NumberFormat('de-DE', {
            minimumFractionDigits: 0,
            maximumFractionDigits: 2
        }).format(1.5)

        expect(formatFileSize(0)).toBe('0 B')
        expect(formatFileSize(1)).toBe('1 B')
        expect(formatFileSize(1536)).toBe(`${localizedOneAndHalf} KiB`)
        expect(formatFileSize(5 * 1024 ** 3)).toBe('5 GiB')
        expect(formatFileSize(-1)).toBe('0 B')
    })

    it('supports explicit SI file-size units without changing the source value', () => {
        const { formatFileSize } = createLocaleFormatters('en-US')
        const bytes = 1_500_000

        expect(formatFileSize(bytes, { unitSystem: 'si' })).toBe('1.5 MB')
        expect(bytes).toBe(1_500_000)
    })
})
