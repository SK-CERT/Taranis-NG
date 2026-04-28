import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { effectScope } from 'vue'
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
  const scope = effectScope()
  scope.run(() => {
    result = useSSE()
  })
  return { result, scope }
}

async function flushMicrotasks() {
  await Promise.resolve()
}

describe('useSSE', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    initSSE.mockResolvedValue({})
    MockEventSource.instances = []
    global.EventSource = MockEventSource
    delete window.VUE_APP_TARANIS_NG_CORE_SSE
  })

  afterEach(() => {
    delete global.EventSource
  })

  it('should initialize SSE and connect with credentials', async () => {
    window.VUE_APP_TARANIS_NG_CORE_SSE = 'http://example.test/sse'
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

    MockEventSource.instances[0].emit(
      'report-item-updated',
      JSON.stringify({ report_item_id: 42, user_id: 7 })
    )

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

    expect(connection.removeEventListener).toHaveBeenCalledWith(
      'report-item-updated',
      registeredListener
    )
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
})
