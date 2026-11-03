import { describe, expect, it } from 'vitest'
import { execFileSync } from 'node:child_process'
import { resolve } from 'node:path'
import { fromLocalDateTime, toLocalDateTime } from '@/utils/dateTime'
import { createLocaleFormatters } from '@/composables/useLocaleFormatters'

describe('UTC API timestamps and local datetime inputs', () => {
    it.each(['UTC', 'Europe/Bratislava', 'America/Los_Angeles'])('round trips instants in %s', (timeZone) => {
        const originalTimeZone = process.env['TZ']
        process.env['TZ'] = timeZone
        try {
            // Midnight crossing, winter/summer offsets and both sides of DST transitions.
            for (const instant of [
                '2026-01-14T23:30:00.123Z',
                '2026-07-14T23:30:00.456Z',
                '2026-03-29T00:30:00.000Z',
                '2026-03-29T01:30:00.000Z',
                '2026-10-25T00:30:00.000Z',
                '2026-10-25T02:30:00.000Z'
            ]) {
                const input = toLocalDateTime(instant)
                const date = new Date(instant)
                expect(input.slice(11, 13)).toBe(String(date.getHours()).padStart(2, '0'))
                expect(fromLocalDateTime(input)).toBe(instant)
                const { formatDateTime } = createLocaleFormatters('en-US')
                expect(formatDateTime(instant)).toBe(
                    new Intl.DateTimeFormat('en-US', { dateStyle: 'medium', timeStyle: 'short' }).format(date)
                )
            }
        } finally {
            if (originalTimeZone === undefined) delete process.env['TZ']
            else process.env['TZ'] = originalTimeZone
        }
    })

    it.each([
        ['UTC', '2026-07-14T23:30:00.123'],
        ['Europe/Bratislava', '2026-07-15T01:30:00.123'],
        ['America/Los_Angeles', '2026-07-14T16:30:00.123']
    ])('converts actual local fields in a %s process', (timeZone, expected) => {
        const helperPath = resolve(import.meta.dirname, '../../src/utils/dateTime.ts')
        const result = execFileSync(
            process.execPath,
            [
                '--input-type=module',
                '--eval',
                `import { fromLocalDateTime, toLocalDateTime } from ${JSON.stringify(helperPath)};
                 const local = toLocalDateTime('2026-07-14T23:30:00.123Z');
                 process.stdout.write(JSON.stringify([local, fromLocalDateTime(local)]));`
            ],
            { env: { ...process.env, TZ: timeZone }, encoding: 'utf8' }
        )
        expect(JSON.parse(result)).toEqual([expected, '2026-07-14T23:30:00.123Z'])
    })

    it('honors explicit API offsets and treats legacy timezone-free API values as UTC', () => {
        expect(toLocalDateTime('2026-07-15T10:30:00+02:00')).toBe(toLocalDateTime('2026-07-15T08:30:00Z'))
        expect(toLocalDateTime('2026-07-15T08:30:00')).toBe(toLocalDateTime('2026-07-15T08:30:00Z'))
    })

    it('keeps empty and invalid input empty', () => {
        for (const value of [null, undefined, '', 'not-a-date']) {
            expect(toLocalDateTime(value)).toBe('')
            expect(fromLocalDateTime(value)).toBe('')
        }
    })
})
