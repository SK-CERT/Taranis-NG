import { describe, expect, it } from 'vitest'
import {
    apiKeyStatus,
    expiresSoon,
    expiryAtEndOfDay,
    expiryInDays,
    invalidAllowlistEntries,
    isIpOrCidr,
    isPublicIpOrCidr,
    nonPublicAllowlistEntries,
    parseAllowlist,
    toDateInput
} from '@/components/common/api-keys/apiKeys'

const NOW = Date.parse('2026-11-07T12:00:00Z')
const DAY = 24 * 60 * 60 * 1000

describe('API key helpers', () => {
    it.each(['10.0.0.0/8', '192.0.2.7', '0.0.0.0/0', '2001:db8::/32', '::1', '::ffff:192.0.2.7', 'fe80::1/64', '2001:DB8::1/128'])(
        'accepts %s as an address or CIDR range',
        (entry) => {
            expect(isIpOrCidr(entry)).toBe(true)
        }
    )

    it.each(['example.com', '10.0.0.0/33', '256.1.1.1', '10.0.0', '10.0.0.0/8/8', '2001:db8::/129', 'fe80::1%eth0', ':::', '*', '10.0.0.0/'])(
        'refuses %s',
        (entry) => {
            expect(isIpOrCidr(entry)).toBe(false)
        }
    )

    it.each(['185.10.20.0/24', '8.8.8.8', '2a01:4f8::/32', '2001:4860:4860::8888', '::ffff:8.8.8.8', '::ffff:185.10.0.0/112'])(
        'accepts the public %s',
        (entry) => {
            expect(isPublicIpOrCidr(entry)).toBe(true)
        }
    )

    it.each([
        '10.0.0.0/8',
        '172.16.5.4',
        '192.168.1.0/24',
        '100.64.0.1',
        '127.0.0.1',
        '169.254.10.10',
        '0.0.0.0/0',
        '8.0.0.0/5',
        '224.0.0.1',
        '255.255.255.255',
        '240.0.0.1',
        '192.0.2.7',
        '198.51.100.0/24',
        '203.0.113.9',
        '198.18.0.1',
        '::',
        '::/0',
        '::1',
        'fe80::1',
        'fc00::/7',
        'fd12:3456::1',
        'ff02::1',
        '2001:db8::/32',
        '3fff::1',
        '2001::1',
        '2002:c000:204::1',
        '4000::1',
        '::ffff:10.0.0.1'
    ])('refuses %s, which is not public (as the server does)', (entry) => {
        expect(isPublicIpOrCidr(entry)).toBe(false)
    })

    it('lists the valid entries that are not public, leaving malformed ones to the syntax check', () => {
        expect(nonPublicAllowlistEntries('185.10.20.0/24\n10.0.0.0/8\nnope\n::1')).toEqual(['10.0.0.0/8', '::1'])
    })

    it('reads a textarea as entries separated by lines, commas or blanks', () => {
        expect(parseAllowlist('10.0.0.0/8\n\n 192.0.2.7 , 2001:db8::/32;')).toEqual(['10.0.0.0/8', '192.0.2.7', '2001:db8::/32'])
        expect(parseAllowlist(null)).toEqual([])
        expect(invalidAllowlistEntries('10.0.0.0/8\nnope\n300.0.0.1')).toEqual(['nope', '300.0.0.1'])
    })

    it('tells active, disabled and expired keys apart, expiry first', () => {
        const future = new Date(NOW + DAY).toISOString()
        const past = new Date(NOW - 1).toISOString()

        expect(apiKeyStatus({ enabled: true, expired: false, expires_at: null }, NOW)).toBe('active')
        expect(apiKeyStatus({ enabled: false, expired: false, expires_at: future }, NOW)).toBe('disabled')
        expect(apiKeyStatus({ enabled: true, expired: false, expires_at: past }, NOW)).toBe('expired')
        expect(apiKeyStatus({ enabled: false, expired: true, expires_at: past }, NOW)).toBe('expired')
    })

    it('warns about keys with two weeks or less left', () => {
        expect(expiresSoon({ expires_at: new Date(NOW + 14 * DAY).toISOString() }, NOW)).toBe(true)
        expect(expiresSoon({ expires_at: new Date(NOW + 15 * DAY).toISOString() }, NOW)).toBe(false)
        expect(expiresSoon({ expires_at: new Date(NOW - DAY).toISOString() }, NOW)).toBe(false)
        expect(expiresSoon({ expires_at: null }, NOW)).toBe(false)
    })

    it('turns presets and picked days into the ISO expiries the API takes', () => {
        expect(expiryInDays(90, NOW)).toBe(new Date(NOW + 90 * DAY).toISOString())
        const endOfDay = new Date(expiryAtEndOfDay('2027-02-05') as string)
        expect([endOfDay.getFullYear(), endOfDay.getMonth(), endOfDay.getDate(), endOfDay.getHours(), endOfDay.getMinutes()]).toEqual([
            2027, 1, 5, 23, 59
        ])
        expect(expiryAtEndOfDay('next week')).toBeNull()
        expect(toDateInput(new Date(2027, 0, 9, 8).getTime())).toBe('2027-01-09')
    })
})
