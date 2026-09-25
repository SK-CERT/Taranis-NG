import { onMounted, onUnmounted } from 'vue'

type ResyncHandler = () => void | Promise<void>

const RESYNC_COALESCE_MS = 100

/**
 * Refresh a mounted SSE consumer after the stream reports a missed-event window.
 * Bursts are coalesced and a signal received during a refresh becomes one trailing
 * refresh, so recovery cannot create parallel request storms or lose the newest signal.
 */
export function useSseResync(handler: ResyncHandler): void {
    let timer: ReturnType<typeof setTimeout> | undefined
    let running = false
    let pending = false
    let mounted = false

    const run = async (): Promise<void> => {
        if (!mounted) return
        if (running) {
            pending = true
            return
        }

        running = true
        try {
            do {
                pending = false
                try {
                    await handler()
                } catch (error) {
                    console.error('[SSE] Data resynchronization failed:', error)
                }
            } while (mounted && pending)
        } finally {
            running = false
        }
    }

    const requestResync = (): void => {
        if (!mounted) return
        if (running) {
            pending = true
            return
        }
        if (timer) return

        timer = setTimeout(() => {
            timer = undefined
            void run()
        }, RESYNC_COALESCE_MS)
    }

    onMounted(() => {
        mounted = true
        window.addEventListener('sse-resync', requestResync)
    })

    onUnmounted(() => {
        mounted = false
        pending = false
        if (timer) {
            clearTimeout(timer)
            timer = undefined
        }
        window.removeEventListener('sse-resync', requestResync)
    })
}
