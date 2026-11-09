import { describe, expect, it } from 'vitest'
import { isSecretParameter, storedSecretKeys } from '@/utils/secretParameters'

// Core sends a stored credential empty with value_set, and keeps it when it is saved empty.
describe('secret parameters', () => {
    it.each([
        ['EMAIL_PASSWORD', true],
        ['PASSWORD', true],
        ['SSH_KEY', true],
        ['MISP_API_KEY', true],
        ['MASTODON_ACCESS_TOKEN', true],
        ['TWITTER_API_KEY_SECRET', true],
        ['FEED_URL', false],
        ['SEARCH_KEYWORDS', false],
        [undefined, false]
    ])('%s is a credential: %s', (key, secret) => {
        expect(isSecretParameter(key)).toBe(secret)
    })

    it('lists the credentials that have a stored value', () => {
        const keys = storedSecretKeys([
            { value_set: true, parameter: { key: 'EMAIL_PASSWORD' } },
            { value_set: false, parameter: { key: 'SSH_KEY' } },
            { value_set: true, parameter: { key: 'FEED_URL' } },
            { parameter: null }
        ])

        expect([...keys]).toEqual(['EMAIL_PASSWORD'])
        expect(storedSecretKeys(undefined).size).toBe(0)
    })
})
