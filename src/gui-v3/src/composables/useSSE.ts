import { ref, onUnmounted } from 'vue'
import { initSSE } from '@/api/auth'
import { useAuthStore } from '@/stores/auth'

type SseHandler = (payload: unknown) => void

type SseListener = (event: MessageEvent<string>) => void

/** Backoff bounds for automatic reconnection attempts. */
const RECONNECT_BASE_DELAY = 1000
const RECONNECT_MAX_DELAY = 30000

/**
 * After this many failures in a row the backend is clearly not coming back in a moment.
 * Retries continue so the tab still recovers on its own, but at a rate that neither hammers
 * the API nor buries its log in rejected requests.
 */
const RECONNECT_ATTEMPTS_BEFORE_SLOWDOWN = 10
const RECONNECT_IDLE_DELAY = 300000

/**
 * How long the tab has to have been in the background before returning to it triggers a
 * resync. Short switches are ignored - the stream almost certainly stayed alive.
 */
const HIDDEN_RESYNC_THRESHOLD = 15000

/**
 * Composable for Server-Sent Events (SSE) connection
 * Manages real-time event streaming from the backend
 */
export function useSSE() {
    useAuthStore()

    const sseConnection = ref<EventSource | null>(null)
    const eventHandlers = ref(new Map<string, SseHandler>())
    const eventListeners = ref(new Map<string, SseListener>())

    const connected = ref(false)
    const reconnectTimer = ref<ReturnType<typeof setTimeout> | null>(null)
    const reconnectAttempt = ref(0)
    // Set by disconnect() (logout / unmount) so we stop retrying on purpose.
    const stopped = ref(false)
    // Whether a live stream existed at some point - tells a first connect from a re-connect.
    const wasConnected = ref(false)
    const hiddenAt = ref<number | null>(null)
    const resyncHandlers = ref(new Set<() => void>())

    /**
     * Get SSE URL from environment
     */
    const getSSEUrl = (): string => {
        const baseUrl = import.meta.env.VITE_APP_TARANIS_NG_CORE_SSE || '/sse'
        return baseUrl
    }

    /**
     * Register a callback fired whenever the stream comes back after having been away.
     * Events published while the tab was disconnected are gone for good (the backend keeps
     * no history), so listeners must re-read whatever state they display.
     */
    const onResync = (handler: () => void): void => {
        resyncHandlers.value.add(handler)
    }

    const notifyResync = (): void => {
        resyncHandlers.value.forEach((handler) => {
            try {
                handler()
            } catch (error) {
                console.error('[SSE] Resync handler failed:', error)
            }
        })
    }

    /**
     * Whether the stream session was refused because this client is not authenticated,
     * as opposed to a transient failure that a retry could still recover from.
     */
    const isAuthFailure = (error: unknown): boolean => {
        const status = (error as { response?: { status?: number } })?.response?.status
        return status === 401 || status === 403
    }

    const clearReconnectTimer = (): void => {
        if (reconnectTimer.value) {
            clearTimeout(reconnectTimer.value)
            reconnectTimer.value = null
        }
    }

    const closeConnection = (clearHandlers = false): void => {
        if (sseConnection.value) {
            sseConnection.value.close()
            sseConnection.value = null
            console.log('[SSE] Disconnected')
        }

        connected.value = false
        eventListeners.value.clear()

        if (clearHandlers) {
            eventHandlers.value.clear()
        }
    }

    /**
     * Queue the next connection attempt with exponential backoff. Without this a single
     * network blip, a suspended laptop or a proxy idle timeout would leave the tab
     * permanently silent while still looking perfectly normal.
     */
    const scheduleReconnect = (): void => {
        if (stopped.value || reconnectTimer.value || sseConnection.value) {
            return
        }

        const delay =
            reconnectAttempt.value >= RECONNECT_ATTEMPTS_BEFORE_SLOWDOWN
                ? RECONNECT_IDLE_DELAY
                : Math.min(RECONNECT_BASE_DELAY * 2 ** reconnectAttempt.value, RECONNECT_MAX_DELAY)
        reconnectAttempt.value += 1
        console.info(`[SSE] Reconnecting in ${delay} ms`)

        reconnectTimer.value = setTimeout(() => {
            reconnectTimer.value = null
            connect().catch(() => {
                // connect() already queued the next attempt.
            })
        }, delay)
    }

    /**
     * Connect to SSE endpoint
     */
    const connect = async (): Promise<EventSource> => {
        stopped.value = false

        if (sseConnection.value) {
            console.log('[SSE] already conected')
            return sseConnection.value
        }

        try {
            await initSSE()
        } catch (error) {
            if (isAuthFailure(error)) {
                // Retrying cannot mint a token: it would only spam the API with rejected
                // requests. Wait for something that can change the outcome instead - a
                // login, a token refresh, or an explicit reconnect.
                console.info('[SSE] Not authenticated - real-time updates stay off until the next login')
            } else {
                console.warn('[SSE] Failed to initialize stream session')
                scheduleReconnect()
            }
            throw error
        }

        return new Promise<EventSource>((resolve, reject) => {
            let settled = false

            try {
                const url = getSSEUrl()
                const eventSource = new EventSource(url, { withCredentials: true })

                eventSource.onopen = () => {
                    console.log('[SSE] Connected')
                    sseConnection.value = eventSource
                    connected.value = true

                    const missedEvents = wasConnected.value
                    wasConnected.value = true
                    reconnectAttempt.value = 0

                    // Subscribe registered handlers
                    eventHandlers.value.forEach((handler, eventName) => {
                        subscribe(eventName, handler)
                    })

                    if (missedEvents) {
                        notifyResync()
                    }

                    settled = true
                    resolve(eventSource)
                }

                eventSource.onerror = (error) => {
                    console.warn('[SSE] Connection error - will retry')
                    closeConnection(false)
                    scheduleReconnect()

                    if (!settled) {
                        reject(error)
                    }
                }
            } catch (error) {
                console.warn('[SSE] Failed to initialize - SSE may not be available')
                scheduleReconnect()
                reject(error)
            }
        })
    }

    /**
     * Subscribe to an event
     */
    const subscribe = (eventName: string, handler: SseHandler): void => {
        eventHandlers.value.set(eventName, handler)

        if (!sseConnection.value) {
            return
        }

        const existingListener = eventListeners.value.get(eventName)
        if (existingListener) {
            sseConnection.value.removeEventListener(eventName, existingListener as EventListener)
        }

        const listener: SseListener = (event) => {
            try {
                const data = JSON.parse(event.data)
                handler(data)
            } catch (error) {
                console.error(`[SSE] Error parsing ${eventName} event:`, error)
                handler(event.data)
            }
        }

        sseConnection.value.addEventListener(eventName, listener as EventListener)
        eventListeners.value.set(eventName, listener)
    }

    /**
     * Unsubscribe from an event
     */
    const unsubscribe = (eventName: string): void => {
        const listener = eventListeners.value.get(eventName)

        if (sseConnection.value && listener) {
            sseConnection.value.removeEventListener(eventName, listener as EventListener)
        }

        eventListeners.value.delete(eventName)
        eventHandlers.value.delete(eventName)
    }

    /**
     * Disconnect SSE
     */
    const disconnect = (): void => {
        stopped.value = true
        wasConnected.value = false
        reconnectAttempt.value = 0
        clearReconnectTimer()
        closeConnection(true)
    }

    /**
     * Reconnect SSE (close and reopen)
     */
    const reconnect = (): Promise<EventSource> => {
        clearReconnectTimer()
        reconnectAttempt.value = 0
        closeConnection(false)
        return connect()
    }

    /**
     * A stream can die without ever firing onerror (the OS suspends, a proxy drops an idle
     * connection), so a tab returning to the foreground re-checks the connection and, if it
     * was away long enough to have missed something, asks listeners to resync.
     */
    const handleVisibilityChange = (): void => {
        if (document.visibilityState !== 'visible') {
            hiddenAt.value = Date.now()
            return
        }

        const hiddenFor = hiddenAt.value === null ? 0 : Date.now() - hiddenAt.value
        hiddenAt.value = null

        if (stopped.value) {
            return
        }

        if (!sseConnection.value) {
            // Only chase a stream that was working before. If it never came up (no session,
            // SSE not deployed), every tab switch would be another rejected request.
            if (!wasConnected.value) {
                return
            }
            // Don't make the user wait out the current backoff delay.
            clearReconnectTimer()
            reconnectAttempt.value = 0
            connect().catch(() => {})
        } else if (hiddenFor > HIDDEN_RESYNC_THRESHOLD) {
            notifyResync()
        }
    }

    document.addEventListener('visibilitychange', handleVisibilityChange)

    // Cleanup on component unmount
    onUnmounted(() => {
        document.removeEventListener('visibilitychange', handleVisibilityChange)
        resyncHandlers.value.clear()
        disconnect()
    })

    return {
        sseConnection,
        connected,
        connect,
        disconnect,
        reconnect,
        subscribe,
        unsubscribe,
        onResync
    }
}
