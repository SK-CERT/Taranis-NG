import { defineComponent, h } from 'vue'
import { mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { useSseResync } from '@/composables/useSseResync'

const deferred = () => {
    let resolve!: () => void
    const promise = new Promise<void>((done) => {
        resolve = done
    })
    return { promise, resolve }
}

const mountConsumer = (handler: () => void | Promise<void>) =>
    mount(
        defineComponent({
            setup() {
                useSseResync(handler)
                return () => h('div')
            }
        })
    )

describe('useSseResync', () => {
    afterEach(() => {
        vi.useRealTimers()
    })

    it('coalesces a burst and removes its listener on unmount', async () => {
        vi.useFakeTimers()
        const handler = vi.fn()
        const wrapper = mountConsumer(handler)

        window.dispatchEvent(new CustomEvent('sse-resync'))
        window.dispatchEvent(new CustomEvent('sse-resync'))
        window.dispatchEvent(new CustomEvent('sse-resync'))
        await vi.advanceTimersByTimeAsync(100)

        expect(handler).toHaveBeenCalledTimes(1)

        wrapper.unmount()
        window.dispatchEvent(new CustomEvent('sse-resync'))
        await vi.advanceTimersByTimeAsync(100)
        expect(handler).toHaveBeenCalledTimes(1)
    })

    it('serializes refreshes and collapses signals received while one is running', async () => {
        vi.useFakeTimers()
        const first = deferred()
        const handler = vi.fn().mockReturnValueOnce(first.promise).mockResolvedValue(undefined)
        const wrapper = mountConsumer(handler)

        window.dispatchEvent(new CustomEvent('sse-resync'))
        await vi.advanceTimersByTimeAsync(100)
        expect(handler).toHaveBeenCalledTimes(1)

        window.dispatchEvent(new CustomEvent('sse-resync'))
        window.dispatchEvent(new CustomEvent('sse-resync'))
        first.resolve()
        await Promise.resolve()
        await Promise.resolve()

        expect(handler).toHaveBeenCalledTimes(2)
        wrapper.unmount()
    })

    it('does not run a trailing refresh after its consumer unmounts', async () => {
        vi.useFakeTimers()
        const first = deferred()
        const handler = vi.fn().mockReturnValue(first.promise)
        const wrapper = mountConsumer(handler)

        window.dispatchEvent(new CustomEvent('sse-resync'))
        await vi.advanceTimersByTimeAsync(100)
        window.dispatchEvent(new CustomEvent('sse-resync'))
        wrapper.unmount()
        first.resolve()
        await Promise.resolve()
        await Promise.resolve()

        expect(handler).toHaveBeenCalledTimes(1)
    })
})
