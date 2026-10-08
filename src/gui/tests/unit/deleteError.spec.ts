import { afterEach, describe, expect, it, vi } from 'vitest'
import { AxiosError, AxiosHeaders } from 'axios'
import { deleteErrorLoc, isServerUnreachable, notifyDeleteError } from '@/utils/deleteError'

const answered = (status: number): AxiosError =>
    new AxiosError(
        `Request failed with status code ${status}`,
        'ERR_BAD_RESPONSE',
        undefined,
        {},
        {
            status,
            statusText: '',
            data: {},
            headers: {},
            config: { headers: new AxiosHeaders() }
        }
    )

// What axios rejects with when the request never got an answer: no `response` at all.
const networkError = (): AxiosError => new AxiosError('Network Error', AxiosError.ERR_NETWORK, undefined, {})

describe('isServerUnreachable', () => {
    it('counts a request that got no answer at all', () => {
        expect(isServerUnreachable(networkError())).toBe(true)
        expect(isServerUnreachable(new AxiosError('timeout of 30000ms exceeded', AxiosError.ECONNABORTED, undefined, {}))).toBe(true)
    })

    it('counts the proxy answering for a core that is down', () => {
        for (const status of [502, 503, 504]) expect(isServerUnreachable(answered(status))).toBe(true)
    })

    it('does not count an answer from core, or a bug on this side', () => {
        for (const status of [400, 403, 409, 500]) expect(isServerUnreachable(answered(status))).toBe(false)
        expect(isServerUnreachable(new TypeError('x is undefined'))).toBe(false)
        expect(isServerUnreachable(undefined)).toBe(false)
    })
})

describe('deleteErrorLoc', () => {
    it('does not call an unreachable server "in use" (SK-CERT#527)', () => {
        const locs = { inUse: 'collectors.sources.removed_error' }
        expect(deleteErrorLoc(networkError(), locs)).toBe('error.server_unreachable')
        expect(deleteErrorLoc(answered(503), locs)).toBe('error.server_unreachable')
    })

    it('says "in use" only for the conflict core answers when records still reference the row', () => {
        expect(deleteErrorLoc(answered(409), { inUse: 'collectors.sources.removed_error' })).toBe('collectors.sources.removed_error')
        expect(deleteErrorLoc(answered(409))).toBe('error.in_use')
        // Mocks and wrappers that carry only the response are read the same way.
        expect(deleteErrorLoc({ response: { status: 409 } })).toBe('error.in_use')
    })

    it('falls back to the generic or the entity-specific failure for everything else', () => {
        expect(deleteErrorLoc(answered(400))).toBe('common.error_deleting')
        expect(deleteErrorLoc(answered(500), { failed: 'auth_provider.remove_error' })).toBe('auth_provider.remove_error')
        expect(deleteErrorLoc(new Error('boom'), { inUse: 'asset.removed_error' })).toBe('common.error_deleting')
    })
})

describe('notifyDeleteError', () => {
    afterEach(() => {
        vi.restoreAllMocks()
    })

    it('raises the error notification with the chosen message', () => {
        const dispatch = vi.spyOn(window, 'dispatchEvent')

        notifyDeleteError(answered(409), { inUse: 'word_lists.removed_error' })

        const event = dispatch.mock.calls[0]?.[0] as CustomEvent
        expect(event.type).toBe('notification')
        expect(event.detail).toEqual({ type: 'error', loc: 'word_lists.removed_error' })
    })
})
