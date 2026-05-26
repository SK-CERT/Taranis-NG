import { ref, onUnmounted } from 'vue'
import { initSSE } from '@/api/auth'
import { useAuthStore } from '@/stores/auth'

type SseHandler = (payload: unknown) => void

type SseListener = (event: MessageEvent<string>) => void

/**
 * Composable for Server-Sent Events (SSE) connection
 * Manages real-time event streaming from the backend
 */
export function useSSE() {
    useAuthStore()

    const sseConnection = ref<EventSource | null>(null)
    const eventHandlers = ref(new Map<string, SseHandler>())
    const eventListeners = ref(new Map<string, SseListener>())

    /**
     * Get SSE URL from environment
     */
    const getSSEUrl = (): string => {
        const baseUrl = import.meta.env.VITE_APP_TARANIS_NG_CORE_SSE || '/sse'
        return baseUrl
    }

    const closeConnection = (clearHandlers = false): void => {
        if (sseConnection.value) {
            sseConnection.value.close()
            sseConnection.value = null
            console.log('[SSE] Disconnected')
        }

        eventListeners.value.clear()

        if (clearHandlers) {
            eventHandlers.value.clear()
        }
    }

    /**
     * Connect to SSE endpoint
     */
    const connect = async (): Promise<EventSource> => {
        if (sseConnection.value) {
            console.log('[SSE] already conected')
            return sseConnection.value
        }

        await initSSE()

        return new Promise<EventSource>((resolve, reject) => {
            let settled = false

            try {
                const url = getSSEUrl()
                const eventSource = new EventSource(url, { withCredentials: true })

                eventSource.onopen = () => {
                    console.log('[SSE] Connected')
                    sseConnection.value = eventSource

                    // Subscribe registered handlers
                    eventHandlers.value.forEach((handler, eventName) => {
                        subscribe(eventName, handler)
                    })

                    settled = true
                    resolve(eventSource)
                }

                eventSource.onerror = (error) => {
                    console.warn('[SSE] Connection error - SSE may not be available')
                    closeConnection(false)

                    if (!settled) {
                        reject(error)
                    }
                }
            } catch (error) {
                console.warn('[SSE] Failed to initialize - SSE may not be available')
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
        closeConnection(true)
    }

    /**
     * Reconnect SSE (close and reopen)
     */
    const reconnect = (): Promise<EventSource> => {
        closeConnection(false)
        return connect()
    }

    // Cleanup on component unmount
    onUnmounted(() => {
        disconnect()
    })

    return {
        sseConnection,
        connect,
        disconnect,
        reconnect,
        subscribe,
        unsubscribe
    }
}
