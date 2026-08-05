import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { defineComponent } from 'vue'
import { mount } from '@vue/test-utils'
import { useSSE } from '@/composables/useSSE'

const { initSSE } = vi.hoisted(() => ({
    initSSE: vi.fn()
}))

vi.mock('@/api/auth', () => ({
    initSSE
}))

vi.mock('@/stores/auth', () => ({
    useAuthStore: () => ({})
}))

class MockEventSource {
    static instances = []

    constructor(url, options) {
        this.url = url
        this.options = options
        this.listeners = new Map()
        this.close = vi.fn()
        this.addEventListener = vi.fn((eventName, handler) => {
            this.listeners.set(eventName, handler)
        })
        this.removeEventListener = vi.fn((eventName, handler) => {
            const current = this.listeners.get(eventName)
            if (current === handler) {
                this.listeners.delete(eventName)
            }
        })
        this.onopen = null
        this.onerror = null

        MockEventSource.instances.push(this)
    }

    emit(eventName, data) {
        const handler = this.listeners.get(eventName)
        if (handler) {
            handler({ data })
        }
    }
}

function setupComposable() {
    let result
    const wrapper = mount(
        defineComponent({
            setup() {
                result = useSSE()
                return () => null
            }
        })
    )
    return { result, scope: { stop: () => wrapper.unmount() } }
}

async function flushMicrotasks() {
    await Promise.resolve()
}

