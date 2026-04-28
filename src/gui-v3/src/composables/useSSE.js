import { ref, onUnmounted } from 'vue'
import { initSSE } from '@/api/auth'
import { useAuthStore } from '@/stores/auth'

/**
 * Composable for Server-Sent Events (SSE) connection
 * Manages real-time event streaming from the backend
 */
export function useSSE() {
  useAuthStore()
  const sseConnection = ref(null)
  const eventHandlers = ref(new Map())
  const eventListeners = ref(new Map())

  /**
   * Get SSE URL from environment
   */
  const getSSEUrl = () => {
    const baseUrl =
      import.meta.env.VITE_APP_TARANIS_NG_CORE_SSE ||
      window.VUE_APP_TARANIS_NG_CORE_SSE ||
      '/sse'
    return baseUrl
  }

  const closeConnection = (clearHandlers = false) => {
    if (sseConnection.value) {
      console.log('[SSE] Disconnecting')
      sseConnection.value.close()
      sseConnection.value = null
    }

    eventListeners.value.clear()

    if (clearHandlers) {
      eventHandlers.value.clear()
    }
  }

  /**
   * Connect to SSE endpoint
   */
  const connect = async () => {
    if (sseConnection.value) {
      return sseConnection.value
    }

    await initSSE()

    return new Promise((resolve, reject) => {
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
  const subscribe = (eventName, handler) => {
    eventHandlers.value.set(eventName, handler)

    if (!sseConnection.value) {
      return
    }

    const existingListener = eventListeners.value.get(eventName)
    if (existingListener) {
      sseConnection.value.removeEventListener(eventName, existingListener)
    }

    const listener = (event) => {
      try {
        const data = JSON.parse(event.data)
        handler(data)
      } catch (error) {
        console.error(`[SSE] Error parsing ${eventName} event:`, error)
        handler(event.data)
      }
    }

    sseConnection.value.addEventListener(eventName, listener)
    eventListeners.value.set(eventName, listener)
  }

  /**
   * Unsubscribe from an event
   */
  const unsubscribe = (eventName) => {
    const listener = eventListeners.value.get(eventName)

    if (sseConnection.value && listener) {
      sseConnection.value.removeEventListener(eventName, listener)
    }

    eventListeners.value.delete(eventName)
    eventHandlers.value.delete(eventName)
  }

  /**
   * Disconnect SSE
   */
  const disconnect = () => {
    closeConnection(true)
  }

  /**
   * Reconnect SSE (close and reopen)
   */
  const reconnect = () => {
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