describe('useSSE', () => {
    beforeEach(() => {
        vi.clearAllMocks()
        vi.unstubAllEnvs()
        initSSE.mockResolvedValue({})
        MockEventSource.instances = []
        global.EventSource = MockEventSource
    })

    afterEach(() => {
        delete global.EventSource
    })

    it('should initialize SSE and connect with credentials', async () => {
        vi.stubEnv('VITE_APP_TARANIS_NG_CORE_SSE', 'http://example.test/sse')
        const { result, scope } = setupComposable()

        const connectPromise = result.connect()
        await flushMicrotasks()

        expect(initSSE).toHaveBeenCalledTimes(1)
        expect(MockEventSource.instances).toHaveLength(1)
        expect(MockEventSource.instances[0].url).toBe('http://example.test/sse')
        expect(MockEventSource.instances[0].options).toEqual({ withCredentials: true })

        MockEventSource.instances[0].onopen()
        const connection = await connectPromise

        expect(connection).toBe(MockEventSource.instances[0])
        expect(result.sseConnection.value?.url).toBe(connection.url)
        expect(result.sseConnection.value?.options).toEqual(connection.options)
        scope.stop()
    })

    it('should replay queued subscriptions after connect and parse JSON payloads', async () => {
        const handler = vi.fn()
        const { result, scope } = setupComposable()

        result.subscribe('report-item-updated', handler)

        const connectPromise = result.connect()
        await flushMicrotasks()
        MockEventSource.instances[0].onopen()
        await connectPromise

        MockEventSource.instances[0].emit('report-item-updated', JSON.stringify({ report_item_id: 42, user_id: 7 }))

        expect(handler).toHaveBeenCalledWith({ report_item_id: 42, user_id: 7 })
        scope.stop()
    })

    it('should unsubscribe using the registered EventSource listener', async () => {
        const handler = vi.fn()
        const { result, scope } = setupComposable()

        result.subscribe('report-item-updated', handler)
        const connectPromise = result.connect()
        await flushMicrotasks()
        MockEventSource.instances[0].onopen()
        await connectPromise

        const connection = MockEventSource.instances[0]
        const registeredListener = connection.listeners.get('report-item-updated')

        result.unsubscribe('report-item-updated')

        expect(connection.removeEventListener).toHaveBeenCalledWith('report-item-updated', registeredListener)
        scope.stop()
    })

    it('should reconnect by closing the current connection and creating a new one', async () => {
        const { result, scope } = setupComposable()

        const firstConnect = result.connect()
        await flushMicrotasks()
        MockEventSource.instances[0].onopen()
        await firstConnect

        const firstConnection = MockEventSource.instances[0]
        const reconnectPromise = result.reconnect()
        await flushMicrotasks()

        expect(firstConnection.close).toHaveBeenCalledTimes(1)
        expect(initSSE).toHaveBeenCalledTimes(2)
        expect(MockEventSource.instances).toHaveLength(2)

        MockEventSource.instances[1].onopen()
        await reconnectPromise

        expect(result.sseConnection.value?.url).toBe(MockEventSource.instances[1].url)
        expect(result.sseConnection.value?.options).toEqual(MockEventSource.instances[1].options)
        scope.stop()
    })

    describe('recovery after a dropped stream', () => {
        // Mirrors RECONNECT_IDLE_DELAY in the composable: the slow rate it falls back to
        // once retries have failed repeatedly.
        const RECONNECT_IDLE_DELAY = 300000

        beforeEach(() => {
            vi.useFakeTimers()
        })

        afterEach(() => {
            vi.useRealTimers()
        })

        it('should retry automatically after a connection error', async () => {
            const { result, scope } = setupComposable()

            const connectPromise = result.connect()
            await flushMicrotasks()
            MockEventSource.instances[0].onopen()
            await connectPromise

            MockEventSource.instances[0].onerror(new Event('error'))
            expect(result.sseConnection.value).toBeNull()

            await vi.advanceTimersByTimeAsync(1000)
            await flushMicrotasks()

            expect(MockEventSource.instances).toHaveLength(2)
            scope.stop()
        })

        it('should notify resync handlers once the stream is back, since events are not replayed', async () => {
            const { result, scope } = setupComposable()
            const onResync = vi.fn()
            result.onResync(onResync)

            const connectPromise = result.connect()
            await flushMicrotasks()
            MockEventSource.instances[0].onopen()
            await connectPromise

            // A first connect has nothing to catch up on.
            expect(onResync).not.toHaveBeenCalled()

            MockEventSource.instances[0].onerror(new Event('error'))
            await vi.advanceTimersByTimeAsync(1000)
            await flushMicrotasks()
            MockEventSource.instances[1].onopen()
            await flushMicrotasks()

            expect(onResync).toHaveBeenCalledTimes(1)
            scope.stop()
        })

        it('should re-register subscriptions on the new connection', async () => {
            const { result, scope } = setupComposable()
            const handler = vi.fn()
            result.subscribe('report-item-updated', handler)

            const connectPromise = result.connect()
            await flushMicrotasks()
            MockEventSource.instances[0].onopen()
            await connectPromise

            MockEventSource.instances[0].onerror(new Event('error'))
            await vi.advanceTimersByTimeAsync(1000)
            await flushMicrotasks()
            MockEventSource.instances[1].onopen()
            await flushMicrotasks()

            MockEventSource.instances[1].emit('report-item-updated', JSON.stringify({ report_item_id: 1 }))
            expect(handler).toHaveBeenCalledWith({ report_item_id: 1 })
            scope.stop()
        })

        it('should not retry when the stream session is refused as unauthenticated', async () => {
            for (const status of [401, 403]) {
                MockEventSource.instances = []
                initSSE.mockRejectedValueOnce({ response: { status } })
                const { result, scope } = setupComposable()

                await expect(result.connect()).rejects.toBeDefined()

                // Retrying cannot produce a token, so nothing further may be attempted.
                await vi.advanceTimersByTimeAsync(120000)
                expect(initSSE).toHaveBeenCalledTimes(1)
                expect(MockEventSource.instances).toHaveLength(0)

                scope.stop()
                initSSE.mockClear()
                initSSE.mockResolvedValue({})
            }
        })

        it('should keep retrying a transient stream session failure', async () => {
            initSSE.mockRejectedValueOnce(new Error('network down'))
            const { result, scope } = setupComposable()

            await expect(result.connect()).rejects.toBeDefined()

            await vi.advanceTimersByTimeAsync(1000)
            expect(initSSE).toHaveBeenCalledTimes(2)
            scope.stop()
        })

        it('should back off to a slow retry once failures pile up', async () => {
            initSSE.mockRejectedValue(new Error('network down'))
            const { result, scope } = setupComposable()

            await expect(result.connect()).rejects.toBeDefined()

            // Walk through the exponential phase (1s, 2s, 4s ... capped at 30s).
            await vi.advanceTimersByTimeAsync(10 * 30000)
            const afterBurst = initSSE.mock.calls.length

            // Once slowed down, half an idle delay must not trigger anything further.
            await vi.advanceTimersByTimeAsync(RECONNECT_IDLE_DELAY / 2)
            expect(initSSE).toHaveBeenCalledTimes(afterBurst)

            await vi.advanceTimersByTimeAsync(RECONNECT_IDLE_DELAY)
            expect(initSSE.mock.calls.length).toBeGreaterThan(afterBurst)

            scope.stop()
            initSSE.mockReset()
            initSSE.mockResolvedValue({})
        })

        it('should stop retrying after an explicit disconnect', async () => {
            const { result, scope } = setupComposable()

            const connectPromise = result.connect()
            await flushMicrotasks()
            MockEventSource.instances[0].onopen()
            await connectPromise

            MockEventSource.instances[0].onerror(new Event('error'))
            result.disconnect()

            await vi.advanceTimersByTimeAsync(60000)
            await flushMicrotasks()

            expect(MockEventSource.instances).toHaveLength(1)
            scope.stop()
        })
    })
})
